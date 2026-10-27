"""Regression: embed exploration across SDL stages, protect participant notes."""
import os
import tempfile
import unittest
from types import SimpleNamespace

TMP=tempfile.TemporaryDirectory()
os.environ["SDL_AI_PREVIEW_DB"]=os.path.join(TMP.name,"major_links.sqlite")

from compass_store import connect,add_material,put_mark
from compass_major_links import (save_link,linked_rows,update_reflection,
      interest_excerpts,ask_ai)

class FakeResponses:
    def __init__(self):self.calls=[]
    def create(self,**kw):
        self.calls.append(kw)
        return SimpleNamespace(output_text="교과목의 개념을 관련 학문과 연결해 보고 공식 교육과정을 확인해 보세요.")

class MajorLinkTests(unittest.TestCase):
    def setUp(self):self.db=connect()
    def tearDown(self):self.db.close()

    def test_course_link_and_student_reflection_belong_to_one_owner(self):
        rid=save_link(self.db,"S01","경제학개론","기회비용","포기한 대안의 가치",
             "선택의 기준을 궁금해함","경제학","전공에서 어떤 사례를 분석하나요?")
        self.assertEqual(1,len(linked_rows(self.db,"S01")))
        self.assertFalse(linked_rows(self.db,"S02"))
        with self.assertRaises(ValueError):
            update_reflection(self.db,"S02",rid,"다른 학생 글","내용","실행")
        update_reflection(self.db,"S01",rid,"기회비용을 전공 수업에서도 분석할 수 있다는 점",
              "실제 전공 과목에서 어떤 응용을 다루는지","공식 전공 교육과정 확인")
        x=linked_rows(self.db,"S01")[0]
        self.assertIn("공식 전공",x["next_action"])
        self.assertIn("기회비용",x["learned"])

    def test_student_interest_not_confused_with_factual_major_fit(self):
        raw=b"public demo material"
        mid=add_material(self.db,"S03","예시자료.pdf",raw,[],1)
        put_mark(self.db,"S03",mid,"p1-0","흥미","기억을 스스로 점검하는 방법")
        put_mark(self.db,"S03",mid,"p1-1","어려움","추가 설명이 필요한 개념")
        records=interest_excerpts(self.db,"S03")
        self.assertEqual(1,len(records))
        self.assertIn("기억",records[0]["text"])
        self.assertFalse(interest_excerpts(self.db,"S04"))

    def test_optional_ai_explains_and_never_auto_saves_decisions(self):
        client=SimpleNamespace(responses=FakeResponses())
        v=ask_ai(client,"gpt-4o-mini","심리학개론","기억","기억과 학습","심리학",
                 "전공 교과목은 무엇을 배우나요?","흥미가 생겼어요")
        self.assertIn("교과목",v)
        data=client.responses.calls[0]
        self.assertFalse(data["store"])
        self.assertIn("전공",data["instructions"])
        self.assertIn("적합도",data["instructions"])
        self.assertFalse(linked_rows(self.db,"S05"))
        with self.assertRaises(ValueError):
            save_link(self.db,"S05","","","","","","")

class EmbeddedScreensTests(unittest.TestCase):
    def test_same_five_tabs_and_integrated_stage_prompts(self):
        from streamlit.testing.v1 import AppTest
        conn=connect()
        save_link(conn,"S09","심리학개론","기억","기억과 학습",
                  "왜 기억이 달라지는지 궁금해요","심리학","전공에서 어떻게 연구할까요?")
        conn.close()
        root=os.path.dirname(os.path.dirname(__file__))
        app=AppTest.from_file(os.path.join(root,"ai_preview_app.py"),default_timeout=65).run()
        app.text_input(key="participant_access_code").set_value("S09").run()
        self.assertFalse(app.exception,[str(e.message) for e in app.exception])
        self.assertTrue(any("교과목에서 시작한 나의 전공" in str(m.value) for m in app.caption))
        nav=app.radio(key="compass_page")
        self.assertEqual(("오늘","목표와 계획","공부하기","학습일지","내 기록"),tuple(nav.options))
        app.radio(key="compass_page").set_value("목표와 계획").run()
        self.assertFalse(app.exception,[str(e.message) for e in app.exception])
        self.assertTrue(any("교과목 학습과 나의 관심 전공" in x.label for x in app.expander))
        self.assertTrue(any("교과목에서 생긴 관심" in m.value for m in app.markdown))
        app.radio(key="compass_page").set_value("공부하기").run()
        self.assertFalse(app.exception,[str(e.message) for e in app.exception])
        self.assertTrue(any("전공과 진로" in x.label for x in app.expander))
        app.radio(key="compass_page").set_value("학습일지").run()
        self.assertFalse(app.exception,[str(e.message) for e in app.exception])
        self.assertTrue(any("관심 전공에 대해 알게 된 점" in x.label for x in app.expander))

if __name__=="__main__":
    unittest.main()
