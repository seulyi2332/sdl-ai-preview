"""AI 학습전략 및 학습일지 기능 시연 앱.
기존 평가용 app.py와 DB를 변경하지 않는 독립 개발용 화면.
Streamlit Cloud: repository seulyi2332/sdl-ai-preview, branch main, main file ai_preview_app.py
"""
import json
import os
import sqlite3
import uuid
from datetime import datetime

import streamlit as st
from openai import OpenAI
from sdl_upgrade.strategies import CATALOG, StudyContext, recommend
from sdl_upgrade.ai import suggest_strategies
from sdl_upgrade.journal import analyze_diary
from sdl_upgrade.model_client import safe_error_message

st.set_page_config(page_title="나의 학습 나침반 · 기능 시연", page_icon="🧭", layout="wide")
st.markdown("""<style>
.block-container {max-width:1220px;padding-top:1.6rem;}
h1,h2,h3 {letter-spacing:-.04em;}
div[data-testid="stVerticalBlockBorderWrapper"] {border-radius:16px;}
button[kind="primary"] {background-color:#116c5e;}
[data-testid="stMetric"] {background:#f4faf8;padding:12px;border-radius:12px;}
</style>""",unsafe_allow_html=True)


def get_secret(name):
    v=os.environ.get(name)
    if v:
        return v
    try:
        if name in st.secrets:
            return str(st.secrets[name])
        for section in st.secrets.values():
            if hasattr(section,"get") and section.get(name):
                return str(section[name])
    except (FileNotFoundError,KeyError,RuntimeError):
        pass
    return ""


@st.cache_resource(show_spinner=False)
def make_client(key):
    return OpenAI(api_key=key)


api_key=get_secret("OPENAI_API_KEY")
client=make_client(api_key) if api_key else None
model=get_secret("OPENAI_MODEL") or "gpt-4o-mini"
DB=os.environ.get("SDL_AI_PREVIEW_DB","ai_preview_learning.db")


def connection():
    con=sqlite3.connect(DB,timeout=20,isolation_level=None)
    con.row_factory=sqlite3.Row
    con.execute("PRAGMA busy_timeout=20000")
    con.execute("""CREATE TABLE IF NOT EXISTS demo_goals (
       id TEXT PRIMARY KEY,owner TEXT NOT NULL,title TEXT NOT NULL,
       parent TEXT NOT NULL DEFAULT '',period TEXT NOT NULL DEFAULT '',
       state TEXT NOT NULL DEFAULT 'active',created TEXT NOT NULL)""")
    con.execute("""CREATE TABLE IF NOT EXISTS demo_tasks (
       id TEXT PRIMARY KEY,owner TEXT NOT NULL,title TEXT NOT NULL,
       goal_id TEXT NOT NULL DEFAULT '',day TEXT NOT NULL DEFAULT '',
       done INTEGER NOT NULL DEFAULT 0,created TEXT NOT NULL)""")
    con.execute("""CREATE TABLE IF NOT EXISTS demo_practice (
       id TEXT PRIMARY KEY,owner TEXT NOT NULL,course TEXT,topic TEXT,
       strategy TEXT,student_work TEXT,created TEXT NOT NULL)""")
    con.execute("""CREATE TABLE IF NOT EXISTS demo_diaries (
       id TEXT PRIMARY KEY,owner TEXT NOT NULL,original TEXT NOT NULL,
       briefing TEXT NOT NULL,analysis TEXT NOT NULL,created TEXT NOT NULL)""")
    return con


def now():
    return datetime.now().isoformat(timespec="seconds")


with st.sidebar:
    st.title("🧭 나의 학습 나침반")
    st.caption("AI 학습전략 및 성찰 기능 시연")
    owner=st.text_input("시연용 코드",value="DEMO01")
    st.caption("실제 학생 자료를 입력하지 마세요. 연구 평가용 앱과 데이터가 연결되지 않습니다.")
    if client:
        st.success("OpenAI 키 설정됨 · 실제 응답은 요청 후 확인")
        st.caption("설정된 AI 모델: " + model)
    else:
        st.warning("OpenAI 키 없음 · 전략은 카탈로그 추천, AI 일지 분석은 사용할 수 없음")

