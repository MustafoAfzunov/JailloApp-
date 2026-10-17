"""Alert wording in Russian / Kyrgyz / English.

NOTE: have the Kyrgyz (ky) strings reviewed by a native speaker before production.
"""
from .constants import (
    DEFAULT_LANG,
    HAZARD_AVALANCHE,
    HAZARD_FIRE,
    HAZARD_FLOOD,
    HAZARD_MUDFLOW,
    LANGS,
    LEVEL_CRITICAL,
    LEVEL_HIGH,
    LEVEL_LOW,
    LEVEL_MEDIUM,
)

HAZARD_NAMES = {
    HAZARD_MUDFLOW: {"ru": "Сель", "ky": "Сел", "en": "Mudflow"},
    HAZARD_FLOOD: {"ru": "Паводок", "ky": "Суу ташкыны", "en": "Flood"},
    HAZARD_AVALANCHE: {"ru": "Лавина", "ky": "Кар көчкү", "en": "Avalanche"},
    HAZARD_FIRE: {"ru": "Пожар", "ky": "Өрт", "en": "Fire"},
}

LEVEL_NAMES = {
    LEVEL_LOW: {"ru": "Низкий", "ky": "Төмөн", "en": "Low"},
    LEVEL_MEDIUM: {"ru": "Средний", "ky": "Орточо", "en": "Medium"},
    LEVEL_HIGH: {"ru": "Высокий", "ky": "Жогорку", "en": "High"},
    LEVEL_CRITICAL: {"ru": "Критический", "ky": "Өтө коркунучтуу", "en": "Critical"},
}

LEVEL_EMOJI = {LEVEL_LOW: "🟢", LEVEL_MEDIUM: "🟡", LEVEL_HIGH: "🟠", LEVEL_CRITICAL: "🔴"}
HAZARD_EMOJI = {HAZARD_MUDFLOW: "🌊", HAZARD_FLOOD: "💧", HAZARD_AVALANCHE: "🏔", HAZARD_FIRE: "🔥"}

ADVICE = {
    HAZARD_MUDFLOW: {
        "ru": "Немедленно уходите на возвышенность, подальше от русла реки. Звоните 112.",
        "ky": "Дароо бийик жерге чыгыңыз, дарыя нугунан алыс болуңуз. 112 номерине чалыңыз.",
        "en": "Move to high ground now, away from the river channel. Call 112.",
    },
    HAZARD_FLOOD: {
        "ru": "Отойдите от реки, поднимитесь выше, не переходите воду вброд. Звоните 112.",
        "ky": "Дарыядан алыс болуңуз, бийик жерге чыгыңыз, сууну кечпеңиз. 112 номерине чалыңыз.",
        "en": "Stay away from the river, move higher, never wade through water. Call 112.",
    },
    HAZARD_AVALANCHE: {
        "ru": "Не выезжайте на горные дороги и склоны, оставайтесь в безопасном месте.",
        "ky": "Тоо жолдоруна жана жантайыштарга чыкпаңыз, коопсуз жерде болуңуз.",
        "en": "Avoid mountain roads and slopes and stay in a safe place.",
    },
    HAZARD_FIRE: {
        "ru": "Уходите от огня против ветра и сообщите спасателям. Звоните 112.",
        "ky": "Өрттөн шамалга каршы четтеп кетиңиз, куткаруучуларга кабарлаңыз. 112 номерине чалыңыз.",
        "en": "Move away from the fire, upwind, and alert rescuers. Call 112.",
    },
}

WATCH_ADVICE = {
    "ru": "Будьте внимательны и следите за обновлениями.",
    "ky": "Этият болуңуз, жаңылыктарды көзөмөлдөңүз.",
    "en": "Stay alert and watch for updates.",
}

ETA_TEXT = {
    "ru": "Ожидаемое время прихода: ≈ {m} мин",
    "ky": "Болжолдуу келүү убактысы: ≈ {m} мүнөт",
    "en": "Expected to arrive in ≈ {m} min",
}
ETA_NOW = {"ru": "Уже совсем близко!", "ky": "Өтө жакын!", "en": "Imminent!"}
SAFE_POINT = {"ru": "Безопасное место", "ky": "Коопсуз жер", "en": "Safe point"}
VILLAGE_LABEL = {"ru": "Село", "ky": "Айыл", "en": "Village"}


def hazard_name(hazard, lang=DEFAULT_LANG):
    return HAZARD_NAMES.get(hazard, {}).get(lang) or HAZARD_NAMES.get(hazard, {}).get("en", hazard)


def level_name(level, lang=DEFAULT_LANG):
    return LEVEL_NAMES.get(level, {}).get(lang) or level


def build_alert_texts(hazard, level, village, eta_seconds=None, safe_point=None, simulated=False):
    """Return {lang: {"title": ..., "body": ...}} for all supported languages."""
    out = {}
    for lang in LANGS:
        prefix = "[DEMO] " if simulated else ""
        title = (
            f"{prefix}{HAZARD_EMOJI.get(hazard, '⚠️')} {hazard_name(hazard, lang)} — "
            f"{LEVEL_EMOJI.get(level, '')} {level_name(level, lang)}"
        )
        lines = [f"📍 {VILLAGE_LABEL[lang]}: {village.name_for(lang)}"]
        if eta_seconds is not None:
            if eta_seconds <= 30:
                lines.append(f"⏱ {ETA_NOW[lang]}")
            else:
                lines.append(f"⏱ {ETA_TEXT[lang].format(m=max(1, round(eta_seconds / 60)))}")
        if level in (LEVEL_HIGH, LEVEL_CRITICAL):
            lines.append(ADVICE.get(hazard, {}).get(lang, WATCH_ADVICE[lang]))
        else:
            lines.append(WATCH_ADVICE[lang])
        if safe_point is not None and level in (LEVEL_HIGH, LEVEL_CRITICAL):
            lines.append(
                f"🛟 {SAFE_POINT[lang]}: {safe_point.name} "
                f"https://maps.google.com/?q={safe_point.lat},{safe_point.lon}"
            )
        out[lang] = {"title": title, "body": "\n".join(lines)}
    return out
