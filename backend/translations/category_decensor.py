from __future__ import annotations

import json
from typing import Any

from database import get_db, get_translation_workbench_item, upsert_translation, upsert_translation_workbench_item


DECENSOR_PAIRS: tuple[tuple[str, str], ...] = (
    ("A***e", "Abuse"),
    ("A****d", "Abused"),
    ("A****p", "Asleep"),
    ("A*****t", "Assault"),
    ("A******d", "Assaulted"),
    ("A*******g", "Assaulting"),
    ("B*****p", "Beat Up"),
    ("B**d", "Bled"),
    ("B******g", "Bleeding"),
    ("B***d", "Blood"),
    ("B*******y", "Brutality"),
    ("C***d", "Child"),
    ("C******n", "Children"),
    ("C*********a", "Coprophilia"),
    ("C***l", "Cruel"),
    ("C******y", "Cruelty"),
    ("D******e", "Disgrace"),
    ("D*******d", "Disgraced"),
    ("D***k", "Drunk"),
    ("D**g", "Drug"),
    ("D*****d", "Drugged"),
    ("D******g", "Drugging"),
    ("D***s", "Drugs"),
    ("E***************l", "Elementary School"),
    ("E******d", "Enforced"),
    ("F***e", "Force"),
    ("F****d", "Forced"),
    ("F******l", "Forceful"),
    ("F*****g", "Forcing"),
    ("G*******g", "Gang Bang"),
    ("G******g", "Gangbang"),
    ("H*********d", "Humiliated"),
    ("H**********g", "Humiliating"),
    ("H**********n", "Humiliation"),
    ("H***o", "Hypno"),
    ("H*******s", "Hypnosis"),
    ("H******c", "Hypnotic"),
    ("H*******m", "Hypnotism"),
    ("H********e", "Hypnotize"),
    ("H*********d", "Hypnotized"),
    ("I******l", "Illegal"),
    ("J***********h", "Junior High"),
    ("J******e", "Juvenile"),
    ("K*d", "Kid"),
    ("K****p", "Kidnap"),
    ("K**s", "Kids"),
    ("K**l", "Kill"),
    ("K****r", "Killer"),
    ("K*****g", "Killing"),
    ("K***********n", "Kindergarten"),
    ("L**i", "Loli"),
    ("L******n", "Lolicon"),
    ("L****a", "Lolita"),
    ("M***********l", "Mind Control"),
    ("M****t", "Molest"),
    ("M*********n", "Molestation"),
    ("M******d", "Molested"),
    ("M******r", "Molester"),
    ("M*******g", "Molesting"),
    ("M**************n", "Mother And Son"),
    ("N******y", "Nursery"),
    ("P*********t", "Passed Out"),
    ("P**********t", "Passing Out"),
    ("P**p", "Poop"),
    ("P********l", "Preschool"),
    ("P****h", "Punish"),
    ("P******d", "Punished"),
    ("P******r", "Punisher"),
    ("P*******g", "Punishing"),
    ("R**e", "Rape"),
    ("R***d", "Raped"),
    ("R***s", "Rapes"),
    ("R****g", "Raping"),
    ("R****t", "Rapist"),
    ("R*****s", "Rapists"),
    ("S**t", "Scat"),
    ("S*******y", "Scatology"),
    ("S*********l", "School Girl"),
    ("S**********s", "School Girls"),
    ("S********l", "Schoolgirl"),
    ("S*********s", "Schoolgirls"),
    ("S***a", "Shota"),
    ("S******n", "Shotacon"),
    ("S***e", "Slave"),
    ("S******g", "Sleeping"),
    ("S*****t", "Student"),
    ("S******s", "Students"),
    ("S*********n", "Submission"),
    ("T******e", "Tentacle"),
    ("T*******s", "Tentacles"),
    ("T******e", "Torture"),
    ("T*******d", "Tortured"),
    ("U**********s", "Unconscious"),
    ("U*******g", "Unwilling"),
    ("V******e", "Violate"),
    ("V*******d", "Violated"),
    ("V********n", "Violation"),
    ("V******e", "Violence"),
    ("V*****t", "Violent"),
    ("Y***********l", "Young Girl"),
)