if not owner.startswith("DEMO") or len(owner)>24 or not owner.isalnum():
    st.error("시연용 코드는 영문과 숫자로 된 DEMO 시작 코드만 사용할 수 있어요.")
    st.stop()

# A new demo code must never inherit another demo user's unsaved AI drafts.
if st.session_state.get("_preview_active_owner") != owner:
    for name in ("strategy_cards","strategy_source","chosen_strategy","diary_analysis","diary_analysis_id","strategy_context"):
        st.session_state.pop(name,None)
    st.session_state["_preview_active_owner"] = owner

db=connection()
st.title("내 공부를 이해하고 다음 학습을 스스로 선택하기")
st.caption("시연용 새 화면 · 기존 연구 평가 앱과 무관 · Streamlit 저장 데이터는 재시작 시 사라질 수 있음")
view_goal,view_study,view_diary=st.tabs(["① 목표와 계획","② 학습전략 추천 및 직접 수행","③ 학습일지와 AI 브리핑"])

with view_goal:
    st.subheader("내 목표 · 먼저 표로 관리해요")
    goals=db.execute("SELECT * FROM demo_goals WHERE owner=? AND state!='hidden' ORDER BY created DESC",(owner,)).fetchall()
    st.caption(f"진행 중 {sum(g['state']=='active' for g in goals)}개 · 완료 표시 {sum(g['state']=='done' for g in goals)}개 · 목표 달성 정도는 학생이 별도 자기평가")
    cols=st.columns([.7,5,2,2])
    for c,h in zip(cols,["완료","목표명 / 장기목표","기간","관리"]):
        c.markdown("**"+h+"**")
    for g in goals:
        cols=st.columns([.7,5,2,2],vertical_alignment="center")
        checked=cols[0].checkbox("완료",value=g["state"]=="done",key="goal_done_"+g["id"],label_visibility="collapsed")
        if checked!=(g["state"]=="done"):
            db.execute("UPDATE demo_goals SET state=? WHERE id=? AND owner=?",("done" if checked else "active",g["id"],owner))
            st.rerun()
        cols[1].write(g["title"])
        if g["parent"]:
            cols[1].caption("장기목표 연결: "+g["parent"])
        cols[2].caption(g["period"] or "자유 기간")
        if cols[3].button("숨기기",key="hide_"+g["id"]):
            db.execute("UPDATE demo_goals SET state='hidden' WHERE id=? AND owner=?",(g["id"],owner))
            st.rerun()
    with st.expander("숨긴 목표 복원"):
        hidden=db.execute("SELECT id,title FROM demo_goals WHERE owner=? AND state='hidden'",(owner,)).fetchall()
        for g in hidden:
            if st.button("복원 · "+g["title"],key="restore_"+g["id"]):
                db.execute("UPDATE demo_goals SET state='active' WHERE id=? AND owner=?",(g["id"],owner))
                st.rerun()
    with st.expander("＋ 목표 추가",expanded=not bool(goals)):
        with st.form("new_goal",clear_on_submit=True):
            title=st.text_input("내 목표")
            parent=st.text_input("연결할 장기목표 (선택)")
            period=st.text_input("기간 (선택)")
            if st.form_submit_button("내 목표로 저장") and title.strip():
                db.execute("INSERT INTO demo_goals VALUES (?,?,?,?,?,?,?)",(str(uuid.uuid4()),owner,title.strip(),parent.strip(),period.strip(),"active",now()))
                st.rerun()
    st.divider()
    st.subheader("이번 주 할 일")
    tasks=db.execute("SELECT * FROM demo_tasks WHERE owner=? ORDER BY done,created DESC",(owner,)).fetchall()
    for task in tasks:
        a,b,c=st.columns([.7,6,2],vertical_alignment="center")
        done=a.checkbox("완료",value=bool(task["done"]),key="task_done_"+task["id"],label_visibility="collapsed")
        if done != bool(task["done"]):
            db.execute("UPDATE demo_tasks SET done=? WHERE id=? AND owner=?",(int(done),task["id"],owner))
            st.rerun()
        b.write(task["title"])
        c.caption(task["day"] or "날짜 미정")
    with st.form("new_task",clear_on_submit=True):
        a,b=st.columns([4,2])
        todo_title=a.text_input("할 일")
        day=b.text_input("예정일 (선택)")
        if st.form_submit_button("할 일 추가") and todo_title.strip():
            db.execute("INSERT INTO demo_tasks VALUES (?,?,?,?,?,?,?)",(str(uuid.uuid4()),owner,todo_title.strip(),"",day.strip(),0,now()))
            st.rerun()

