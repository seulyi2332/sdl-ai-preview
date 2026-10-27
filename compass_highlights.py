"""Student-owned PDF difficulty keywords and highlight navigation.

A keyword is an editable snippet of what the student actually selected, not an
AI diagnosis, extracted concept mastery or automated importance rating.
"""
import re
from compass_store import all_rows,now


def ensure(db):
    existing={r["name"] for r in db.execute("PRAGMA table_info(compass_marks)")}
    if "keyword" not in existing:
        db.execute("ALTER TABLE compass_marks ADD COLUMN keyword TEXT NOT NULL DEFAULT ''")


def extract_label(text,max_chars=34):
    """Use the first short phrase actually present in the source quotation."""
    cleaned=re.sub(r"\s+"," ",str(text or "")).strip()
    cleaned=re.sub(r"^[\s\-•·▪○■\d.)]+","",cleaned)
    if not cleaned:
        return "표시한 어려움"
    fragment=re.split(r"(?<=[.!?。])\s+",cleaned,1)[0]
    fragment=fragment[:max_chars+8]
    words=fragment.split()
    if len(words)>1:
        fragment=" ".join(words[:min(5,len(words))])
    if len(fragment)>max_chars:
        fragment=fragment[:max_chars].rstrip()+"…"
    return fragment


def difficulty_items(db,owner,limit=8):
    ensure(db)
    return all_rows(db,"""SELECT m.id,m.text,m.note,m.keyword,m.material_id,
           m.paragraph_id,m.created,d.title AS material_title
           FROM compass_marks m JOIN compass_materials d
            ON d.id=m.material_id AND d.owner=m.owner
           WHERE m.owner=? AND m.kind='어려움' AND m.state='active'
           ORDER BY m.created DESC,m.rowid DESC LIMIT ?""",(owner,limit))


def label(item):
    user_label=str(item.get("keyword") or "").strip()
    return user_label if user_label else extract_label(item.get("text") or "")


def set_label(db,owner,mark_id,keyword):
    ensure(db)
    item=db.execute("""SELECT id FROM compass_marks
         WHERE id=? AND owner=? AND kind='어려움'""",(mark_id,owner)).fetchone()
    if not item:
        raise ValueError("본인이 표시한 어려움이 아니에요.")
    normalized=" ".join(str(keyword or "").split())[:65]
    db.execute("UPDATE compass_marks SET keyword=? WHERE id=? AND owner=?",
               (normalized,mark_id,owner))
    return normalized
