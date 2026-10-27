"""Regression tests for learner autonomy, time reflection and optional AI feedback."""
import os
import tempfile
import unittest
from types import SimpleNamespace

TMP=tempfile.TemporaryDirectory()
os.environ["SDL_AI_PREVIEW_DB"]=os.path.join(TMP.name,"progress.db")

from compass_store import connect,add_task,task_rows,add_material,put_mark
from compass_progress import (save_criterion,criterion_for,save_time,
                              latest_time,time_summaries,revise_goal,adjustments)
from compass_feedback import make_feedback
from compass_pdf_selection import pdf_layers,selection_key,JS,HTML
from compass_pdf_selection import readable_ratio
from compass_independence import choice as record_strategy,recent as selected_methods,student_chosen_card


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
        self.assertIn("사용자 요청 없이",request["instructions"])


class ScrollablePdfTests(unittest.TestCase):
    def test_continuous_two_page_pdf_with_text_layer(self):
        import fitz
        doc=fitz.open()
        first=doc.new_page()
        first.insert_text((70,100),"Chapter one learning concept")
        second=doc.new_page()
        second.insert_text((70,100),"Chapter two reflection strategy")
        pdf=doc.tobytes()
        doc.close()
        pages=pdf_layers(pdf)
        self.assertEqual(2,len(pages))
        self.assertEqual([1,2],[p["page"] for p in pages])
        self.assertTrue(all(x["image"].startswith("data:image/png;base64,") for x in pages))
        self.assertTrue(any("learning" in x["text"] for x in pages[0]["spans"]))
        self.assertTrue(any("reflection" in x["text"] for x in pages[1]["spans"]))
        self.assertIn("overflow-y:auto",__import__("compass_pdf_selection").CSS)
        self.assertIn("setTriggerValue",JS)
        self.assertIn("marked",JS)
        self.assertNotIn("parentElement.innerHTML",HTML)

    def test_pdf_floating_color_palette_and_overlay(self):
        from compass_pdf_selection import CSS
        self.assertIn("어떤 내용으로 표시할까요?",HTML)
        self.assertIn("const palette=",JS)
        self.assertIn('"어려움":{fill:"#ff9fa5"',JS)
        self.assertIn('"흥미":{fill:"#9ac6ff"',JS)
        self.assertIn('"핵심":{fill:"#ffe478"',JS)
        self.assertIn('"질문":{fill:"#9be4bc"',JS)
        self.assertIn("toolbar.style.top=clamp",JS)
        self.assertIn("selectionRects(range,page)",JS)
        self.assertIn("drawMarks()",JS)
        self.assertIn('setTriggerValue("marked"',JS)
        self.assertIn("position:absolute",CSS)
        self.assertIn("document.addEventListener",JS)

    def test_saved_pdf_highlights_preserve_selection_rectangles(self):
        db=connect()
        material_id=add_material(db,"S07","public-example.pdf",b"%PDF",[],1)
        rects=[{"x":11.3,"y":22.5,"w":37.2,"h":1.8}]
        put_mark(db,"S07",material_id,"drag-1-example","흥미",
                 "나의 학습 흥미 문장",geometry=rects)
        row=db.execute("""SELECT kind,text,geometry FROM compass_marks
             WHERE owner=? AND material_id=?""",("S07",material_id)).fetchone()
        self.assertEqual("흥미",row["kind"])
        self.assertEqual(rects,__import__("json").loads(row["geometry"]))
        put_mark(db,"S07",material_id,"drag-1-example","흥미",
                 "나의 학습 흥미 문장",geometry=rects)
        count=db.execute("""SELECT COUNT(*) FROM compass_marks
             WHERE owner=? AND material_id=?""",("S07",material_id)).fetchone()[0]
        self.assertEqual(1,count)
        put_mark(db,"S07",material_id,"p1-0","어려움","기존 문단 표시")
        row2=db.execute("""SELECT geometry FROM compass_marks
             WHERE owner=? AND paragraph_id='p1-0'""",("S07",)).fetchone()
        self.assertEqual("",row2["geometry"])
        self.assertEqual(0,db.execute("""SELECT COUNT(*) FROM compass_marks
             WHERE owner='S08' AND material_id=?""",(material_id,)).fetchone()[0])
        with self.assertRaises(ValueError):
            put_mark(db,"S08",material_id,"drag-1-example","핵심","다른 학생 자료",geometry=rects)
        db.close()

    def test_student_selection_same_quote_same_record_key(self):
        same=selection_key(2,"기회비용은   포기한 대안")
        self.assertEqual(same,selection_key(2,"기회비용은 포기한 대안"))
        self.assertNotEqual(same,selection_key(3,"기회비용은 포기한 대안"))


