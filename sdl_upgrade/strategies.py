"""교과 특성과 학습 어려움에 따른 학습전략 카탈로그 (시연 모듈).
랭킹은 단순 검색 순서이며 학습효과, 역량 또는 전공 적합도 점수가 아니다.
"""
from dataclasses import dataclass, asdict


@dataclass
class StudyContext:
    course: str = ""
    topic: str = ""
    difficulty: str = ""
    task: str = ""
    material_excerpt: str = ""
    prior_methods: str = ""


# id, 이름, 실행폼, 목적, 단계, 적합한 맥락 키워드, 어려움 키워드
_DATA = [
 ("compare","비교표 만들기","comparison","비슷한 개념의 공통점과 차이 구분","비교할 두 개념 선택|비교 기준과 근거 설정|표를 직접 채우고 자료와 비교","심리,교육,경제,생물,법,역사,개념","헷갈,차이,비교,구분"),
 ("own_example","내 예시 만들기","example","배운 개념을 실제 상황에 적용","핵심 개념 정리|나만의 상황 만들기|개념과 사례의 연결 근거 확인","심리,경제,교육,철학,이론,개념","이해,적용,예시,어려"),
 ("recall","자료 덮고 떠올리기","recall","자료 없이 기억나는 부분 확인","자료 잠시 가리기|기억나는 핵심 작성|자료와 대조해 보완","암기,해부,법,역사,생물,용어","외우,기억,암기,시험,잊"),
 ("teach_back","친구에게 설명하기","explain","이해한 내용을 스스로 설명","자기 말로 설명|설명하기 어려운 부분 확인|도움 후 다시 설명","심리,교육,경제,과학,개념","설명,이해,말로"),
 ("concept_map","개념 관계도","map","여러 개념의 연결과 위계 이해","중심 개념 선택|연결되는 개념과 관계 작성|빠진 관계 확인","심리,생물,사회,교육,개념","연결,전체,복잡,흐름"),
 ("step_solution","풀이 단계 나누기","solve","문제를 순서대로 해결","주어진 조건 찾기|풀이 단계를 직접 쓰기|막힌 단계에서 단서 활용","수학,통계,회계,물리,경제,공학","문제,공식,풀이,계산,막혀"),
 ("condition_table","공식 적용 조건 비교","comparison","공식과 방법을 선택하는 조건 구별","문제 조건 확인|가능한 공식의 조건 비교|선택 이유 쓰기","통계,수학,회계,공학,경제","공식,어떤,헷갈,계산"),
 ("error_reason","오답 이유 추적하기","solve","틀린 이유를 확인하고 다시 시도","처음 풀이 되돌아보기|개념·조건·계산의 오류 구분|다시 풀어보기","수학,통계,회계,과학,공학","틀,오답,실수,오류"),
 ("variant_problem","조건 바꿔 풀기","solve","원리를 다른 문제에 적용","원래 문제 풀이|문제의 조건 하나 변경|결과가 달라진 이유 설명","수학,통계,경제,과학","문제,응용,적용"),
 ("question_making","직접 점검 질문 만들기","recall","학습자료를 자기점검 문제로 변환","핵심 내용 찾기|왜·어떻게 질문 작성|자료를 덮고 답하기","역사,교육,철학,읽기,개념","읽,이해,질문,시험"),
 ("claim_evidence","주장과 근거 찾기","reading","글의 주장, 근거, 한계를 구분","중심 주장 작성|원문의 근거 표시|반론이나 한계 쓰기","논문,철학,사회,법,교육,읽기","논문,글,분석,읽"),
 ("paragraph_outline","문단 구조 정리","reading","긴 글의 논리적 흐름 파악","문단별 핵심 작성|논리의 연결 표시|내 말로 재구성","논문,철학,교육,사회,역사","읽,글,복잡,정리"),
 ("keyword_recall","핵심어로 회상","recall","핵심어를 이용해 개념 재구성","핵심어 3~5개 고르기|단어만 보고 설명|원문과 비교","암기,해부,법,역사,생물,용어","암기,기억,외우,잊"),
 ("spaced_revisit","짧게 여러 번 복습","plan","반복 회상으로 복습 계획 세우기","다시 볼 항목 선택|다음 확인 시점 설정|회상 결과 확인","암기,용어,역사,법,생물","외우,잊,기억,시험"),
 ("worked_then_self","예제 뒤에 스스로 풀기","solve","예제의 도움을 점차 줄이기","예제 풀이 이유 살피기|예제 가리고 직접 풀이|막힌 부분 확인","수학,통계,회계,물리","문제,풀이,어려"),
 ("mini_start","짧게 시작하기","plan","시작 장벽을 낮추고 학습 재개","5~15분 할 내용 선택|방해 요소 확인|계속할지 결정","집중,계획,동기,실행","시작,미뤄,집중,지루,귀찮"),
 ("environment_check","환경 바꿔 시도하기","environment","집중과 환경의 관계 확인","장소와 방해 기록|바꿀 조건 하나 선택|다음 집중 경험 비교","집중,환경,실행","집중,소음,산만,방해"),
 ("priority_slice","학습 우선순위 정하기","plan","가용시간에 맞춰 활동 선택","남은 학습량 작성|중요도와 기한 비교|이번에 할 것 선택","계획,시간,시험,과제","시간,밀,계획,많,부족"),
 ("resource_criteria","자료 탐색 기준 만들기","resource","학습목적에 맞는 자료 찾아보기","필요한 주제 정하기|자료 수준과 형식 선택|출처 비교","자료,논문,과제,읽기","자료,찾,참고,어디"),
 ("case_transfer","새 사례에 적용하기","example","배운 원리를 다른 상황에 적용","핵심 조건 정리|새 사례 만들기|적용 근거 설명","심리,교육,경제,간호,경영,법","적용,사례,응용"),
 ("argument_compare","관점 비교하기","comparison","관점의 주장과 근거를 비교","관점 두 가지 선택|각각의 근거 작성|내 해석과 이유 적기","철학,사회,문학,역사,법","비교,관점,주장,해석"),
 ("worked_outline","과제의 뼈대 잡기","writing","과제를 요구조건에 따라 직접 작성","과제 요구 확인|목차와 주장 설계|근거 채우기","과제,보고서,논문,글쓰기","과제,보고서,쓰기,글"),
 ("major_link","전공 관련 연결 탐색","reflection","배운 내용과 관심 전공의 연관성 확인","관련 학습내용 정보 확인|가치와 흥미 스스로 생각|더 알아볼 것 작성","전공,관심,탐색,개념","전공,흥미,연결"),
 ("rebuild_schedule","예상과 실제시간 비교","plan","다음 학습의 시간 배분 조정","계획시간과 실제시간 비교|차이의 이유 생각|다음 시간 직접 정하기","계획,시간,시험","시간,부족,늦,계획"),
]

