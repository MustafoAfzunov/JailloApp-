"""Telegram update handlers (called by the `run_bot` polling command)."""
import logging

from apps.accounts.models import User
from apps.accounts.phone import normalize_phone
from apps.accounts.services import get_or_create_user
from apps.alerts.models import Alert
from apps.common import telegram
from apps.common.constants import HAZARDS, LEVEL_LOW, max_level, pick_lang
from apps.common.messages import LEVEL_EMOJI, hazard_name, level_name
from apps.geo.models import Village
from apps.reports.models import HazardReport
from apps.reports.services import create_report

from .models import BotSession
from .texts import REPORT_TYPES, all_labels, tr

log = logging.getLogger(__name__)


# ---------------------------------------------------------------- keyboards
def _share_keyboard(lang):
    return {
        "keyboard": [[{"text": tr(lang, "share"), "request_contact": True}]],
        "resize_keyboard": True,
        "one_time_keyboard": True,
    }


def _menu(lang):
    return {
        "keyboard": [
            [{"text": tr(lang, "btn_risk")}, {"text": tr(lang, "btn_alerts")}],
            [{"text": tr(lang, "btn_report")}, {"text": tr(lang, "btn_language")}],
        ],
        "resize_keyboard": True,
    }


def _location_keyboard(lang):
    return {
        "keyboard": [[{"text": tr(lang, "send_location"), "request_location": True}], [{"text": tr(lang, "cancel")}]],
        "resize_keyboard": True,
        "one_time_keyboard": True,
    }


def _inline(rows):
    return {"inline_keyboard": rows}


def _say(chat_id, text, markup=None):
    return telegram.safe_send(chat_id, text, markup)


def _guess_lang(from_user):
    code = (from_user or {}).get("language_code", "")[:2]
    return code if code in ("ru", "ky", "en") else "ru"


# ---------------------------------------------------------------- entry point
def handle_update(update):
    if "callback_query" in update:
        return _handle_callback(update["callback_query"])
    msg = update.get("message")
    if not msg or msg.get("chat", {}).get("type") != "private":
        return None

    chat_id = msg["chat"]["id"]
    from_user = msg.get("from") or {}
    user = User.objects.filter(telegram_chat_id=chat_id).first()
    lang = user.language if user else _guess_lang(from_user)

    if "contact" in msg:
        return _handle_contact(chat_id, from_user, msg["contact"], lang)

    text = (msg.get("text") or "").strip()
    if text.startswith("/start"):
        return _say(chat_id, tr(lang, "welcome") + "\n\n" + tr(lang, "ask_share"), _share_keyboard(lang)) \
            if user is None else _say(chat_id, tr(lang, "welcome"), _menu(lang))
    if user is None:
        return _say(chat_id, tr(lang, "ask_share"), _share_keyboard(lang))

    if "location" in msg:
        return _handle_location(user, chat_id, msg["location"])
    if "photo" in msg:
        return _handle_photo(user, chat_id, msg["photo"])
    return _handle_text(user, chat_id, text)


# ---------------------------------------------------------------- handlers
def _handle_contact(chat_id, from_user, contact, lang):
    # only accept the sender's own number, never a forwarded contact card
    if contact.get("user_id") != from_user.get("id"):
        return _say(chat_id, tr(lang, "wrong_contact"), _share_keyboard(lang))
    try:
        phone = normalize_phone(contact.get("phone_number"))
    except ValueError:
        return _say(chat_id, tr(lang, "wrong_contact"), _share_keyboard(lang))

    name = " ".join(x for x in (contact.get("first_name"), contact.get("last_name")) if x)[:120]
    user, created = get_or_create_user(phone, name=name, language=lang)
    User.objects.filter(telegram_chat_id=chat_id).exclude(pk=user.pk).update(telegram_chat_id=None)
    user.telegram_chat_id = chat_id
    if not user.name and name:
        user.name = name
    user.save(update_fields=["telegram_chat_id", "name"])

    _say(chat_id, tr(user.language, "linked"), _menu(user.language))
    if user.village_id is None:
        _ask_village(chat_id, user.language)


def _ask_village(chat_id, lang):
    rows = [[{"text": v.name_for(lang), "callback_data": f"v:{v.pk}"}] for v in Village.objects.all()[:20]]
    if rows:
        _say(chat_id, tr(lang, "pick_village"), _inline(rows))