class PdfAppMountTests(unittest.TestCase):
    def test_saved_pdf_page_renders_in_study_tab(self):
        import fitz
        from streamlit.testing.v1 import AppTest
        doc=fitz.open()
        for label in ("We study memory and cognition.","This page is about reflection."):
            page=doc.new_page()
            page.insert_text((72,95),label)
        raw=doc.tobytes()
        doc.close()
        db=connect()
        add_material(db,"S01","public-sample.pdf",raw,
          [{"page":1,"id":"p1-0","text":"We study memory and cognition."},
           {"page":2,"id":"p2-0","text":"This page is about reflection."}],2)
        db.close()
        entry=os.path.join(os.path.dirname(os.path.dirname(__file__)),"ai_preview_app.py")
        app=AppTest.from_file(entry,default_timeout=60).run()
        self.assertFalse(app.exception,[str(e.message) for e in app.exception])
        app.text_input(key="participant_access_code").set_value("S01").run()
        app.radio(key="compass_page").set_value("공부하기").run()
        self.assertFalse(app.exception,[str(e.message) for e in app.exception])


class IndependentLearningTests(unittest.TestCase):
    def setUp(self):
        self.db=connect()
        record_strategy(self.db,"S00","테스트","", "compare","student")
        self.db.execute("DELETE FROM compass_strategy_choices")

    def tearDown(self):
        self.db.close()

    def test_student_strategy_choice_is_not_ai_decision(self):
        record_strategy(self.db,"S01","경제학","기회비용","compare","student")
        record_strategy(self.db,"S01","경제학","기회비용","recall","ai_suggestion")
        record_strategy(self.db,"S02","경제학","기회비용","own_example","student")
        methods=selected_methods(self.db,"S01","경제학")
        self.assertEqual(2,len(methods))
        self.assertEqual(["ai_suggestion","student"],[m["choice_source"] for m in methods])
        self.assertEqual([],selected_methods(self.db,"S03","경제학"))
        with self.assertRaises(ValueError):
            record_strategy(self.db,"S01","경제학","기회비용","fake","student")
        with self.assertRaises(ValueError):
            record_strategy(self.db,"S01","경제학","기회비용","compare","automatic")
        card=student_chosen_card("compare")
        self.assertEqual("student_selected",card["source"])
        self.assertNotIn("점수",card["reason"])

    def test_pdf_keeps_position_and_prevents_broken_text(self):
        self.assertIn("previousScroll",JS)
        self.assertIn("sameDocument",JS)
        self.assertIn("aspectRatio=pg.width",JS)
        self.assertGreater(readable_ratio("기회비용은 포기한 대안 중 가치가 가장 높은 것"),0.9)
        self.assertLess(readable_ratio("☐☐☐☐☐☐☐☐"),0.65)

    def test_student_method_choice_is_visible_in_study_app(self):
        from streamlit.testing.v1 import AppTest
        entry=os.path.join(os.path.dirname(os.path.dirname(__file__)),"ai_preview_app.py")
        app=AppTest.from_file(entry,default_timeout=60).run()
        app.text_input(key="participant_access_code").set_value("S11").run()
        app.radio(key="compass_page").set_value("공부하기").run()
        self.assertFalse(app.exception,[str(e.message) for e in app.exception])
        self.assertTrue(any("학습전략 카드 모음" in x.label for x in app.expander))
        app.button(key="study_library_choose_compare").click().run()
        self.assertFalse(app.exception,[str(e.message) for e in app.exception])
        self.assertTrue(any("직접 해 보기" in str(x.value) for x in app.markdown))
        con=connect()
        found=con.execute("""SELECT choice_source,strategy_id FROM compass_strategy_choices
            WHERE owner='S11' ORDER BY created DESC LIMIT 1""").fetchone()
        con.close()
        self.assertIsNotNone(found)
        self.assertEqual("student",found["choice_source"])
        self.assertEqual("compare",found["strategy_id"])


if __name__=="__main__":
    unittest.main()
