"""Create demo data (idempotent): villages, evacuation points, sensor nodes, users, market.

Village and node coordinates are approximate and for demonstration only.
Device keys are written to .demo_node_keys.json (gitignored) so simulators can use them.
"""
import json
import math
import secrets
from decimal import Decimal

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from apps.accounts.models import User
from apps.geo.models import (
    Announcement, Building, EvacuationPoint, EvacuationRoute, HazardZone, RoadStatus, Village, VillageContact,
)
from apps.market.models import Category, Listing, ListingImage
from apps.risk.models import WeatherSnapshot
from apps.sensors.models import Node

VILLAGES = [
    # slug, name, name_ky, name_en, region, lat, lon, population
    ("arslanbob", "Арслан-Боб", "Арстанбап", "Arslanbob", "Jalal-Abad", 41.3315, 72.9446, 15000),
    ("kochkor", "Кочкор", "Кочкор", "Kochkor", "Naryn", 42.2150, 75.7500, 13000),
    ("jeti-oguz", "Джети-Огуз", "Жети-Өгүз", "Jeti-Oguz", "Issyk-Kul", 42.3350, 78.1850, 8000),
    ("naryn", "Нарын", "Нарын", "Naryn", "Naryn", 41.4287, 76.0000, 40000),
]

# The design's village: Ak-Tash in the Suusamyr valley. Coordinates are approximate (demo).
SUUSAMYR_VALLEY = ("Суусамырская долина", "Суусамыр өрөөнү")
SUUSAMYR_VILLAGES = [
    # slug, name, name_ky, name_en, lat, lon, population, elevation_m
    ("ak-tash", "Ак-Таш", "Ак-Таш", "Ak-Tash", 42.2000, 73.5000, 1800, 2240),
    ("suusamyr", "Суусамыр", "Суусамыр", "Suusamyr", 42.1700, 73.6000, 2600, 2100),
    ("kara-suu", "Кара-Суу", "Кара-Суу", "Kara-Suu", 42.1400, 73.4300, 1500, 2050),
]

# Map shapes are drawn in the design's 700x740 picture; 1 unit = 1.5 m, village centre = (350, 370).
SAFE_HILL = [(300, 140), (380, 120), (500, 125), (600, 160), (660, 230), (670, 360), (640, 450), (560, 500),
             (470, 510), (380, 460), (310, 390), (270, 300), (285, 210)]
RAVINE = [(180, 0), (185, 100), (170, 200), (130, 300), (80, 420), (45, 520), (60, 650), (120, 740), (220, 740),
          (165, 650), (150, 540), (190, 390), (240, 280), (270, 150), (270, 0)]
ROUTE = [(310, 560), (360, 490), (410, 430), (460, 330), (510, 290)]
HOUSES = [(268, 556, "№14"), (380, 567, "№15"), (302, 637, "№16"), (441, 468, "№21"), (499, 456, "№22"),
          (582, 488, "№23"), (601, 329, "№31"), (423, 239, "№32")]
SHELTERS = [
    # name_ru, name_ky, notes_ru, notes_ky, x, y, primary, clinic, water
    ("Сельская школа", "Айыл мектеби", "Северный холм, 8 минут пешком", "Түндүк дөңсөө тарап",
     510, 290, True, True, True),
    ("Сельский клуб", "Айыл клубу", "Просторный зал, тёплый", "Кең залы бар, жылуу", 440, 455, False, False, False),
    ("Северный холм", "Түндүк дөңсөө", "Открытая возвышенность", "Ачык бийик жер", 560, 215, False, False, False),
    ("Фельдшерский пункт", "Фельдшердик пункт (ФАП)", "Врач на месте", "Дарыгер бар", 405, 235, False, True, True),
]

CONTACTS = [
    # role, name_ru, name_ky, phone, display, order
    ("head", "Глава села (аким)", "Айыл башчысы (Аким)", "0313752102", "0 (3137) 5-21-02", 1),
    ("ambulance", "Скорая помощь (ФАП)", "Тез жардам (ФАП)", "103", "103 же 0700 12-34-56", 2),
    ("emergency", "МЧС Кыргызстана", "Өзгөчө кырдаалдар министрлиги", "112", "112 (Акысыз)", 3),
    ("vet", "Бакыт-байке", "Бакыт байке", "0700123456", "0700 12-34-56", 4),
    ("medic", "Айнура-эже", "Айнура эже", "0772987654", "0772 98-76-54", 5),
    ("pasture", "Темир-ава", "Темир ава", "0555456789", "0555 45-67-89", 6),
    ("transport", "Грузоперевозки", "Жүк ташуучу", "0313752102", "0 (3137) 5-21-02", 7),
    ("support", "Поддержка села", "Айылдык колдоо", "0313752102", "0 (3137) 5-21-02", 8),
]

