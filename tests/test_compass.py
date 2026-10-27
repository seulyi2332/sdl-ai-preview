"""Tests for user-owned tasks, meaningful PDF highlights and compass navigation."""
import json
import os
import tempfile
import unittest

# Set before modules first read their DB path.
TMP=tempfile.TemporaryDirectory()
os.environ["SDL_AI_PREVIEW_DB"]=os.path.join(TMP.name,"test.db")

from compass_store import (connect,add_task,task_rows,change_task,add_material,
                           put_mark,marks,mark_status,material_rows,MARKS)
from compass_pdf import extract_pdf,render_page
from sdl_upgrade.strategies import CATALOG
from compass_access import STUDENT_CODES,is_demo_access_code,study_id_label
import fitz


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.db=connect()
        for name in ("compass_tasks","compass_marks","compass_materials"):
            self.db.execute("DELETE FROM "+name)

    def tearDown(self):
        self.db.close()

    def test_kanban_with_user_isolation(self):
        a=add_task(self.db,"DEMO01","심리학 챕터 정리")
        b=add_task(self.db,"DEMO02","영어 단어 외우기")
        self.assertEqual(1,len(task_rows(self.db,"DEMO01")))
        self.assertEqual(1,len(task_rows(self.db,"DEMO02")))
        change_task(self.db,"DEMO02",a,"완료")
        self.assertEqual("시작 전",task_rows(self.db,"DEMO01")[0]["status"])
        change_task(self.db,"DEMO01",a,"완료")
        self.assertEqual("완료",task_rows(self.db,"DEMO01")[0]["status"])
        change_task(self.db,"DEMO01",a,"숨김")
        self.assertFalse(task_rows(self.db,"DEMO01"))
        self.assertEqual(1,len(task_rows(self.db,"DEMO01",include_hidden=True)))

    def test_pdf_marks_with_recovery_and_user_isolation(self):
        material=add_material(self.db,"DEMO01","교재.pdf",b"test",
                              [{"page":1,"id":"p1-0","text":"기억의 원리"}],1)
        put_mark(self.db,"DEMO01",material,"p1-0","어려움","기억의 원리")
        self.assertEqual(1,len(marks(self.db,"DEMO01")))
        self.assertEqual([],marks(self.db,"DEMO02"))
        put_mark(self.db,"DEMO01",material,"p1-0","어려움","기억의 원리","모르겠어")
        self.assertEqual(1,len(marks(self.db,"DEMO01")))
        item=marks(self.db,"DEMO01")[0]
        self.assertEqual("모르겠어",item["note"])
        mark_status(self.db,"DEMO02",item["id"],"hidden")
        self.assertEqual(1,len(marks(self.db,"DEMO01")))
        mark_status(self.db,"DEMO01",item["id"],"hidden")
        self.assertEqual(0,len(marks(self.db,"DEMO01")))
        self.assertEqual(1,len(marks(self.db,"DEMO01",include_hidden=True)))
        mark_status(self.db,"DEMO01",item["id"],"active")
        self.assertEqual(1,len(marks(self.db,"DEMO01")))
        self.assertIn("흥미",MARKS)

    def test_pdf_source_extraction(self):
        doc=fitz.open()
        page=doc.new_page()
        page.insert_text((72,90),"Self-directed learning requires reflection.")
        raw=doc.tobytes()
        doc.close()
        paragraphs,pages=extract_pdf(raw)
        self.assertEqual(1,pages)
        self.assertTrue(any("learning" in p["text"] for p in paragraphs))
        image=render_page(raw,1)
        self.assertTrue(image.startswith(b"\x89PNG"))
        with self.assertRaises(ValueError):
            extract_pdf(b"not pdf")


