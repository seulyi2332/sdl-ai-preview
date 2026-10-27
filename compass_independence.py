"""Student-selected strategies and optional AI support.

A count of independent selections is an interaction trace, not a competency
score or evidence of achieved learning independence.
"""
from compass_store import all_rows,ident,now
from sdl_upgrade.strategies import CATALOG


def ensure(db):
    db.execute("""CREATE TABLE IF NOT EXISTS compass_strategy_choices(
       id TEXT PRIMARY KEY,owner TEXT NOT NULL,course TEXT NOT NULL,
       topic TEXT NOT NULL DEFAULT '',strategy_id TEXT NOT NULL,
       choice_source TEXT NOT NULL,created TEXT NOT NULL)""")


def choice(db,owner,course,topic,strategy_id,source):
    """Record only an explicit learner click, never auto-select."""
    ensure(db)
    if strategy_id not in {s["id"] for s in CATALOG}:
        raise ValueError("목록에 없는 학습방법이에요.")
    if source not in ("student","ai_suggestion"):
        raise ValueError("학습방법 선택 경로가 올바르지 않아요.")
    db.execute("INSERT INTO compass_strategy_choices VALUES(?,?,?,?,?,?,?)",
       (ident(),owner,course[:160],topic[:180],strategy_id,source,now()))


def recent(db,owner,course=None,limit=4):
    ensure(db)
    if course:
        rows=all_rows(db,"""SELECT * FROM compass_strategy_choices
           WHERE owner=? AND course=? ORDER BY created DESC,rowid DESC LIMIT ?""",
           (owner,course,limit))
    else:
        rows=all_rows(db,"""SELECT * FROM compass_strategy_choices
           WHERE owner=? ORDER BY created DESC,rowid DESC LIMIT ?""",(owner,limit))
    catalog={s["id"]:s for s in CATALOG}
    return [{**r,"name":catalog[r["strategy_id"]]["name"]}
            for r in rows if r["strategy_id"] in catalog]


def student_chosen_card(strategy_id):
    for s in CATALOG:
        if s["id"]==strategy_id:
            return {**s,"source":"student_selected","reason":"내가 직접 선택한 공부 방법이에요.",
                    "task_prompt":"","example":""}
    raise ValueError("찾을 수 없는 학습방법이에요.")
