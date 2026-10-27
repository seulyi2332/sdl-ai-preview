"""SQLite store for the compact compass app. Public demo: NOT durable or secure student storage."""
import json
import os
import sqlite3
import uuid
from datetime import datetime

DB_PATH=os.environ.get("SDL_AI_PREVIEW_DB","ai_preview_learning.db")
STATES=("시작 전","진행 중","도움 필요","완료","숨김")
MARKS=("어려움","흥미","핵심","질문")


def now():
    return datetime.now().isoformat(timespec="seconds")


def ident():
    return uuid.uuid4().hex


def connect():
    con=sqlite3.connect(DB_PATH,timeout=20,isolation_level=None)
    con.row_factory=sqlite3.Row
    con.execute("PRAGMA busy_timeout=20000")
    con.execute("""CREATE TABLE IF NOT EXISTS demo_goals (
        id TEXT PRIMARY KEY, owner TEXT NOT NULL, title TEXT NOT NULL,
        parent TEXT NOT NULL DEFAULT '',period TEXT NOT NULL DEFAULT '',
        state TEXT NOT NULL DEFAULT 'active',created TEXT NOT NULL)""")
    con.execute("""CREATE TABLE IF NOT EXISTS demo_tasks (
        id TEXT PRIMARY KEY,owner TEXT NOT NULL,title TEXT NOT NULL,
        goal_id TEXT NOT NULL DEFAULT '',day TEXT NOT NULL DEFAULT '',
        done INTEGER NOT NULL DEFAULT 0,created TEXT NOT NULL)""")
    con.execute("""CREATE TABLE IF NOT EXISTS demo_practice (
        id TEXT PRIMARY KEY,owner TEXT NOT NULL,course TEXT,topic TEXT,
        strategy TEXT,student_work TEXT,created TEXT NOT NULL)""")
    con.execute("""CREATE TABLE IF NOT EXISTS demo_diaries (
        id TEXT PRIMARY KEY,owner TEXT NOT NULL,original TEXT NOT NULL,
        briefing TEXT NOT NULL,analysis TEXT NOT NULL,created TEXT NOT NULL)""")
    con.execute("""CREATE TABLE IF NOT EXISTS compass_tasks (
        id TEXT PRIMARY KEY,owner TEXT NOT NULL,title TEXT NOT NULL,
        goal_id TEXT NOT NULL DEFAULT '',day TEXT NOT NULL DEFAULT '',
        status TEXT NOT NULL DEFAULT '시작 전',note TEXT NOT NULL DEFAULT '',
        created TEXT NOT NULL)""")
    con.execute("""CREATE TABLE IF NOT EXISTS compass_materials (
        id TEXT PRIMARY KEY,owner TEXT NOT NULL,title TEXT NOT NULL,
        pdf BLOB NOT NULL,paragraphs TEXT NOT NULL,page_count INTEGER NOT NULL,
        created TEXT NOT NULL)""")
    con.execute("""CREATE TABLE IF NOT EXISTS compass_marks (
        id TEXT PRIMARY KEY,owner TEXT NOT NULL,material_id TEXT NOT NULL,
        paragraph_id TEXT NOT NULL,kind TEXT NOT NULL,text TEXT NOT NULL,
        note TEXT NOT NULL DEFAULT '',state TEXT NOT NULL DEFAULT 'active',
        created TEXT NOT NULL,UNIQUE(owner,material_id,paragraph_id,kind))""")
    con.execute("""CREATE TABLE IF NOT EXISTS compass_chat (
        id TEXT PRIMARY KEY,owner TEXT NOT NULL,course TEXT NOT NULL DEFAULT '',
        role TEXT NOT NULL,text TEXT NOT NULL,created TEXT NOT NULL)""")
    con.execute("""CREATE TABLE IF NOT EXISTS compass_selfcheck (
        id TEXT PRIMARY KEY,owner TEXT NOT NULL,goal_id TEXT NOT NULL,
        evaluation TEXT NOT NULL,memo TEXT NOT NULL,created TEXT NOT NULL)""")
    return con


