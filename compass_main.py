"""나의 학습나침반: a learner-controlled compact self-directed learning app."""
import os
import json
import streamlit as st
from openai import OpenAI
from compass_store import connect, migrate_tasks
from compass_views import home_view, goal_view, study_view, diary_view, records_view

MENU=("오늘","목표와 계획","공부하기","학습일지","내 기록")

STYLE="""<style>
:root {--sea:#155d56;--mist:#edf7f4;--ink:#182b31;--moss:#597168;--sand:#f8f6f1;}
html,body,[data-testid="stAppViewContainer"]{background:#fafaf7;color:#1e3033;}
.block-container{max-width:1310px;padding-top:1.1rem;padding-bottom:3rem;}
h1,h2,h3{letter-spacing:-.045em;color:#153b36;}
h1{font-weight:780!important;} h3{margin:0.1rem 0!important;}
div[data-testid="stVerticalBlockBorderWrapper"]{border-radius:17px;border-color:#e6eae5;}
.stButton>button{border-radius:13px;min-height:38px;}
.stButton>button[kind="primary"]{background:#155d56;border-color:#155d56;color:white;}
.stButton>button[kind="primary"]:hover{background:#0a403b;border-color:#0a403b;}
[data-testid="stSidebar"]{background:#f4f7f3;}
[data-testid="stMetric"]{background:#edf7f4;padding:12px 16px;border-radius:14px;}
[data-testid="stWidgetLabel"]{font-weight:600;}
[data-testid="stFileUploader"]{border-radius:14px;}
.st-key-compass_page [role="radiogroup"]{gap:.45rem;}
div[data-testid="stExpander"]{border-radius:14px;}
.hero{padding:24px 27px;background:linear-gradient(115deg,#e2f2eb 0%,#f5f7ee 100%);border:1px solid #d9e9e0;border-radius:20px;margin-bottom:12px;}
.hero .eyebrow{color:#537c70;font-size:12px;font-weight:700;letter-spacing:.11em;}
.hero h2{margin:.2rem 0;font-size:28px;}
.hero p{margin:0;color:#516b66;font-size:14px;}
.lane{padding:10px 12px;border-radius:13px;background:#f1f4f1;font-weight:700;font-size:13px;}
.smallcaps{font-size:12px;letter-spacing:.05em;color:#5c736e;font-weight:700;}
.note{background:#f5f4ee;border-radius:12px;padding:14px 17px;margin:5px 0 12px;line-height:1.7;}
</style>"""


def secret(name):
    v=os.environ.get(name)
    if v:
        return v
    try:
        if name in st.secrets:
            return str(st.secrets[name])
        for sec in st.secrets.values():
            if hasattr(sec,"get") and sec.get(name):
                return str(sec[name])
    except (FileNotFoundError,RuntimeError,KeyError):
        pass
    return ""


@st.cache_resource(show_spinner=False)
def client_for(key):
    return OpenAI(api_key=key,timeout=90,max_retries=1)


def change_page(page):
    st.session_state["_compass_go"]=page
    st.rerun()


def run():
    st.set_page_config(page_title="나의 학습나침반",page_icon="🧭",layout="wide",initial_sidebar_state="expanded")
    st.markdown(STYLE,unsafe_allow_html=True)
    key=secret("OPENAI_API_KEY")
    client=client_for(key) if key else None
    model=secret("OPENAI_MODEL") or "gpt-4o-mini"
    with st.sidebar:
        st.markdown("## 🧭 나의 학습나침반")
        st.caption("내가 목표를 정하고 공부하며 돌아보는 공간")
        owner=st.text_input("접속 코드",value="DEMO01",max_chars=40)
        st.divider()
        st.caption("AI는 근거와 선택지를 제공해요. 목표, 수행, 점검, 조정은 내가 결정해요.")
        st.caption("이 시연 앱의 접속 코드는 보안 인증이 아니며, 저장 정보는 서버 재시작 시 없어질 수 있어요.")
        if client:
            st.caption("● AI 연결 설정됨 · 실제 응답은 요청 시 확인")
        else:
            st.warning("AI API 키 없음 · 전략은 카탈로그로 안내")
    allowed=secret("PARTICIPANT_CODES")
    configured={x.strip() for x in allowed.replace("\n",",").split(",") if x.strip()}
    if not (owner.isalnum() and 5<=len(owner)<=40 and (owner.startswith("DEMO") or owner in configured)):
        st.error("시연 코드는 DEMO로 시작해요. 별도 참여 코드는 관리자가 설정한 경우에만 사용할 수 있어요.")
        st.stop()
    if st.session_state.get("_active_owner")!=owner:
        for k in list(st.session_state):
            if k not in ("_active_owner","compass_page","_compass_go"):
                # clear widget state and pending AI drafts between codes, never share drafts
                if k.startswith(("study_","pdf_","mark_","strat_","chosen_","diary_","brief_","chat_","goal_","task_","pdfopt_","home_","board_","marks_","selfcheck_","_study_")):
                    st.session_state.pop(k,None)
        st.session_state["_active_owner"]=owner
    db=connect()
    migrate_tasks(db,owner)
    target=st.session_state.pop("_compass_go",None)
    if target in MENU:
        st.session_state["compass_page"]=target
    st.markdown('<div class="smallcaps">MY LEARNING COMPASS</div>',unsafe_allow_html=True)
    st.title("나의 학습나침반")
    st.radio("이동",MENU,key="compass_page",horizontal=True,label_visibility="collapsed")
    st.divider()
    page=st.session_state["compass_page"]
    params=dict(db=db,owner=owner,client=client,model=model)
    if page=="오늘":
        home_view(**params)
    elif page=="목표와 계획":
        goal_view(**params)
    elif page=="공부하기":
        study_view(**params)
    elif page=="학습일지":
        diary_view(**params)
    else:
        records_view(**params)


if __name__=="__main__":
    run()