ROADS = [
    ("Перевал Тоо-Ашуу", "Төө-Ашуу ашуусу", "open", "", ""),
    ("Дорога в село", "Айылга баруучу жол", "open", "", ""),
]

ANNOUNCEMENT = dict(
    source="Глава села и ветеринар", source_ky="Айыл башчысынан жана ветеринардан",
    title="Летняя вакцинация и график выгона скота",
    title_ky="Жайкы эмдөө жана жайыт графиги",
    body=("Уважаемые односельчане! С 15 июня разрешён выгон скота на высокогорные пастбища. "
          "Пункт вакцинации лошадей и крупного рогатого скота работает у центрального клуба "
          "ежедневно с 08:00 до 17:00."),
    body_ky=("Урматтуу айылдаштар! 15-июндан тарта жогорку жайлоолорго мал чыгарууга уруксат берилет. "
             "Жылкы жана бодо малды эмдөө пункту айылдын борбордук клубунун алдында күн сайын саат "
             "08:00дөн 17:00гө чейин иштейт."),
)

EVAC = {
    "arslanbob": [("Школа №1 (на возвышенности)", 41.3380, 72.9300), ("Площадка у мечети", 41.3290, 72.9380)],
    "kochkor": [("Холм за центральной площадью", 42.2210, 75.7400)],
    "jeti-oguz": [("Высокая терраса над сёлами", 42.3400, 78.1750)],
    "naryn": [("Холм у стадиона", 41.4350, 75.9900)],
}

# device_id, name, kind, lat offset, lon offset, flow_order, water_alert_cm   (offsets from Arslanbob)
AKTASH_NODES = [
    ("ak-tash-n1", "Верховье сая (узел 1)", "multi", 0.045, -0.004, 0, 220.0),
    ("ak-tash-n2", "Середина сая (узел 2)", "multi", 0.025, -0.003, 1, 220.0),
    ("ak-tash-n3", "Перед селом (узел 3)", "multi", 0.008, -0.002, 2, 200.0),
    ("ak-tash-fire", "Склон над селом (огонь)", "fire", 0.015, 0.012, 0, None),
    ("ak-tash-gw", "Шлюз LoRa и сирена", "gateway", 0.001, 0.001, 9, None),
]

ARSLANBOB_NODES = [
    ("arslanbob-n1", "Верховье реки (узел 1)", "multi", 0.050, 0.030, 0, 220.0),
    ("arslanbob-n2", "Середина ущелья (узел 2)", "multi", 0.030, 0.018, 1, 220.0),
    ("arslanbob-n3", "Перед селом (узел 3)", "multi", 0.012, 0.007, 2, 200.0),
    ("arslanbob-fire", "Орехово-плодовый лес (огонь)", "fire", -0.020, 0.030, 0, None),
    ("arslanbob-gw", "Шлюз LoRa и сирена", "gateway", 0.002, 0.001, 9, None),
]

CATEGORIES = [
    # slug, ru, ky, en, icon, is_animal, order, hint_ru, hint_ky
    ("dairy", "Молочные продукты", "Сүт азыктары", "Dairy", "water_drop", False, 1, "Кымыз, молоко, масло", "Кымыз, сүт, май"),
    ("meat", "Свежее мясо", "Таза эт", "Meat", "restaurant", False, 2, "Баранина, говядина, конина", "Кой, уй, жылкы"),
    ("honey", "Натуральный мёд", "Табигый бал", "Honey", "hive", False, 3, "Горный, белый мёд", "Тоо гүлү, ак бал"),
    ("livestock", "Живой скот", "Тирүү мал", "Livestock", "pets", True, 4, "Бараны, телята, жеребята", "Кочкор, торпок, тай"),
]