def all_rows(db,sql,args=()):
    return [dict(x) for x in db.execute(sql,args).fetchall()]


def task_rows(db,owner,include_hidden=False):
    where="" if include_hidden else " AND status!='숨김'"
    return all_rows(db,"SELECT * FROM compass_tasks WHERE owner=?"+where+
                    " ORDER BY CASE WHEN day='' THEN 1 ELSE 0 END, day, created DESC",(owner,))


def migrate_tasks(db,owner):
    for t in all_rows(db,"SELECT * FROM demo_tasks WHERE owner=?",(owner,)):
        db.execute("""INSERT OR IGNORE INTO compass_tasks
          (id,owner,title,goal_id,day,status,note,created) VALUES(?,?,?,?,?,?,?,?)""",
          (t["id"],owner,t["title"],t["goal_id"],t["day"],
           "완료" if t["done"] else "시작 전","",t["created"]))


def add_task(db,owner,title,day="",goal_id="",status="시작 전",note=""):
    if status not in STATES or not title.strip():
        raise ValueError("잘못된 할 일 입력")
    tid=ident()
    db.execute("INSERT INTO compass_tasks VALUES(?,?,?,?,?,?,?,?)",
               (tid,owner,title.strip(),goal_id,day,status,note.strip(),now()))
    return tid


def change_task(db,owner,tid,status):
    if status not in STATES:
        raise ValueError("알 수 없는 상태")
    db.execute("UPDATE compass_tasks SET status=? WHERE id=? AND owner=?",
               (status,tid,owner))


def add_material(db,owner,title,data,paragraphs,pages):
    mid=ident()
    db.execute("INSERT INTO compass_materials VALUES(?,?,?,?,?,?,?)",
               (mid,owner,title,data,json.dumps(paragraphs,ensure_ascii=False),pages,now()))
    return mid


def material_rows(db,owner):
    return all_rows(db,"SELECT id,title,page_count,created FROM compass_materials WHERE owner=? ORDER BY created DESC",(owner,))


def get_material(db,owner,mid):
    row=db.execute("SELECT * FROM compass_materials WHERE owner=? AND id=?",(owner,mid)).fetchone()
    return dict(row) if row else None


def put_mark(db,owner,mid,paragraph_id,kind,content,note=""):
    if kind not in MARKS:
        raise ValueError("알 수 없는 표시")
    db.execute("""INSERT INTO compass_marks
        (id,owner,material_id,paragraph_id,kind,text,note,state,created)
        VALUES(?,?,?,?,?,?,?,'active',?)
        ON CONFLICT(owner,material_id,paragraph_id,kind)
        DO UPDATE SET note=excluded.note,text=excluded.text,state='active'""",
       (ident(),owner,mid,paragraph_id,kind,content[:1600],note[:400],now()))


def marks(db,owner,kind=None,include_hidden=False):
    query="SELECT m.*,d.title AS material_title FROM compass_marks m JOIN compass_materials d ON d.id=m.material_id AND d.owner=m.owner WHERE m.owner=?"
    params=[owner]
    if kind:
        query+=" AND m.kind=?"
        params.append(kind)
    if not include_hidden:
        query+=" AND m.state!='hidden'"
    query+=" ORDER BY m.created DESC"
    return all_rows(db,query,tuple(params))


def mark_status(db,owner,mid,status):
    if status not in ("active","resolved","hidden"):
        raise ValueError("표시 상태 오류")
    db.execute("UPDATE compass_marks SET state=? WHERE id=? AND owner=?",(status,mid,owner))


def chat_messages(db,owner,course="",limit=10):
    data=all_rows(db,"SELECT role,text FROM compass_chat WHERE owner=? AND course=? ORDER BY created DESC,id DESC LIMIT ?",
                  (owner,course,limit))
    return list(reversed(data))


def put_chat(db,owner,course,role,text):
    if role not in ("user","assistant"):
        raise ValueError("잘못된 대화 역할")
    db.execute("INSERT INTO compass_chat VALUES(?,?,?,?,?,?)",
               (ident(),owner,course,role,text[:12000],now()))
