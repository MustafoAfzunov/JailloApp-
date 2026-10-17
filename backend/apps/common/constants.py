"""Shared constants: hazards, risk levels, languages."""

HAZARD_MUDFLOW = "mudflow"
HAZARD_FLOOD = "flood"
HAZARD_AVALANCHE = "avalanche"
HAZARD_FIRE = "fire"

HAZARD_CHOICES = [
    (HAZARD_MUDFLOW, "Mudflow"),
    (HAZARD_FLOOD, "Flood"),
    (HAZARD_AVALANCHE, "Avalanche"),
    (HAZARD_FIRE, "Fire"),
]
HAZARDS = [h for h, _ in HAZARD_CHOICES]

LEVEL_LOW = "low"
LEVEL_MEDIUM = "medium"
LEVEL_HIGH = "high"
LEVEL_CRITICAL = "critical"

LEVEL_CHOICES = [
    (LEVEL_LOW, "Low"),
    (LEVEL_MEDIUM, "Medium"),
    (LEVEL_HIGH, "High"),
    (LEVEL_CRITICAL, "Critical"),
]
LEVEL_RANK = {LEVEL_LOW: 0, LEVEL_MEDIUM: 1, LEVEL_HIGH: 2, LEVEL_CRITICAL: 3}

LANG_CHOICES = [("ru", "Русский"), ("ky", "Кыргызча"), ("en", "English")]
DEFAULT_LANG = "ru"
LANGS = [code for code, _ in LANG_CHOICES]


def level_from_score(score: float) -> str:
    """Map a 0-100 risk score to a level."""
    if score >= 75:
        return LEVEL_CRITICAL
    if score >= 50:
        return LEVEL_HIGH
    if score >= 25:
        return LEVEL_MEDIUM
    return LEVEL_LOW


def max_level(levels) -> str:
    return max(levels, key=lambda lv: LEVEL_RANK[lv], default=LEVEL_LOW)


def pick_lang(value) -> str:
    return value if value in LANGS else DEFAULT_LANG