# seller phone, name, village slug, verified, [listings]
SELLERS = [
    ("+996700123456", "Нурбек ава", "ak-tash", [
        dict(title="Тоо балы (1 кг)", category="honey", price="650", unit="jar", qty="12",
             description="Суусамырдын бийик тоолуу шыбак, арча гүлдөрүнөн жыйналган таза бал.",
             tag="100% Табигый тоо балы", place_note="Ак-Таш айылы, Жайлоо-1", art="honey"),
    ]),
    ("+996772987654", "Бакыт аксакал", "kara-suu", [
        dict(title="Жаш кочкор (Гиссар)", category="livestock", price="18000", unit="head", qty="1",
             description="1 жаш 4 айлык, семиз, жайлоодо гана багылган. Эмдөөлөрү толук бүткөн.",
             tag="Асыл тукумдуу", place_note="Кара-Суу айылы, мал сарай", art="ram",
             extra=dict(species="sheep", breed="Гиссар", sex="m", age_months=16, weight_kg=Decimal("62"))),
    ]),
    ("+996555332211", "Бектур аксакал", "suusamyr", [
        dict(title="Таза Саамал / Кымыз (1 л)", category="dairy", price="150", unit="l", qty="30",
             description="Эртең мененки жаңы саамал жана бир сутка бабында турган таза жайлоо кымызы. Суу аралашпаган.",
             tag="Таңкы жаңы саамал", place_note="Суусамыр, Боз-Үй конушу", art="kymyz"),
    ]),
    ("+996705778899", "Айша эне", "ak-tash", [
        dict(title="Таза Сары май", category="dairy", price="900", unit="kg", qty="8",
             description="Уйдун жаңы сүтүнөн тартылган каймакты кайнатып жасалган нукура сары май.",
             tag="Колдун таза майы", place_note="Ак-Таш айылы, Борбордук көчө", art="butter"),
    ]),
]


def svg_art(kind):
    """Small flat illustrations used as dummy listing photos (no external images needed)."""
    sky = ('<defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#cfe8ff"/>'
           '<stop offset="1" stop-color="#f1f8e9"/></linearGradient></defs>'
           '<rect width="800" height="600" fill="url(#g)"/>'
           '<path d="M0 360 L160 220 L300 340 L470 170 L640 330 L800 240 L800 600 L0 600Z" fill="#dfe7ee"/>'
           '<path d="M470 170 L520 215 L470 205 L430 225Z" fill="#fff"/>'
           '<path d="M0 420 Q220 340 420 410 T800 390 L800 600 L0 600Z" fill="#7cb342"/>'
           '<path d="M0 480 Q260 420 520 480 T800 460 L800 600 L0 600Z" fill="#558b2f"/>')
    art = {
        "honey": ('<rect x="300" y="250" width="200" height="250" rx="34" fill="#f9a825"/>'
                  '<rect x="300" y="250" width="200" height="250" rx="34" fill="none" stroke="#e65100" stroke-width="8"/>'
                  '<rect x="285" y="215" width="230" height="50" rx="14" fill="#8d6e63"/>'
                  '<rect x="335" y="320" width="130" height="90" rx="12" fill="#fff8e1"/>'
                  '<circle cx="400" cy="365" r="22" fill="#f9a825"/>'),
        "ram": ('<ellipse cx="400" cy="400" rx="170" ry="100" fill="#f5f1e6" stroke="#bdb59c" stroke-width="6"/>'
                '<rect x="270" y="470" width="24" height="90" rx="8" fill="#5d4037"/><rect x="340" y="480" width="24" height="80" rx="8" fill="#5d4037"/>'
                '<rect x="450" y="480" width="24" height="80" rx="8" fill="#5d4037"/><rect x="520" y="470" width="24" height="90" rx="8" fill="#5d4037"/>'
                '<ellipse cx="575" cy="345" rx="62" ry="52" fill="#6d4c41"/>'
                '<path d="M540 320 q-50 -40 -10 -85 q40 20 25 70" fill="none" stroke="#3e2723" stroke-width="12" stroke-linecap="round"/>'
                '<circle cx="590" cy="338" r="8" fill="#fff"/><circle cx="592" cy="338" r="4" fill="#000"/>'),
        "kymyz": ('<path d="M230 330 H570 Q560 480 400 500 Q240 480 230 330Z" fill="#fff8e1" stroke="#8d6e63" stroke-width="10"/>'
                  '<ellipse cx="400" cy="330" rx="170" ry="34" fill="#fffde7" stroke="#8d6e63" stroke-width="10"/>'
                  '<ellipse cx="400" cy="334" rx="140" ry="22" fill="#fff"/>'
                  '<rect x="360" y="500" width="80" height="26" rx="8" fill="#8d6e63"/>'),
        "butter": ('<path d="M280 280 H520 Q560 380 520 480 Q400 540 280 480 Q240 380 280 280Z" fill="#a1664a" stroke="#6d4030" stroke-width="8"/>'
                   '<ellipse cx="400" cy="280" rx="120" ry="30" fill="#ffd54f" stroke="#6d4030" stroke-width="8"/>'
                   '<ellipse cx="400" cy="276" rx="95" ry="20" fill="#ffe082"/>'),
    }[kind]
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600">{sky}{art}</svg>'


