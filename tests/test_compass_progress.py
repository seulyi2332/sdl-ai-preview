"""Regression tests for learner autonomy, time reflection and optional AI feedback."""
import os
import tempfile
import unittest
from types import SimpleNamespace

TMP=tempfile.TemporaryDirectory()
os.environ["SDL_AI_PREVIEW_DB"]=os.path.join(TMP.name,"progress.db")

from compass_store import connect,add_task,task_rows
from compass_progress import (save_criterion,criterion_for,save_time,
                              latest_time,time_summaries,revise_goal,adjustments)
from compass_feedback import make_feedback


class FakeResponses:
    def __init__(self,output):
        self.output=output
        self.calls=[]
    def create(self,**kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(output_text=self.output)


class CompassProgressTests(unittest.TestCase):
    def setUp(self):
        self.db=connect()
        self.db.execute("DELETE FROM compass_tasks")
        self.db.execute("DELETE FROM demo_goals")
        for table in ("compass_goal_criteria","compass_time_observations","compass_adjustments"):
            self.db.execute(f"""CREATE TABLE IF NOT EXISTS {table}
               (id TEXT, owner TEXT, goal_id TEXT, PRIMARY KEY(id))""") if False else None

    def tearDown(self):
        self.db.close()

    def test_learner_goal_criterion_is_private(self):
        self.db.execute("INSERT INTO demo_goals VALUES(?,?,?,?,?,?,?)",
                        ("G01","S01","나의 비교 목표","","","active","2026-10-27"))
        save_criterion(self.db,"S01","G01","내 말로 개념 차이 설명")
        self.assertEqual("내 말로 개념 차이 설명",criterion_for(self.db,"S01","G01"))
        self.assertEqual("",criterion_for(self.db,"S02","G01"))
        with self.assertRaises(ValueError):
            save_criterion(self.db,"S02","G01","수정 시도")

    def test_time_is_not_completion_or_grade(self):
        task=add_task(self.db,"S01","심리학 개념 비교")
        save_time(self.db,"S01",task,estimated=30,actual=47,
                  reason="예시를 추가로 읽음",next_minutes=40)
        entry=latest_time(self.db,"S01",task)
        self.assertEqual(17,entry["actual"]-entry["estimated"])
        self.assertEqual(40,entry["next_minutes"])
        self.assertEqual([],time_summaries(self.db,"S02"))
        self.assertEqual("시작 전",task_rows(self.db,"S01")[0]["status"])
        with self.assertRaises(ValueError):
            save_time(self.db,"S02",task,estimated=5)
        with self.assertRaises(ValueError):
            save_time(self.db,"S01",task,estimated=-3)
        with self.assertRaises(ValueError):
            save_time(self.db,"S01",task)

    def test_student_must_supply_revision_and_reason(self):
        self.db.execute("INSERT INTO demo_goals VALUES(?,?,?,?,?,?,?)",
                        ("G02","S01","원래 목표","","","active","2026-10-27"))
        with self.assertRaises(ValueError):
            revise_goal(self.db,"S01","G02","변경 목표","")
        with self.assertRaises(ValueError):
            revise_goal(self.db,"S02","G02","변경 목표","내가 수정")
        revise_goal(self.db,"S01","G02","개념 예시 설명","내 공부 기록에서 막힌 점을 발견")
        self.assertEqual(1,len(adjustments(self.db,"S01","G02")))
        self.assertEqual([],adjustments(self.db,"S02"))
        self.assertEqual("개념 예시 설명",self.db.execute(
            "SELECT title FROM demo_goals WHERE owner='S01' AND id='G02'").fetchone()["title"])


class FeedbackTests(unittest.TestCase):
    def test_explicit_student_work_and_no_auto_scoring(self):
        responses=FakeResponses("이 비교표에서는 조건 구분이 잘되어 있어요. 원인 설명을 보완하면 좋아요.")
        client=SimpleNamespace(responses=responses)
        result=make_feedback(client,"gpt-4o-mini","경제학","기회비용","비교표 만들기",
                             {"left_work":"저는 기회비용이 0원이라고 생각해요."},
                             "기회비용은 포기한 대안 중 최대 가치.","보완할 점")
        self.assertIn("원인 설명",result)
        request=responses.calls[0]
        self.assertEqual("gpt-4o-mini",request["model"])
        self.assertFalse(request["store"])
        self.assertNotIn("temperature",request)
        self.assertIn("저는 기회비용",request["input"][0]["content"])
        self.assertIn("기회비용은 포기한 대안",request["input"][0]["content"])
        self.assertIn("자동",request["instructions"])


if __name__=="__main__":
    unittest.main()
