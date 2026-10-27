"""Regression: clicking 'study this paragraph' must create an AI turn, not only show success."""
import json
import os
import tempfile
import unittest
from types import SimpleNamespace
import compass_store
from compass_pdf_chat import question_from_selection,send_pdf_message
from compass_store import connect,chat_messages,save_interest


class FakeResponses:
    def __init__(self):
        self.calls=[]
    def create(self,**kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(output_text="자료에는 저널명과 발행정보가 적혀 있어요. 어떤 부분이 궁금한가요?")


class PdfChatFlowTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.before=compass_store.DB_PATH
        compass_store.DB_PATH=os.path.join(self.temp.name,"pdfchat.db")
        self.db=connect()

    def tearDown(self):
        self.db.close()
        compass_store.DB_PATH=self.before
        self.temp.cleanup()

    def test_note_is_first_real_question(self):
        self.assertIn("무슨말이야?",question_from_selection("질문","무슨말이야?"))
        self.assertIn("예시",question_from_selection("어려움"))
        self.assertIn("전공",question_from_selection("흥미"))

    def test_click_calls_ai_with_selected_paragraph_and_note_then_saves_both_messages(self):
        fake=FakeResponses()
        client=SimpleNamespace(responses=fake)
        save_interest(self.db,"S01","교육학")
        excerpt="교육혁신연구 제24권 제2호 2014, pp.97-116"
        question=question_from_selection("질문","무슨말이야?")
        result=send_pdf_message(self.db,"S01",client,"gpt-4o-mini","심리학개론","논문 읽기",excerpt,question)
        self.assertIn("저널명",result)
        self.assertEqual(1,len(fake.calls))
        request=fake.calls[0]["input"]
        self.assertIn("무슨말이야?",str(request))
        self.assertIn(excerpt,str(request))
        self.assertIn("교육학",str(request))
        own=chat_messages(self.db,"S01","심리학개론")
        self.assertEqual(["user","assistant"],[r["role"] for r in own])
        self.assertIn("무슨말이야?",own[0]["text"])
        self.assertEqual(result,own[1]["text"])
        self.assertEqual([],chat_messages(self.db,"S02","심리학개론"))

    def test_unavailable_ai_must_not_claim_connected_or_save_chat(self):
        with self.assertRaises(ValueError):
            send_pdf_message(self.db,"S01",None,"gpt-4o-mini","과목","","문단","무슨 뜻?")
        self.assertEqual([],chat_messages(self.db,"S01","과목"))


if __name__=="__main__":
    unittest.main()