with view_study:
    st.subheader("지금 상황에 맞는 공부 방법 찾기")
    st.write("과목과 어려움을 편하게 적으면 AI가 여러 방법 중 가능한 전략과 그 이유를 보여줘요.")
    c1,c2=st.columns(2)
    course=c1.text_input("교과목",value="심리학개론")
    topic=c2.text_input("학습 주제",value="기억과 학습")
    difficulty=st.text_input("지금 어려운 점",placeholder="예: 단기기억과 장기기억이 헷갈려요.")
    task=st.text_input("과제와 목표 (선택)",placeholder="예: 두 개념의 차이를 설명하기")
    excerpt=st.text_area("강의자료 중 참고할 문장 (선택)",height=80)
    recent_methods=db.execute("SELECT strategy FROM demo_practice WHERE owner=? ORDER BY created DESC LIMIT 3",(owner,)).fetchall()
    context=StudyContext(course=course,topic=topic,difficulty=difficulty,task=task,
                         material_excerpt=excerpt,prior_methods=" ".join(x["strategy"] for x in recent_methods))
    context_key=(course,topic,difficulty,task,excerpt)
    if st.session_state.get("strategy_context") != context_key:
        st.session_state.pop("strategy_cards",None)
        st.session_state.pop("chosen_strategy",None)
        st.session_state["strategy_context"] = context_key
    if st.button("내 상황에 맞는 학습전략 보기",type="primary"):
        if client:
            try:
                with st.spinner("AI가 학습전략을 구성하고 있어요"):
                    st.session_state["strategy_cards"]=suggest_strategies(context,client,model)
                st.session_state["strategy_source"]="실제 OpenAI가 구성한 학습전략"
            except Exception as ex:
                st.warning("AI 호출 실패. 카탈로그 기반 대안을 보여줘요. 실제 AI 응답이 아닙니다. ("+safe_error_message(ex)+")")
                st.session_state["strategy_cards"]=recommend(context)
                st.session_state["strategy_source"]="학습전략 카탈로그 기반 대안"
        else:
            st.session_state["strategy_cards"]=recommend(context)
            st.session_state["strategy_source"]="학습전략 카탈로그 기반 대안 · AI 아님"
    st.caption(f"24가지 학습전략 중 관련성 높은 일부 제시 · {st.session_state.get('strategy_source','아직 추천 전')}")
    cards=st.session_state.get("strategy_cards",[])
    if cards:
        cols=st.columns(len(cards))
        for i,s in enumerate(cards):
            with cols[i].container(border=True):
                st.markdown("#### "+s["name"])
                st.write(s["reason"])
                st.caption("어떻게 해 볼까요?")
                for j,step in enumerate(s["steps"],1):
                    st.write(f"{j}. {step}")
                if st.button("이 방식으로 시작",key="pick_"+s["id"],use_container_width=True):
                    st.session_state["chosen_strategy"]=s
                    st.rerun()
    chosen=st.session_state.get("chosen_strategy")
    if chosen:
        st.divider()
        st.subheader("직접 해 보기 · "+chosen["name"])
        st.caption("학생이 먼저 작성하고 필요하면 방법이나 예시를 펼쳐 봐요.")
        if chosen.get("task_prompt"):
            st.info(chosen["task_prompt"])
        with st.form("do_practice",clear_on_submit=True):
            kind=chosen["kind"]
            if kind=="comparison":
                a,b=st.columns(2)
                concept_a=a.text_input("첫 번째 개념",value="")
                concept_b=b.text_input("두 번째 개념",value="")
                criterion=st.text_input("비교 기준 (학생이 수정할 수 있어요)",value="의미, 특징, 예시")
                a,b=st.columns(2)
                part_a=a.text_area("첫 번째 개념을 직접 설명",height=140)
                part_b=b.text_area("두 번째 개념을 직접 설명",height=140)
                student={"concept_a":concept_a,"concept_b":concept_b,
                         "criterion":criterion,"work_a":part_a,"work_b":part_b}
                attempted=bool(part_a.strip() or part_b.strip())
            elif kind=="solve":
                problem=st.text_area("문제 및 주어진 조건",height=100)
                solution=st.text_area("내 풀이 과정과 막힌 부분",height=150)
                student={"problem":problem,"student_work":solution}
                attempted=bool(solution.strip())
            else:
                answer=st.text_area("내가 직접 수행한 내용",height=170,
                                    placeholder="정리, 설명, 회상, 사례 등을 자유롭게 적어 보세요.")
                student={"student_work":answer}
                attempted=bool(answer.strip())
            if st.form_submit_button("내 수행기록 저장",type="primary"):
                if attempted:
                    db.execute("INSERT INTO demo_practice VALUES (?,?,?,?,?,?,?)",
                               (str(uuid.uuid4()),owner,course,topic,chosen["id"],
                                json.dumps(student,ensure_ascii=False),now()))
                    st.success("학생이 직접 작성한 내용이 저장됐어요.")
                else:
                    st.warning("직접 작성한 수행 내용을 먼저 입력해 주세요.")
        with st.expander("도움이 필요할 때 · 진행 방법과 선택적 예시"):
            for n,step in enumerate(chosen["steps"],1):
                st.write(f"{n}. {step}")
            if chosen.get("example"):
                st.caption("AI가 생성한 예시")
                st.write(chosen["example"])
        if st.button("다른 공부 방법 선택"):
            st.session_state.pop("chosen_strategy",None)
            st.rerun()

