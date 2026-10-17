"""Factories shared by the test suites."""
from apps.accounts.models import User
from apps.geo.models import EvacuationPoint, Village
from apps.sensors.models import Node

BASE_LAT, BASE_LON = 41.3315, 72.9446


def make_village(slug="testville", name="Testville", lat=BASE_LAT, lon=BASE_LON):
    v, _ = Village.objects.get_or_create(slug=slug, defaults=dict(name=name, name_en=name, lat=lat, lon=lon, region="Test"))
    EvacuationPoint.objects.get_or_create(village=v, name="High ground", defaults=dict(lat=lat + 0.01, lon=lon + 0.01))
    return v


def make_user(phone, role=User.VILLAGER, village=None, chat_id=None, name="", language="en"):
    return User.objects.create_user(
        phone, role=role, village=village, telegram_chat_id=chat_id, name=name or phone, language=language
    )


def make_node(village, device_id, dlat, dlon, order, kind="multi", water_alert_cm=None):
    """Create a node and return (node, plain_device_key)."""
    node = Node(
        device_id=device_id, name=device_id, village=village, kind=kind, lat=village.lat + dlat,
        lon=village.lon + dlon, flow_order=order, water_alert_cm=water_alert_cm,
    )
    key = node.rotate_key(save=False)
    node.save()
    return node, key
