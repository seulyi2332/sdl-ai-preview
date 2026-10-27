"""Regression tests: goal-linked self checks, diary evidence and graduated AI hints."""
import json
import os
import sqlite3
import tempfile
import unittest
from types import SimpleNamespace

import compass_store
from compass_selfcheck_links import latest_for_goal,recent_with_goals
from compass_diary_dialogue import context_for,ensure as ensure_diary,reply_for,messages,add
from compass_scaffold import ensure as ensure_scaffold,make_step,session_for,steps_for
from compass_store import ident,now,add_material,put_mark,save_interest


class FakeResponses:
    def __init__(self,payload):
        self.payload=payload
        self.calls=[]
    def create(self,**kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(output_text=json.dumps(self.payload,ensure_ascii=False))


class FlowTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.before=compass_store.DB_PATH
        compass_store.DB_PATH=os.path.join(self.temp.name,"learn.db")
        self.db=compass_store.connect()
        self.goal=ident()
        self.diary=ident()
        self.db.execute("INSERT INTO demo_goals VALUES(?,?,?,?,?,?,?)",
            (self.goal,"S01","기억과 망각을 설명하기","","이번 주","active",now()))
        self.db.execute("INSERT INTO demo_diaries VALUES(?,?,?,?,?,?)",
            (self.diary,"S01","기억의 원리가 재미있고 실생활에 쓰일 것 같아요.","","{}",now()))
        self.db.execute("INSERT INTO compass_selfcheck VALUES(?,?,?,?,?,?)",
            (ident(),"S01",self.goal,"조정이 필요하다","망각 개념의 예시가 아직 부족해요",now()))

    def tearDown(self):
        self.db.close()
        compass_store.DB_PATH=self.before
        self.temp.cleanup()

    def test_selfcheck_shows_in_goal_and_records_without_changing_goal(self):
        latest=latest_for_goal(self.db,"S01",self.goal)
        self.assertEqual("조정이 필요하다",latest["evaluation"])
        records=recent_with_goals(self.db,"S01")
        self.assertEqual("기억과 망각을 설명하기",records[0]["goal_title"])
        self.assertIn("예시",records[0]["memo"])
        self.assertIsNone(latest_for_goal(self.db,"S02",self.goal))
        self.assertEqual([],recent_with_goals(self.db,"S02"))
        self.assertEqual("active",self.db.execute(
            "SELECT state FROM demo_goals WHERE id=?",(self.goal,)).fetchone()["state"])

    def test_dialogue_context_reuses_only_students_own_records(self):
        save_interest(self.db,"S01","심리학")
        m=add_material(self.db,"S01","강의자료.pdf",b"demo",[],1)
        put_mark(self.db,"S01",m,"p1-0","흥미","기억의 원리가 생활에 연결됨")
        self.db.execute("INSERT INTO demo_practice VALUES(?,?,?,?,?,?,?)",
            (ident(),"S01","심리학개론","망각","teach_back",
             '{"work":{"response":"친구에게 설명하려고 해 봄"}}',now()))
        c=context_for(self.db,"S01",self.diary)
        self.assertEqual("심리학",c["student_selected_interest"])
        self.assertEqual("흥미",c["student_marked_passages"][0]["category"])
        self.assertEqual("조정이 필요하다",c["student_self_evaluations"][0]["evaluation"])
        stub=FakeResponses({"reply":"기억이 실생활과 연결된다고 느꼈군요. 어떤 사례가 떠올랐나요?"})
        reply=reply_for(self.db,"S01",self.diary,SimpleNamespace(responses=stub),"gpt-4o-mini")
        self.assertIn("사례",reply)
        inp=stub.calls[0]["input"][0]["content"]
        self.assertIn("기억의 원리가 재미있고",inp)
        self.assertIn("심리학",inp)
        ensure_diary(self.db)
        add(self.db,"S01",self.diary,"assistant",reply)
        self.assertEqual(1,len(messages(self.db,"S01",self.diary)))
        self.assertEqual([],messages(self.db,"S02",self.diary))
        with self.assertRaises(ValueError):
            context_for(self.db,"S02",self.diary)

    def test_scaffold_help_is_explicitly_staged(self):
        ensure_scaffold(self.db)
        sid=ident()
        self.db.execute("INSERT INTO compass_scaffold_sessions VALUES(?,?,?,?,?,?,?,?)",
            (sid,"S01","경제학","기회비용","공부 선택의 비용 계산",
             "돈이 안 드니 기회비용은 0일 것 같아요.","포기한 대안 중 최대 가치",now()))
        stub=FakeResponses({"feedback":"돈을 쓰는 것 외에도 포기하는 선택이 있지 않을까요?"})
        result=make_step(SimpleNamespace(responses=stub),"gpt-4o-mini",
                         session_for(self.db,"S01",sid),1,[])
        self.assertIn("선택",result)
        payload=stub.calls[0]["input"][0]["content"]
        self.assertIn('"help_step": 1',payload)
        self.assertIn("기회비용",payload)
        self.assertEqual([],steps_for(self.db,"S01",sid))
        self.assertIsNone(session_for(self.db,"S02",sid))
        with self.assertRaises(ValueError):
            make_step(None,"gpt-4o-mini",session_for(self.db,"S01",sid),1,[])


if __name__=="__main__":
    unittest.main()