def to_latlon(village, x, y):
    """Design picture coords (x right, y down; 1 unit = 1.5 m; centre 350,370) -> lat, lon."""
    dy_m, dx_m = -(y - 370) * 1.5, (x - 350) * 1.5
    return (village.lat + dy_m / 111_320.0, village.lon + dx_m / (111_320.0 * math.cos(math.radians(village.lat))))


class Command(BaseCommand):
    help = "Create demo data for the hackathon (safe to run repeatedly)."

    def add_arguments(self, parser):
        parser.add_argument("--reset-keys", action="store_true", help="Issue new device keys for all demo nodes")

    def handle(self, *args, **opts):
        villages = {}
        for slug, name, ky, en, region, lat, lon, pop in VILLAGES:
            v, _ = Village.objects.get_or_create(
                slug=slug, defaults=dict(name=name, name_ky=ky, name_en=en, region=region, lat=lat, lon=lon, population=pop)
            )
            villages[slug] = v
        for slug, points in EVAC.items():
            for name, lat, lon in points:
                EvacuationPoint.objects.get_or_create(village=villages[slug], name=name, defaults=dict(lat=lat, lon=lon))

        for slug, name, ky, en, lat, lon, pop, elev in SUUSAMYR_VILLAGES:
            v, _ = Village.objects.update_or_create(
                slug=slug,
                defaults=dict(
                    name=name, name_ky=ky, name_en=en, region="Chui", lat=lat, lon=lon, population=pop,
                    valley=SUUSAMYR_VALLEY[0], valley_ky=SUUSAMYR_VALLEY[1], elevation_m=elev,
                    river_name="река Суусамыр", river_name_ky="Суусамыр суусу",
                ),
            )
            villages[slug] = v
        self._seed_aktash(villages["ak-tash"])

        keys_path = settings.BASE_DIR / ".demo_node_keys.json"
        keys = json.loads(keys_path.read_text()) if keys_path.exists() else {}
        for base, rows in ((villages["arslanbob"], ARSLANBOB_NODES), (villages["ak-tash"], AKTASH_NODES)):
            for device_id, name, kind, dlat, dlon, order, alert_cm in rows:
                node, created = Node.objects.get_or_create(
                    device_id=device_id,
                    defaults=dict(name=name, village=base, kind=kind, lat=base.lat + dlat, lon=base.lon + dlon,
                                  flow_order=order, water_alert_cm=alert_cm),
                )
                if created or opts["reset_keys"] or device_id not in keys:
                    keys[device_id] = node.rotate_key()
        keys_path.write_text(json.dumps(keys, indent=2))

        home_x, home_y, home_label = HOUSES[0]
        home_lat, home_lon = to_latlon(villages["ak-tash"], home_x, home_y)
        users = {}
        for phone, name, role, village, extra_fields in [
            ("+996700000001", "Admin", User.ADMIN, None, {}),
            ("+996700000002", "Спасатель МЧС (demo)", User.RESCUER, villages["ak-tash"], {"is_verified": True}),
            ("+996700000003", "Айбек (житель Ак-Таша)", User.VILLAGER, villages["ak-tash"],
             {"is_verified": True, "home_lat": home_lat, "home_lon": home_lon, "home_label": home_label,
              "language": "ky"}),
            ("+996700000004", "Бишкекский покупатель", User.BUYER, None, {}),
        ]:
            user = User.objects.filter(phone=phone).first()
            if user is None:
                extra = dict(name=name, role=role, village=village, **extra_fields)
                if role == User.ADMIN:
                    password = secrets.token_urlsafe(12)
                    user = User.objects.create_superuser(phone, password, **extra)
                    self.stdout.write(self.style.WARNING(f"Admin site login: {phone} / {password}  (shown once)"))
                else:
                    user = User.objects.create_user(phone, **extra)
            else:
                for k, v in {"village": village, **extra_fields}.items():
                    if v is not None:
                        setattr(user, k, v)
                user.save()
            users[phone] = user

        self._seed_market(villages)

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {len(villages)} villages, {Node.objects.count()} sensor nodes, {len(users)} users, "
            f"{Listing.objects.count()} listings."
        ))
        self.stdout.write(f"Device keys saved to {keys_path.name} (gitignored).")
        self.stdout.write("Demo logins use OTP: villager +996700000003 (Ak-Tash), rescuer +996700000002, buyer +996700000004.")

    # ------------------------------------------------------------------
    def _seed_aktash(self, v):
        v.zones.all().delete(); v.routes.all().delete(); v.buildings.all().delete()
        v.evacuation_points.all().delete(); v.contacts.all().delete(); v.roads.all().delete(); v.announcements.all().delete()
        HazardZone.objects.create(village=v, kind="safe", name="Северный холм (безопасно)", name_ky="Түндүк дөңсөө (коопсуз)",
                                  polygon=[list(to_latlon(v, x, y)) for x, y in SAFE_HILL])
        HazardZone.objects.create(village=v, kind="danger", hazard="mudflow", name="Русло селя (опасно)",
                                  name_ky="Сел тилкеси (кооптуу)", polygon=[list(to_latlon(v, x, y)) for x, y in RAVINE])
        points = []
        for ru, ky, nru, nky, x, y, primary, clinic, water in SHELTERS:
            lat, lon = to_latlon(v, x, y)
            points.append(EvacuationPoint.objects.create(
                village=v, name=ru, name_ky=ky, notes=nru, notes_ky=nky, lat=lat, lon=lon,
                is_primary=primary, has_clinic=clinic, has_water=water))
        EvacuationRoute.objects.create(village=v, point=points[0], path=[list(to_latlon(v, x, y)) for x, y in ROUTE])
        for x, y, label in HOUSES:
            lat, lon = to_latlon(v, x, y)
            Building.objects.create(village=v, label=label, lat=lat, lon=lon)
        for role, ru, ky, phone, display, order in CONTACTS:
            VillageContact.objects.create(village=v, role=role, name=ru, name_ky=ky, phone=phone, phone_display=display, order=order)
        for ru, ky, status, note, note_ky in ROADS:
            RoadStatus.objects.create(village=v, name=ru, name_ky=ky, status=status, note=note, note_ky=note_ky)
        Announcement.objects.create(village=v, **ANNOUNCEMENT)
        # dummy weather so the screens have something offline; the worker replaces it with real Open-Meteo data
        WeatherSnapshot.objects.create(village=v, summary={
            "precip_prev24_mm": 0, "precip_next24_mm": 0, "snowfall_prev24_cm": 0, "snowfall_next24_cm": 0,
            "temp_now_c": 22, "temp_max_prev24_c": 24, "wind_max_24h_kmh": 8, "snow_depth_m": 0,
            "freezing_level_m": 4200, "condition": "clear", "dummy": True,
        })

    def _seed_market(self, villages):
        for slug, ru, ky, en, icon, is_animal, order, hint_ru, hint_ky in CATEGORIES:
            Category.objects.update_or_create(
                slug=slug, defaults=dict(name_ru=ru, name_ky=ky, name_en=en, icon=icon, is_animal=is_animal,
                                         order=order, hint_ru=hint_ru, hint_ky=hint_ky))
        phones = [row[0] for row in SELLERS]
        Listing.objects.filter(seller__phone__in=phones).delete()
        Listing.objects.filter(seller__phone="+996700000003").delete()  # listings from the older seed
        Category.objects.exclude(slug__in=[c[0] for c in CATEGORIES]).filter(listings__isnull=True).delete()
        for phone, name, slug, items in SELLERS:
            seller, _ = User.objects.get_or_create(phone=phone, defaults=dict(name=name, village=villages[slug]))
            seller.name, seller.village, seller.is_verified, seller.language = name, villages[slug], True, "ky"
            seller.save()
            for item in items:
                item = dict(item)
                art = item.pop("art")
                extra = item.pop("extra", {})
                listing = Listing.objects.create(
                    seller=seller, category=Category.objects.get(slug=item.pop("category")),
                    price_kgs=Decimal(item.pop("price")), quantity=Decimal(item.pop("qty")),
                    village=villages[slug], lat=villages[slug].lat, lon=villages[slug].lon, **item, **extra)
                img = ListingImage(listing=listing, order=0)
                img.image.save(f"{art}.svg", ContentFile(svg_art(art).encode()), save=True)