MASKED_CATEGORY_REPAIRS: dict[str, tuple[str, str, tuple[str, ...]]] = {
    "29": ("Gang Bang", "群交", ("G*******g",)),
    "4121": ("Drunk Girl", "醉酒女孩", ("D***k Girl", "Drink Girl")),
    "5064": ("Hypnotism", "催眠", ("H*******m",)),
    "6122": ("Shotacon", "正太控", ("S******n",)),
    "6141": ("Gang Bang", "群交", ("G*******g",)),
}


def decensor_category_name(value: Any) -> str:
    text = str(value or "").strip()
    if "*" not in text:
        return text
    text = text.replace("D***k Girl", "Drunk Girl")
    for masked, replacement in DECENSOR_PAIRS:
        text = text.replace(masked, replacement)
    return text


def _json_mapping(raw: str | None) -> dict[str, str]:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except Exception:
        return {}
    if not isinstance(parsed, dict):
        return {}
    return {str(key): str(value) for key, value in parsed.items() if key and value}


def _remove_category_mapping_keys(category_id: str, source_keys: tuple[str, ...]) -> None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT category_json FROM translation_mappings WHERE content_id = ?",
            (f"category:{category_id}",),
        ).fetchone()
        if not row:
            return
        mapping = _json_mapping(row["category_json"])
        for key in source_keys:
            mapping.pop(key, None)
        conn.execute(
            "UPDATE translation_mappings SET category_json = ?, updated_at = CURRENT_TIMESTAMP WHERE content_id = ?",
            (json.dumps(mapping, ensure_ascii=False), f"category:{category_id}"),
        )


def _category_mapping(category_id: str) -> dict[str, str]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT category_json FROM translation_mappings WHERE content_id = ?",
            (f"category:{category_id}",),
        ).fetchone()
    return _json_mapping(row["category_json"]) if row else {}


def _has_polluted_translation(value: object) -> bool:
    return "*" in str(value or "")


def _category_needs_repair(
    category_id: str,
    source_text: str,
    translated_text: str,
    stale_sources: tuple[str, ...],
) -> bool:
    mapping = _category_mapping(category_id)
    if any(source in mapping for source in stale_sources):
        return True
    if _has_polluted_translation(mapping.get(source_text)):
        return True

    item = get_translation_workbench_item("category", category_id)
    if not item:
        return False
    item_source = str(item.get("source_text") or "")
    if item_source in stale_sources:
        return True
    if item_source == source_text and _has_polluted_translation(item.get("translated_text")):
        return True
    return False


def repair_masked_category_translations() -> list[str]:
    repaired: list[str] = []
    for category_id, (source_text, translated_text, stale_sources) in MASKED_CATEGORY_REPAIRS.items():
        if not _category_needs_repair(category_id, source_text, translated_text, stale_sources):
            continue
        item = get_translation_workbench_item("category", category_id)
        if item and item.get("status") in {"manual_edited", "reviewed"} and item.get("source_text") not in stale_sources:
            manual_source = str(item.get("source_text") or source_text)
            manual_translation = str(item.get("translated_text") or "")
            if manual_source == source_text and manual_translation and not _has_polluted_translation(manual_translation):
                upsert_translation(f"category:{category_id}", {"category": {manual_source: manual_translation}})
            _remove_category_mapping_keys(category_id, stale_sources)
            repaired.append(category_id)
            continue
        upsert_translation(f"category:{category_id}", {"category": {source_text: translated_text}})
        _remove_category_mapping_keys(category_id, stale_sources)
        upsert_translation_workbench_item(
            "category",
            category_id,
            source_text,
            translated_text=translated_text,
            status="machine_translated",
            provider="decensor_repair",
            model=None,
            attempts=0,
            last_error=None,
            scope=f"category:{category_id}",
            preserve_reviewed=False,
        )
        repaired.append(category_id)
    return repaired
