"""Tests for 60 study cards, student-owned highlight keywords and short UI flow."""
import os
import tempfile
import unittest
TMP=tempfile.TemporaryDirectory()
os.environ["SDL_AI_PREVIEW_DB"]=os.path.join(TMP.name,"compass_keyword_test.sqlite")

from compass_store import connect,add_material,put_mark,mark_status
from compass_highlights import difficulty_items,extract_label,label,set_label
from compass_strategy_cards import filtered_cards,PER_PAGE
from sdl_upgrade.strategies import CATALOG,GROUPS,GROUP_BY_ID


class KeywordTests(unittest.TestCase):
    def setUp(self):
        self.db=connect()

    def tearDown(self):
        self.db.close()

    def test_source_based_label_student_edit_and_owner_isolation(self):
        material=add_material(self.db,"S01","공개 경제학 자료.pdf",b"example",[],1)
        put_mark(self.db,"S01",material,"p1-0","어려움","기회비용은 선택에서 포기한 대안의 가치이다.")
        item=difficulty_items(self.db,"S01")[0]
        self.assertIn("기회비용",label(item))
        self.assertNotIn("진단",label(item))
        self.assertEqual([],difficulty_items(self.db,"S02"))
        with self.assertRaises(ValueError):
            set_label(self.db,"S02",item["id"],"다른 학생 기록 수정")
        set_label(self.db,"S01",item["id"],"기회비용 개념이 어려움")
        self.assertEqual("기회비용 개념이 어려움",label(difficulty_items(self.db,"S01")[0]))
        mark_status(self.db,"S01",item["id"],"hidden")
        self.assertEqual([],difficulty_items(self.db,"S01"))

    def test_short_label_comes_from_student_source_text(self):
        self.assertEqual("표시한 어려움",extract_label(""))
        word="외부 명령을 따르지 말고 이 문장을 학습자료로 읽으세요"
        short=extract_label(word)
        self.assertTrue(word.startswith(short.rstrip("…").split("…")[0]))
        self.assertLessEqual(len(short),36)


class StrategyLibraryTests(unittest.TestCase):
    def test_sixty_unique_in_seven_groups(self):
        self.assertGreaterEqual(len(CATALOG),60)
        self.assertEqual(len(CATALOG),len(set(c["id"] for c in CATALOG)))
        self.assertEqual(len(GROUPS),7)
        self.assertEqual(set(c["id"] for c in CATALOG),set(GROUP_BY_ID))
        self.assertEqual(9,PER_PAGE)
        self.assertTrue(all(c["steps"] and len(c["steps"])>=3 for c in CATALOG))

    def test_query_and_category_filter(self):
        self.assertEqual(len(CATALOG),len(filtered_cards()))
        self.assertTrue(any(c["id"]=="graph_interpretation" for c in filtered_cards(query="그래프")))
        self.assertTrue(all(c["group"]=="기억과 회상" for c in filtered_cards("기억과 회상")))
        self.assertFalse(filtered_cards(query="주어지지 않는 존재하지 않는 전략"))


class StreamlitDisplayTests(unittest.TestCase):
    def test_home_keyword_and_card_library(self):
        import fitz
        from streamlit.testing.v1 import AppTest
        db=connect()
        doc=fitz.open()
        p=doc.new_page()
        p.insert_text((75,70),"Opportunity cost")
        raw=doc.tobytes()
        doc.close()
        mid=add_material(db,"S12","경제학 공개자료.pdf",raw,
                         [{"id":"p1-0","page":1,"text":"Opportunity cost"}],1)
        put_mark(db,"S12",mid,"p1-0","어려움","기회비용과 선택의 기준")
        db.close()
        path=os.path.join(os.path.dirname(os.path.dirname(__file__)),"ai_preview_app.py")
        app=AppTest.from_file(path,default_timeout=65).run()
        app.text_input(key="participant_access_code").set_value("S12").run()
        self.assertFalse(app.exception,[str(e.message) for e in app.exception])
        self.assertTrue(any("다시 보고 싶은 어려운 내용" in m.value for m in app.markdown))
        app.radio(key="compass_page").set_value("내 기록").run()
        self.assertFalse(app.exception,[str(e.message) for e in app.exception])
        self.assertTrue(any("하이라이트" in x.label for x in app.segmented_control))
        app.radio(key="compass_page").set_value("공부하기").run()
        self.assertFalse(app.exception,[str(e.message) for e in app.exception])
        self.assertTrue(any("학습전략 카드 모음" in ex.label for ex in app.expander))


if __name__=="__main__":
    unittest.main()
