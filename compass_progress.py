"""Optional, student-owned evidence for goal criteria, task time comparison and revisions.

Do not infer SDL competency or goal achievement from checkboxes or minutes.
"""
import sqlite3
from compass_store import all_rows,ident,now


def ensure(db):
    db.execute("""CREATE TABLE IF NOT EXISTS compass_goal_criteria(
         owner TEXT NOT NULL,goal_id TEXT NOT NULL,criterion TEXT NOT NULL DEFAULT '',
         updated TEXT NOT NULL,PRIMARY KEY(owner,goal_id))""")
    db.execute("""CREATE TABLE IF NOT EXISTS compass_time_observations(
         id TEXT PRIMARY KEY,owner TEXT NOT NULL,task_id TEXT NOT NULL,
         estimated INTEGER,actual INTEGER,reason TEXT NOT NULL DEFAULT '',
         next_minutes INTEGER,created TEXT NOT NULL)""")
    db.execute("""CREATE TABLE IF NOT EXISTS compass_adjustments(
         id TEXT PRIMARY KEY,owner TEXT NOT NULL,goal_id TEXT NOT NULL,
         before_text TEXT NOT NULL,after_text TEXT NOT NULL,reason TEXT NOT NULL,
         created TEXT NOT NULL)""")


def criterion_for(db,owner,goal_id):
    ensure(db)
    row=db.execute("SELECT criterion FROM compass_goal_criteria WHERE owner=? AND goal_id=?",
                   (owner,goal_id)).fetchone()
    return str(row["criterion"]) if row else ""


def save_criterion(db,owner,goal_id,criterion):
    ensure(db)
    if not db.execute("SELECT id FROM demo_goals WHERE owner=? AND id=?",(owner,goal_id)).fetchone():
        raise ValueError("이 목표를 찾을 수 없어요.")
    db.execute("""INSERT INTO compass_goal_criteria(owner,goal_id,criterion,updated)
              VALUES(?,?,?,?) ON CONFLICT(owner,goal_id)
              DO UPDATE SET criterion=excluded.criterion,updated=excluded.updated""",
              (owner,goal_id,criterion.strip()[:850],now()))


def save_time(db,owner,task_id,estimated=None,actual=None,reason="",next_minutes=None):
    """Only explicitly entered measurements, never a guessed timer or grade."""
    ensure(db)
    if not db.execute("SELECT id FROM compass_tasks WHERE owner=? AND id=?",
                      (owner,task_id)).fetchone():
        raise ValueError("이 할 일을 찾을 수 없어요.")
    entries=(estimated,actual,next_minutes)
    if all(x is None for x in entries):
        raise ValueError("시간을 하나 이상 기록해 주세요.")
    if any(x is not None and (type(x) is not int or x<0 or x>1440) for x in entries):
        raise ValueError("시간은 0~1440분 사이에서 직접 입력할 수 있어요.")
    oid=ident()
    db.execute("""INSERT INTO compass_time_observations
          (id,owner,task_id,estimated,actual,reason,next_minutes,created)
          VALUES(?,?,?,?,?,?,?,?)""",
          (oid,owner,task_id,estimated,actual,reason.strip()[:800],next_minutes,now()))
    return oid


def latest_time(db,owner,task_id):
    ensure(db)
    row=db.execute("""SELECT * FROM compass_time_observations
                WHERE owner=? AND task_id=? ORDER BY created DESC,id DESC LIMIT 1""",
                (owner,task_id)).fetchone()
    return dict(row) if row else None


def time_summaries(db,owner,limit=7):
    ensure(db)
    return all_rows(db,"""SELECT t.title,c.estimated,c.actual,c.reason,c.next_minutes,c.created
        FROM compass_time_observations c JOIN compass_tasks t
          ON t.id=c.task_id AND t.owner=c.owner
        WHERE c.owner=? ORDER BY c.created DESC,c.id DESC LIMIT ?""",(owner,limit))


def revise_goal(db,owner,goal_id,new_title,reason):
    ensure(db)
    if not new_title.strip() or not reason.strip():
        raise ValueError("바꾸려는 내용과 학생이 생각한 이유를 적어 주세요.")
    previous=db.execute("SELECT title FROM demo_goals WHERE owner=? AND id=?",(owner,goal_id)).fetchone()
    if not previous:
        raise ValueError("이 목표를 찾을 수 없어요.")
    earlier=str(previous["title"])
    if earlier==new_title.strip():
        raise ValueError("목표 제목에 변경된 내용이 없어요.")
    with db:
        db.execute("UPDATE demo_goals SET title=? WHERE owner=? AND id=?",
                   (new_title.strip()[:300],owner,goal_id))
        db.execute("""INSERT INTO compass_adjustments
            (id,owner,goal_id,before_text,after_text,reason,created)
            VALUES(?,?,?,?,?,?,?)""",
            (ident(),owner,goal_id,earlier,new_title.strip()[:300],reason.strip()[:850],now()))


def adjustments(db,owner,goal_id=None):
    ensure(db)
    if goal_id:
        return all_rows(db,"SELECT * FROM compass_adjustments WHERE owner=? AND goal_id=? ORDER BY created DESC",
                        (owner,goal_id))
    return all_rows(db,"SELECT * FROM compass_adjustments WHERE owner=? ORDER BY created DESC",(owner,))
