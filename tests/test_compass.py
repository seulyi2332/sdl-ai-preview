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
        app=AppTest.from_file("ai_preview_app.py",default_timeout=40).run()
        self.assertFalse(app.exception,[e.message for e in app.exception])
        self.assertTrue(any("할 일" in b.label for b in app.button))
        for page in ("목표와 계획","공부하기","학습일지","내 기록"):
            app.radio(key="compass_page").set_value(page).run()
            self.assertFalse(app.exception,[e.message for e in app.exception])


if __name__=="__main__":
    unittest.main()
