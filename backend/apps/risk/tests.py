from datetime import datetime, timedelta, timezone as tz
from unittest import mock

from django.test import TestCase

from apps.alerts.models import Alert
from apps.common.constants import level_from_score
from apps.common.testing import make_node, make_user, make_village
from apps.risk import engine, firms, weather
from apps.risk.models import FireHotspot, RiskAssessment, WeatherSnapshot

FIRMS_CSV = """latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,instrument,confidence,version,bright_ti5,frp,daynight
41.35,72.96,340.1,0.4,0.4,2026-10-17,0042,N,VIIRS,n,2.0NRT,300.2,12.5,N
41.36,72.97,350.0,0.4,0.4,2026-10-17,1304,N,VIIRS,h,2.0NRT,301.0,30.1,D
bad,row,,,,2026-10-17,0100,N,VIIRS,l,2.0NRT,,,D
"""


class ParserTests(TestCase):
    def test_firms_parse_and_store_is_idempotent(self):
        rows = firms.parse_csv(FIRMS_CSV, source="VIIRS_SNPP_NRT")
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["acquired_at"], datetime(2026, 10, 17, 0, 42, tzinfo=tz.utc))
        self.assertEqual((rows[0]["confidence"], rows[1]["confidence"]), ("nominal", "high"))
        self.assertEqual(firms.store_hotspots(rows), 2)
        self.assertEqual(firms.store_hotspots(rows), 0)

    def test_firms_error_text_is_reported_not_parsed(self):
        with self.assertRaises(firms.FirmsError):
            firms.parse_csv("Invalid MAP_KEY.")

    def test_open_meteo_parse(self):
        now = datetime(2026, 10, 17, 12, tzinfo=tz.utc)
        times = [(now - timedelta(hours=47 - i)).strftime("%Y-%m-%dT%H:%M") for i in range(96)]
        data = {"hourly": {
            "time": times, "precipitation": [1.0] * 96, "snowfall": [0.5] * 96, "temperature_2m": [5.0] * 96,
            "wind_speed_10m": [10.0] * 96, "snow_depth": [0.3] * 96, "freezing_level_height": [3000.0] * 96,
        }}
        s = weather.parse_open_meteo(data, now=now)
        self.assertEqual(s["precip_prev24_mm"], 24.0)
        self.assertEqual(s["precip_next24_mm"], 24.0)
        self.assertEqual(s["snowfall_prev24_cm"], 12.0)
        self.assertEqual(s["freezing_level_m"], 3000.0)

    def test_open_meteo_empty_raises(self):
        with self.assertRaises(weather.WeatherError):
            weather.parse_open_meteo({"hourly": {}})

    def test_null_values_are_tolerated(self):
        now = datetime(2026, 10, 17, 12, tzinfo=tz.utc)
        data = {"hourly": {"time": ["2026-10-17T11:00", "2026-10-17T13:00"], "precipitation": [None, None]}}
        self.assertEqual(weather.parse_open_meteo(data, now=now)["precip_prev24_mm"], 0.0)


class LevelTests(TestCase):
    def test_boundaries(self):
        self.assertEqual([level_from_score(s) for s in (0, 24, 25, 49, 50, 74, 75, 100)],
                         ["low", "low", "medium", "medium", "high", "high", "critical", "critical"])


@mock.patch("apps.common.telegram.safe_send", return_value=(True, ""))
class EngineTests(TestCase):
    def setUp(self):
        self.village = make_village()

    def _weather(self, **kw):
        s = dict(precip_prev24_mm=0, precip_next24_mm=0, snowfall_prev24_cm=0, snowfall_next24_cm=0,
                 temp_now_c=15, temp_max_prev24_c=20, wind_max_24h_kmh=5, snow_depth_m=0, freezing_level_m=4000)
        s.update(kw)
        WeatherSnapshot.objects.create(village=self.village, summary=s)

    def test_calm_conditions_are_low_and_raise_no_alerts(self, send):
        self._weather()
        engine.evaluate_village(self.village)
        self.assertEqual(Alert.objects.count(), 0)
        self.assertTrue(RiskAssessment.objects.filter(village=self.village).exists())
        self.assertTrue(all(a.level == "low" for a in RiskAssessment.objects.all()))

    def test_heavy_rain_raises_flood_and_mudflow_scores(self, send):
        self._weather(precip_prev24_mm=90, precip_next24_mm=60)
        engine.evaluate_village(self.village)
        flood = RiskAssessment.objects.get(village=self.village, hazard="flood")
        self.assertNotEqual(flood.level, "low")

    def test_fire_hotspot_nearby_makes_fire_risk(self, send):
        self._weather(temp_now_c=33, wind_max_24h_kmh=40)
        FireHotspot.objects.create(
            latitude=self.village.lat + 0.01, longitude=self.village.lon, acquired_at=datetime.now(tz.utc),
            satellite="N", confidence="high", frp=40, brightness=350, source="VIIRS_SNPP_NRT",
        )
        engine.evaluate_village(self.village)
        fire = RiskAssessment.objects.get(village=self.village, hazard="fire")
        self.assertEqual(fire.level, "medium")  # satellite alone is only a watch-level signal

    def test_smoke_sensor_plus_hotspot_is_high_or_critical(self, send):
        from apps.sensors.models import Reading

        node, _ = make_node(self.village, "t-fire", 0.01, 0.0, 0, kind="fire")
        self._weather()
        Reading.objects.create(node=node, smoke_ppm=900, temperature_c=70, extra={"crackle_score": 0.9})
        FireHotspot.objects.create(
            latitude=self.village.lat + 0.01, longitude=self.village.lon, acquired_at=datetime.now(tz.utc),
            satellite="N", confidence="high", frp=40, brightness=350, source="VIIRS_SNPP_NRT",
        )
        engine.evaluate_village(self.village)
        fire = RiskAssessment.objects.get(village=self.village, hazard="fire")
        self.assertIn(fire.level, ("high", "critical"))
        self.assertTrue(Alert.objects.filter(hazard="fire", status="active").exists())

    def test_assessments_are_updated_in_place(self, send):
        self._weather()
        engine.evaluate_village(self.village)
        n = RiskAssessment.objects.count()
        engine.evaluate_village(self.village)
        self.assertEqual(RiskAssessment.objects.count(), n)
