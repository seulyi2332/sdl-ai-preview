"""Independent tests for isolated AI strategy and learning diary modules."""
import unittest
from types import SimpleNamespace
from sdl_upgrade.strategies import StudyContext, CATALOG, recommend
from sdl_upgrade.ai import suggest_strategies
from sdl_upgrade.journal import validate_draft, analyze_diary, ask_diary_followup, CATEGORIES
from sdl_upgrade.model_client import safe_error_message


class FakeResponses:
    def __init__(self, data):
        self.data=data
        self.calls=[]
    def create(self, **kw):
        import json
        self.calls.append(kw)
        return SimpleNamespace(output_text=json.dumps(self.data,ensure_ascii=False))


def mock_client(data):
    obj=FakeResponses(data)
    return SimpleNamespace(responses=obj),obj


class TestStrategy(unittest.TestCase):
    def test_expanded_catalog(self):
        self.assertGreaterEqual(len(CATALOG),60)
        self.assertEqual(len(CATALOG),len({x["id"] for x in CATALOG}))

    def test_math_strategy(self):
        results=recommend(StudyContext(course="통계학",difficulty="공식을 언제 쓰는지 헷갈려요"))
        self.assertTrue({"condition_table","step_solution"} & {x["id"] for x in results})
        self.assertTrue(all(x["source"]=="catalog_fallback" for x in results))

    def test_reading_strategy(self):
        result=recommend(StudyContext(course="철학",task="논문의 글을 읽고 주장과 근거 분석"))
        self.assertIn("claim_evidence",[x["id"] for x in result])

    def test_ai_cannot_introduce_unknown_strategy(self):
        client,_=mock_client({"strategies":[
            {"id":"fabricated","reason":"추천","task_prompt":"쓰기"},
            {"id":"compare","reason":"둘을 비교","task_prompt":"두 개념의 차이를 설명"}]})
        result=suggest_strategies(StudyContext(course="심리학",difficulty="차이가 헷갈려요"),client)
        self.assertEqual(1,len(result))
        self.assertEqual("compare",result[0]["id"])
        self.assertEqual("openai_generated",result[0]["source"])

    def test_reasoning_model_uses_responses_without_temperature(self):
        client,stub=mock_client({"strategies":[{"id":"compare","reason":"비교","task_prompt":"표에 써보세요"}]})
        suggest_strategies(StudyContext(course="심리학",difficulty="차이가 헷갈려요"),client,model="gpt-6.1-sol")
        self.assertEqual("gpt-6.1-sol",stub.calls[0]["model"])
        self.assertNotIn("temperature",stub.calls[0])
        self.assertNotIn("response_format",stub.calls[0])
        self.assertEqual("json_object",stub.calls[0]["text"]["format"]["type"])
        self.assertIn("json",stub.calls[0]["input"][0]["content"])

    def test_safe_error_message_does_not_expose_secret(self):
        err=ValueError("sk-sensitive-data")
        self.assertNotIn("sk-sensitive-data",safe_error_message(err))

    def test_invalid_ai_result_is_error_not_impersonated(self):
        client,_=mock_client({"strategies":[{"id":"unknown","reason":"추정"}]})
        with self.assertRaises(ValueError):
            suggest_strategies(StudyContext(),client)


class TestJournal(unittest.TestCase):
    def test_facts_require_verbatim_evidence(self):
        diary="비교표를 그려보니 단기기억이 조금 이해됐다."
        data={"facts":{"strategy":{"text":"비교표를 활용함","evidence":"비교표를 그려보니"},
                       "emotion":{"text":"매우 행복함","evidence":"행복했다"}}}
        result=validate_draft(data,diary)
        self.assertEqual("student_diary",result["facts"]["strategy"]["source"])
        self.assertIsNone(result["facts"]["emotion"])
        self.assertEqual(set(CATEGORIES),set(result["facts"]))

    def test_goal_requires_evidence_and_approval(self):
        diary="기억이 왜 사라지는지 다음에 더 알아보고 싶다."
        data={"goal_candidates":[
            {"title":"망각 이론 알아보기","why":"학생이 직접 궁금해함","evidence":"기억이 왜 사라지는지"},
            {"title":"심리학으로 진로 결정","why":"AI 추정","evidence":"전공 적합성 확인"}]}
        result=validate_draft(data,diary)
        self.assertEqual(1,len(result["goal_candidates"]))
        self.assertEqual("ai_draft_unconfirmed",result["goal_candidates"][0]["status"])
        self.assertFalse(result["approved"])

    def test_single_diary_question_uses_student_diary_and_optional_major(self):
        diary="심리학 시간에 기억의 원리를 배웠는데 더 궁금해졌어요."
        client,stub=mock_client({"question":"기억에 관한 이번 수업에서 심리학 전공을 더 알아보고 싶어진 부분이 있었나요?"})
        question=ask_diary_followup(diary,client,interest="심리학")
        self.assertIn("심리학 전공",question)
        payload=stub.calls[0]["input"][0]["content"]
        self.assertIn(diary,payload)
        self.assertIn("심리학",payload)
        self.assertEqual("gpt-4o-mini",stub.calls[0]["model"])

    def test_diary_question_does_not_require_major(self):
        client,stub=mock_client({"question":"오늘 공부한 것 가운데 다음에 더 알아보고 싶은 내용이 있나요?"})
        question=ask_diary_followup("오늘 통계를 공부했어요.",client)
        self.assertIn("더 알아보고 싶은",question)
        self.assertIn("null",stub.calls[0]["input"][0]["content"])

    def test_empty_diary_question_is_rejected(self):
        client,_=mock_client({"question":"무엇을 배웠나요?"})
        with self.assertRaises(ValueError):
            ask_diary_followup(" ",client)

    def test_empty_diary_rejected(self):
        client,_=mock_client({})
        with self.assertRaises(ValueError):
            analyze_diary("   ","",client)

    def test_ai_analysis_preserves_original(self):
        diary="오늘은 심리학 개념을 비교했어요."
        client,_=mock_client({"facts":{"studied":{"text":"심리학 개념 비교","evidence":"심리학 개념을 비교했어요"}},
                              "briefing":"오늘 심리학을 비교했어요.","goal_candidates":[]})
        result=analyze_diary(diary,"",client)
        self.assertEqual(diary,result["original_diary"])
        self.assertFalse(result["approved"])
        self.assertEqual("오늘 심리학을 비교했어요.",result["briefing_draft"])


if __name__=="__main__":
    unittest.main()