class RenderTests(unittest.TestCase):
    def test_first_page_and_all_navigation(self):
        from streamlit.testing.v1 import AppTest
        app=AppTest.from_file(os.path.join(os.path.dirname(os.path.dirname(__file__)),"ai_preview_app.py"),default_timeout=40).run()
        self.assertFalse(app.exception,[e.message for e in app.exception])
        self.assertTrue(any("접속 코드" in x.label for x in app.text_input))
        app.text_input(key="participant_access_code").set_value("S01").run()
        self.assertFalse(app.exception,[e.message for e in app.exception])
        self.assertTrue(any("할 일" in b.label for b in app.button))
        for page in ("목표와 계획","공부하기","학습일지","내 기록"):
            app.radio(key="compass_page").set_value(page).run()
            self.assertFalse(app.exception,[e.message for e in app.exception])


    def test_feedback_selection_works_as_visible_radio(self):
        """Saved practice shows tappable radio choices rather than a mobile dropdown."""
        from streamlit.testing.v1 import AppTest
        app=AppTest.from_file(
            os.path.join(os.path.dirname(os.path.dirname(__file__)),"ai_preview_app.py"),
            default_timeout=40).run()
        app.text_input(key="participant_access_code").set_value("S03").run()
        app.radio(key="compass_page").set_value("공부하기").run()
        self.assertFalse(app.exception,[x.message for x in app.exception])
        app.button(key="study_recommend").click().run()
        buttons=[b for b in app.button if b.key and b.key.startswith("study_pick_")]
        self.assertTrue(buttons,"추천된 전략을 고르는 버튼이 보여야 해요.")
        buttons[0].click().run()
        fields={field.label:field for field in app.text_area}
        if "내가 직접 해 본 내용" in fields:
            fields["내가 직접 해 본 내용"].set_value("오늘 배운 개념을 예를 들어 설명했어요.").run()
        elif "내 풀이 과정" in fields:
            fields["내 풀이 과정"].set_value("문제의 조건을 먼저 찾아보았어요.").run()
        else:
            fields["첫 개념의 특징"].set_value("두 개념의 차이를 구분했어요.").run()
        save=next(b for b in app.button if b.label=="내 학습기록에 저장")
        save.click().run()
        self.assertFalse(app.exception,[x.message for x in app.exception])
        self.assertTrue(any(x.key=="study_feedback_mode" for x in app.radio),
            "After save, feedback radio missing. Widgets="+str([(x.key,x.label) for x in app.radio])+
            " Messages="+str([x.message for x in app.success])+
            " Warnings="+str([x.message for x in app.warning])+
            " Buttons="+str([(x.key,x.label) for x in app.button]))
        mode=app.radio(key="study_feedback_mode")
        self.assertEqual("정답을 바로 말하기보다 단서부터",mode.value)
        mode.set_value("필요한 개념과 예시 자세히").run()
        self.assertEqual("필요한 개념과 예시 자세히",
                         app.radio(key="study_feedback_mode").value)
        self.assertTrue(any(b.key=="study_feedback_btn" for b in app.button))


class ParticipantCodeTests(unittest.TestCase):
    def test_student_and_backup_codes(self):
        self.assertEqual(len(STUDENT_CODES),12)
        for i in range(1,13):
            self.assertTrue(is_demo_access_code(f"S{i:02d}"))
        for bad in ("S00","S13","S1","S100","", "S 01","../S01","s01","S01;DROP"):
            self.assertFalse(is_demo_access_code(bad))
        self.assertTrue(is_demo_access_code("DEMO01"))
        self.assertFalse(is_demo_access_code("ADMIN"))
        self.assertEqual("평가 참여자 S09",study_id_label("S09"))

    def test_student_records_do_not_cross_codes(self):
        conn=connect()
        add_task(conn,"S01","학생 1 과제")
        add_task(conn,"S02","학생 2 과제")
        self.assertEqual(["학생 1 과제"],[r["title"] for r in task_rows(conn,"S01")])
        self.assertEqual(["학생 2 과제"],[r["title"] for r in task_rows(conn,"S02")])
        conn.close()


if __name__=="__main__":
    unittest.main()