# 36 additional learner-executable cards; together with the existing 24, 60 in total.
# Each card has concrete self-performed steps, not AI-completed answers.
_EXTRA = [
 ("rewrite_definition","정의를 내 말로 다시 쓰기","explain","교과서 표현을 이해한 말로 바꾸기","정의에서 핵심 조건 찾기|자기 말로 다시 작성|원문과 의미 비교","이론,개념,정의,철학,심리","이해,어려,용어"),
 ("counter_example","반례 하나 찾아보기","example","개념의 적용 범위를 스스로 점검","성립하는 예시 고르기|성립하지 않는 상황 생각|구분 근거 작성","과학,경제,통계,법,논리","예외,헷갈,원리"),
 ("boundary_conditions","적용 조건 확인하기","comparison","정의나 공식의 적용 조건 구별","적용 조건 세 가지 찾기|조건이 빠진 사례 비교|적용 여부 설명","수학,통계,경제,법,공학","조건,공식,틀림"),
 ("sketch_diagram","그림으로 개념 설명하기","map","개념 사이의 구조를 시각화","요소 세 가지 선택|화살표로 관계 그리기|관계의 의미를 글로 설명","생물,과학,경제,심리,해부","복잡,관계,이해"),
 ("similarity_talk","비슷한 개념을 말로 구별하기","comparison","유사 개념의 핵심 차이 말하기","비슷한 개념 둘 정하기|차이를 한 문장씩 말하기|틀리기 쉬운 부분 확인","심리,법,경제,간호","차이,헷갈,구분"),
 ("cause_chain","원인과 결과 이어 보기","map","변화의 원인과 결과를 단계별로 설명","출발 사건 정하기|중간 과정을 연결|마지막 결과의 근거 확인","역사,경제,과학,심리","원인,과정,이해"),
 ("nonexample_pair","사례와 비사례 짝짓기","comparison","개념이 성립하는 조건을 구별","해당 사례 만들기|해당하지 않는 사례 만들기|판별 기준 쓰기","교육,심리,사회,법","적용,개념,차이"),
 ("free_recall","빈 종이에 기억나는 것 적기","recall","읽은 내용을 자료 없이 인출","자료 덮기|기억나는 용어와 관계 작성|빠진 내용만 다시 확인","법,의학,생물,역사,암기","기억,잊,시험"),
 ("three_retrieval_questions","세 가지 인출 질문에 답하기","recall","자기점검 질문으로 이해 여부 확인","무엇·왜·어떻게 질문 만들기|자료 없이 답하기|답이 막힌 부분만 복습","심리,과학,역사,법","시험,암기,모르"),
 ("interleave_cases","문제 유형 섞어서 풀기","solve","유형을 구별하며 풀이전략 선택","서로 다른 유형 선택|순서를 섞어 풀기|유형 구분 근거 기록","통계,수학,회계,물리","유형,문제,헷갈"),
 ("revisit_calendar","나만의 복습 시점 정하기","plan","회상 경험에 맞춰 다음 복습 계획","어려운 항목 고르기|다음 점검 날짜 정하기|재회상 후 간격 조정","암기,생물,법,역사","반복,복습,잊"),
 ("memory_cue","기억 단서 직접 만들기","recall","다시 떠올릴 단서를 스스로 생성","기억할 개념 고르기|연상되는 단서 작성|단서만 보고 개념 설명","해부,법,용어,역사","외우,용어,암기"),
 ("error_log","오답의 유형 기록하기","solve","자신의 오류 패턴을 구체적으로 확인","틀린 풀이 선택|조건·개념·계산 등 이유 구분|다음 점검 질문 만들기","수학,통계,회계,과학","오답,실수,틀"),
 ("underline_conditions","문제 조건 먼저 표시하기","solve","문제에 주어진 조건을 누락하지 않기","조건에 표시하기|묻는 것 다시 작성|풀이 순서 스스로 정하기","통계,수학,회계,법","문제,조건,실수"),
 ("reverse_solution","풀이 마지막부터 거꾸로 점검","solve","풀이 단계의 논리적 연결 확인","나온 결과 적기|직전 단계의 근거 확인|처음 조건까지 거슬러 검토","수학,회계,공학,통계","풀이,검산,틀"),
 ("make_problem","유사 문제 직접 만들기","solve","배운 원리를 문제 구성에 적용","핵심 개념과 조건 적기|새 조건으로 문제 만들기|풀이 가능 여부 확인","통계,수학,경제,과학","응용,문제,이해"),
 ("calculation_table","계산 과정을 표로 정리하기","comparison","수식 적용 단계를 명확히 구분","변수와 단위 쓰기|계산 단계 표로 작성|결과의 의미 설명","회계,통계,수학,경제","계산,공식,복잡"),
 ("check_answer_reason","답이 맞는 이유 검토하기","explain","결과가 아니라 풀이 근거를 확인","내 답 적기|선택한 방법의 이유 쓰기|조건을 바꾸면 달라질지 검토","통계,수학,과학,경제","답,근거,검산"),
 ("graph_interpretation","그래프를 말로 설명하기","explain","도표와 개념의 관계 이해","축과 단위 확인|증감 패턴 묘사|자료가 말하지 않는 점 구별","경제,통계,사회,과학","그래프,표,해석"),
 ("three_sentence_summary","세 문장으로 요약하기","writing","긴 글의 핵심 주장을 자기 언어로 요약","글의 주제 확인|핵심 세 문장 작성|빠진 조건과 근거 확인","논문,사회,인문,교육","긴글,요약,읽"),
 ("notes_into_questions","필기 내용을 질문으로 바꾸기","recall","수동적인 필기를 점검 질문으로 전환","중요 메모 하나 선택|관련 질문 만들기|필기 없이 답해보기","강의,필기,시험,용어","필기,복습,모르"),
 ("paragraph_argument","문단마다 논점 표시하기","reading","긴 읽기자료의 구조 파악","각 문단 주장 적기|근거 문장 선택|문단 사이 연결 설명","논문,법,철학,사회","읽기,복잡,논문"),
 ("claim_objection","주장·근거·반론 정리하기","comparison","근거의 강약과 대안을 비교","주장 한 문장 적기|근거와 반론 분리|추가로 확인할 것 작성","철학,법,교육,사회","주장,근거,토론"),
 ("paraphrase_passage","어려운 문장 다시 풀어 쓰기","writing","난해한 문장의 의미를 점검","어려운 표현 밑줄|쉬운 말로 다시 쓰기|원문과 의미 차이 비교","논문,철학,법,교육","문장,어려,읽"),
 ("debate_perspectives","두 관점에서 설명해 보기","comparison","주제를 다른 관점으로 해석","관점 둘 고르기|각 입장의 근거 적기|내 질문과 판단 기준 정리","역사,사회,철학,법","관점,토론,비교"),
 ("source_crosscheck","자료 출처 교차 확인하기","resource","자료의 근거와 신뢰성 점검","출처·저자·날짜 확인|자료 두 개의 주장 비교|더 확인할 근거 기록","논문,과제,전공,자료","출처,자료,정확"),
 ("distraction_forecast","집중을 방해할 요인 예상하기","environment","학습 시작 전 환경을 직접 준비","예상 방해 요인 선택|조절 방법 정하기|학습 후 실제 차이 확인","집중,계획,환경","방해,산만,집중"),
 ("micro_commitment","지킬 수 있는 학습 약속 정하기","plan","현실적인 작은 행동기준을 세우기","지금 실천할 행동 고르기|측정 기준 정하기|실행 후 기록 비교","계획,공부,실행","미루,시작,동기"),
 ("chunk_work","큰 과제 작은 단계로 나누기","plan","과제 시작 부담을 줄이고 우선순위 결정","완료 기준 확인|활동을 세 단계로 분할|이번에 시작할 단계 선택","과제,시험,계획","막막,많,시간"),
 ("fallback_plan","막힐 때 다른 방법 준비하기","plan","중단 상황에서 학습을 재개할 대안 만들기","막힐 상황 생각|도움 요청이나 대체 방법 정하기|다음 시도 방법 선택","실행,과제,계획","중단,막혀,미루"),
 ("precheck_knowledge","학습 전 아는 것 확인하기","reflection","자신의 사전 지식과 부족한 부분 구분","주제에서 아는 것 적기|모르는 것 적기|오늘의 확인 질문 정하기","심리,과학,교육,전공","모르,처음,개념"),
 ("goal_criteria_check","목표의 확인 기준 대조하기","reflection","스스로 정한 기준에 비추어 수행 점검","목표 기준 다시 읽기|근거가 되는 내 활동 선택|다음에 보완할 점 선택","목표,학습,성찰","목표,평가,점검"),
 ("explanation_record","내 설명을 짧게 기록하기","explain","개념 설명 중 막히는 부분 찾기","배운 내용 1분 설명|막힌 표현 기록|자료 확인 뒤 설명 보완","개념,심리,과학,역사","설명,이해,모르"),
 ("know_unknown_map","아는 것과 모르는 것 나누기","reflection","추가 학습이 필요한 부분을 스스로 식별","아는 부분 두 가지 작성|확인할 부분 표시|다음 공부 순서 선택","전공,시험,교과","점검,모르,복습"),
 ("next_step_reason","다음 학습의 이유 정리하기","reflection","성찰 결과를 실행 가능한 조정에 연결","잘된 점과 어려움 살피기|바꿀 방법 하나 고르기|그 이유를 자기 말로 쓰기","성찰,계획,목표","성찰,바꾸,다음"),
 ("major_viewpoint","관심 전공 관점으로 질문하기","reflection","교과목 내용과 관심 분야를 연결해 탐색","배운 개념 선택|관심 전공의 질문 만들기|확인이 필요한 전공 학습내용 구분","전공,탐색,교양,관심","전공,흥미,연결"),
]

