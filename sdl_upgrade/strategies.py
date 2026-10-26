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
CATALOG = [
 dict(id=i,name=n,kind=k,benefit=b,steps=s.split("|"),
      contexts=c.split(","),difficulties=d.split(","))
 for i,n,k,b,s,c,d in _DATA
]


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