def _handle_text(user, chat_id, text):
    lang = user.language
    cmd = text.split()[0].split("@")[0].lower() if text.startswith("/") else ""

    if cmd == "/risk" or text in all_labels("btn_risk"):
        return _send_risk(user, chat_id)
    if cmd == "/alerts" or text in all_labels("btn_alerts"):
        return _send_alerts(user, chat_id)
    if cmd == "/report" or text in all_labels("btn_report"):
        session, _ = BotSession.objects.get_or_create(chat_id=chat_id)
        session.reset()
        rows = [[{"text": tr(lang, f"r_{t}"), "callback_data": f"rt:{t}"}] for t in REPORT_TYPES]
        return _say(chat_id, tr(lang, "report_pick"), _inline(rows))
    if cmd == "/village":
        return _ask_village(chat_id, lang)
    if cmd == "/language" or text in all_labels("btn_language"):
        rows = [[{"text": "Русский", "callback_data": "lang:ru"}, {"text": "Кыргызча", "callback_data": "lang:ky"},
                 {"text": "English", "callback_data": "lang:en"}]]
        return _say(chat_id, tr(lang, "lang_pick"), _inline(rows))
    if text in all_labels("cancel"):
        BotSession.objects.filter(chat_id=chat_id).update(state="", data={})
        return _say(chat_id, "OK", _menu(lang))
    return _say(chat_id, tr(lang, "help"), _menu(lang))


def _send_risk(user, chat_id):
    lang = user.language
    if user.village_id is None:
        return _ask_village(chat_id, lang)
    village = user.village
    levels = {a.hazard: a.level for a in village.assessments.all()}
    overall = max_level(levels.get(h, LEVEL_LOW) for h in HAZARDS)
    lines = [tr(lang, "risk_title", name=village.name_for(lang), level=f"{LEVEL_EMOJI[overall]} {level_name(overall, lang)}")]
    for h in HAZARDS:
        lv = levels.get(h, LEVEL_LOW)
        lines.append(f"{LEVEL_EMOJI[lv]} {hazard_name(h, lang)}: {level_name(lv, lang)}")
    return _say(chat_id, "\n".join(lines))


def _send_alerts(user, chat_id):
    lang = user.language
    qs = Alert.objects.filter(status=Alert.ACTIVE).select_related("village")
    if not user.is_rescuer and user.village_id:
        qs = qs.filter(village_id=user.village_id)
    alerts = list(qs[:10])
    if not alerts:
        return _say(chat_id, tr(lang, "no_alerts"))
    parts = [tr(lang, "alerts_title")]
    for a in alerts:
        t = a.texts.get(lang) or a.texts.get("ru") or {}
        parts.append(f"{t.get('title', '')}\n{t.get('body', '')}")
    return _say(chat_id, "\n\n".join(parts))


def _handle_photo(user, chat_id, photos):
    session, _ = BotSession.objects.get_or_create(chat_id=chat_id)
    if session.state != "report_location":
        return _say(chat_id, tr(user.language, "need_type"), _menu(user.language))
    session.data = {**session.data, "photo_file_id": photos[-1]["file_id"]}
    session.save()
    return _say(chat_id, tr(user.language, "photo_saved"), _location_keyboard(user.language))


def _handle_location(user, chat_id, location):
    lang = user.language
    session, _ = BotSession.objects.get_or_create(chat_id=chat_id)
    if session.state != "report_location":
        return _say(chat_id, tr(lang, "need_type"), _menu(lang))

    photo = None
    file_id = session.data.get("photo_file_id")
    if file_id:
        try:
            photo = telegram.get_file_bytes(file_id)
        except telegram.TelegramError as exc:
            log.warning("could not download report photo: %s", exc)
    create_report(
        user, session.data.get("type", HazardReport.OTHER),
        location["latitude"], location["longitude"], photo_bytes=photo, source="telegram",
    )
    session.reset()
    return _say(chat_id, tr(lang, "report_thanks"), _menu(lang))


def _handle_callback(cb):
    chat_id = cb["message"]["chat"]["id"]
    data = cb.get("data", "")
    user = User.objects.filter(telegram_chat_id=chat_id).first()
    if user is None:
        return None
    lang = user.language
    try:
        telegram.answer_callback(cb["id"])
    except telegram.TelegramError:
        pass

    if data.startswith("v:") and data[2:].isdigit():
        village = Village.objects.filter(pk=int(data[2:])).first()
        if village:
            user.village = village
            user.save(update_fields=["village"])
            _say(chat_id, tr(lang, "village_set", name=village.name_for(lang)), _menu(lang))
    elif data.startswith("lang:"):
        new = pick_lang(data[5:])
        user.language = new
        user.save(update_fields=["language"])
        _say(chat_id, tr(new, "lang_set"), _menu(new))
    elif data.startswith("rt:") and data[3:] in REPORT_TYPES:
        session, _ = BotSession.objects.get_or_create(chat_id=chat_id)
        session.state, session.data = "report_location", {"type": data[3:]}
        session.save()
        _say(chat_id, tr(lang, "report_prompt"), _location_keyboard(lang))
    return None