_DATA.extend(_EXTRA)

CATALOG = [
 dict(id=i,name=n,kind=k,benefit=b,steps=s.split("|"),
      contexts=c.split(","),difficulties=d.split(","))
 for i,n,k,b,s,c,d in _DATA
]


GROUPS={
 "이해와 개념":["compare","own_example","teach_back","concept_map","case_transfer",
 "rewrite_definition","counter_example","boundary_conditions","sketch_diagram",
 "similarity_talk","cause_chain","nonexample_pair","graph_interpretation","explanation_record"],
 "기억과 회상":["recall","question_making","keyword_recall","spaced_revisit",
 "free_recall","three_retrieval_questions","revisit_calendar","memory_cue",
 "notes_into_questions"],
 "문제풀이와 적용":["step_solution","condition_table","error_reason","variant_problem",
 "worked_then_self","interleave_cases","error_log","underline_conditions",
 "reverse_solution","make_problem","calculation_table","check_answer_reason"],
 "읽기와 쓰기":["claim_evidence","paragraph_outline","argument_compare","worked_outline",
 "three_sentence_summary","paragraph_argument","claim_objection","paraphrase_passage",
 "debate_perspectives"],
 "계획과 지속":["mini_start","environment_check","priority_slice","rebuild_schedule",
 "distraction_forecast","micro_commitment","chunk_work","fallback_plan"],
 "점검과 성찰":["precheck_knowledge","goal_criteria_check","know_unknown_map",
 "next_step_reason"],
 "자료와 전공탐색":["resource_criteria","major_link","source_crosscheck",
 "major_viewpoint"],
}
GROUP_BY_ID={key:group for group,items in GROUPS.items() for key in items}
assert len(GROUP_BY_ID)==len(CATALOG), "All learning strategies must have a category."
assert len(set(s["id"] for s in CATALOG))==len(CATALOG), "Each strategy needs a unique id."
for _strategy in CATALOG:
    _strategy["group"]=GROUP_BY_ID[_strategy["id"]]


def recommend(ctx: StudyContext, limit: int = 3):
    text = " ".join([ctx.course,ctx.topic,ctx.difficulty,ctx.task,ctx.material_excerpt]).lower()
    order = []
    for pos,strategy in enumerate(CATALOG):
        d=[w for w in strategy["difficulties"] if w in text]
        c=[w for w in strategy["contexts"] if w in text]
        score=4*len(d)+2*len(c)
        if ctx.prior_methods and strategy["name"] in ctx.prior_methods:
            score += 1
        order.append((score,-pos,strategy,d,c))
    order.sort(reverse=True,key=lambda r:(r[0],r[1]))
    results=[]
    for _,_,s,d,c in order[:max(1,min(limit,5))]:
        reason=(f"말씀한 어려움을 고려할 때 {s['benefit']}에 활용할 수 있어요."
                if d else f"{s['benefit']}에 활용할 수 있는 방법이에요.")
        results.append({**s,"reason":reason,"task_prompt":"","example":"",
                        "source":"catalog_fallback"})
    return results