with view_diary:
    st.subheader("나의 학습일지")
    st.write("오늘 공부하며 느낀 점을 일기처럼 자유롭게 써 보세요. AI는 실제 표현에 근거해 브리핑 초안을 만들어요.")
    practices=db.execute("SELECT * FROM demo_practice WHERE owner=? ORDER BY created DESC LIMIT 3",(owner,)).fetchall()
    with st.expander("참고 · 최근 내가 직접 수행한 학습"):
        for p in practices:
            st.write(f"{p['course']} · {p['topic']} · {p['strategy']} · {p['created']}")
    diary=st.text_area("오늘의 공부 이야기",key="diary_text",height=210,
       placeholder="무엇을 공부했나요? 도움이 된 방법, 어려웠던 점, 흥미로웠던 것과 다음에 해 보고 싶은 것을 편하게 이야기해 보세요.")
    if st.button("AI가 일지 정리 및 브리핑 만들기",type="primary"):
        if not diary.strip():
            st.warning("일기를 먼저 작성해 주세요.")
        elif not client:
            st.error("실제 AI 브리핑에는 OpenAI API 키가 필요해요. 고정된 문구를 AI 응답으로 보여주지 않아요.")
        else:
            history=db.execute("SELECT original FROM demo_diaries WHERE owner=? ORDER BY created DESC LIMIT 3",(owner,)).fetchall()
            try:
                with st.spinner("작성한 일기에서 근거를 찾고 있어요"):
                    data=analyze_diary(diary,"\n".join(x["original"] for x in history),client,model)
                st.session_state["diary_analysis"]=data
                st.session_state["diary_analysis_id"]=str(uuid.uuid4())
            except Exception as ex:
                st.error("AI 브리핑 생성에 실패했어요. ("+safe_error_message(ex)+")")
                st.caption("학습일지 원문은 입력칸에 남아 있어요. 오류가 반복되면 표시된 HTTP 및 code 정보만 알려 주세요. API 키는 공유하지 마세요.")
    result=st.session_state.get("diary_analysis")
    if result and result["original_diary"]==diary:
        st.divider()
        st.subheader("AI가 정리한 오늘의 기록 · 학생 확인 전")
        names={"studied":"학습한 내용","well":"잘된 점","difficult":"어려웠던 점",
               "strategy":"활용한 학습방법","reason":"학생이 이야기한 이유",
               "emotion":"학습 정서","interest":"흥미 및 관심 전공",
               "next_topic":"더 알고 싶은 내용","perceived_change":"내가 느낀 변화"}
        facts=[(names[key],value) for key,value in result["facts"].items() if value]
        if facts:
            cols=st.columns(2)
            for i,(label,value) in enumerate(facts):
                with cols[i%2].container(border=True):
                    st.markdown("**"+label+"**")
                    st.write(value["text"])
                    st.caption("내 일기에서: "+value["evidence"])
        else:
            st.info("일기에 명시된 내용을 확인할 수 없어 추출 항목을 비워 두었어요.")
        st.markdown("#### 오늘의 AI 학습 브리핑")
        edit=st.text_area("브리핑 초안 · 학생이 고친 뒤 저장",value=result["briefing_draft"],
                          height=160,key="briefing_"+st.session_state["diary_analysis_id"])
        if result["questions"]:
            with st.expander("더 돌아보고 싶다면 · 선택 질문"):
                for question in result["questions"]:
                    st.write(question)
        if st.button("내 학습일지와 브리핑 저장"):
            db.execute("INSERT OR IGNORE INTO demo_diaries VALUES (?,?,?,?,?,?)",
                       (st.session_state["diary_analysis_id"],owner,diary,edit,
                        json.dumps(result["facts"],ensure_ascii=False),now()))
            st.success("학생이 확인한 일지와 브리핑이 저장됐어요.")
        st.divider()
        st.subheader("다음에 해 볼 목표 · 저장 전 제안")
        st.caption("AI가 제안한 목표는 회색 초안으로만 보여요. 내가 직접 선택할 때만 목표로 추가돼요.")
        if result["goal_candidates"]:
            for i,g in enumerate(result["goal_candidates"]):
                with st.container(border=True):
                    title=st.text_input("목표 초안",value=g["title"],
                        key="proposed_"+st.session_state["diary_analysis_id"]+"_"+str(i))
                    st.caption("제안 근거: "+g["evidence"])
                    if st.button("내 목표에 추가",key="add_proposed_"+str(i)) and title.strip():
                        gid=st.session_state["diary_analysis_id"]+":goal:"+str(i)
                        db.execute("INSERT OR IGNORE INTO demo_goals VALUES (?,?,?,?,?,?,?)",
                                   (gid,owner,title.strip(),"","","active",now()))
                        st.success("내 목표 목록에 추가했어요.")
        else:
            st.caption("일기의 근거만으로 제안할 목표 후보가 없어요. 직접 추가해도 좋아요.")
    elif result:
        st.caption("일기 내용이 바뀌었어요. 수정한 일기를 다시 분석해 주세요.")
    with st.expander("이전에 저장한 학습일지"):
        rows=db.execute("SELECT * FROM demo_diaries WHERE owner=? ORDER BY created DESC LIMIT 8",(owner,)).fetchall()
        for d in rows:
            st.caption(d["created"])
            st.write(d["original"])
            st.write(d["briefing"])
            st.divider()
