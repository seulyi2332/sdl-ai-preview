"""An actual AI conversation starts at the selected PDF paragraph, not a status-only link."""
import streamlit as st
from compass_chat import answer
from compass_store import chat_messages,put_chat,interest_for
from sdl_upgrade.model_client import safe_error_message

PROMPTS={
    "어려움":"이 문단에서 이해하기 어려운 부분을 구체적으로 짚고 쉬운 설명과 작은 예시를 주세요. 제가 다시 생각해 볼 질문을 하나 해 주세요.",
    "흥미":"이 문단에서 흥미로운 내용을 실제 사례와 연결해 설명해 주세요. 제 관심을 더 탐색할 수 있는 질문을 하나 해 주세요. 특정 전공을 추천하거나 결정하지 마세요.",
    "핵심":"제가 핵심이라고 표시한 이 문단의 의미를 제 말로 설명할 수 있도록 핵심 내용을 명료하게 짚고 확인 질문을 하나 해 주세요.",
    "질문":"제가 질문으로 표시한 문단을 읽고 문단에 실제로 담긴 내용부터 설명해 주세요. 궁금한 점을 구체화하도록 질문 하나를 덧붙여 주세요."
}


def question_from_selection(kind,note=""):
    """Keep the student's typed question as the real request; no forced template."""
    note=str(note or "").strip()
    if note:
        return "제가 선택한 PDF 문단에 대한 질문 또는 메모예요: "+note[:650]
    return PROMPTS.get(kind,PROMPTS["질문"])


def send_pdf_message(db,owner,client,model,course,topic,excerpt,question):
    """Call the model and save the actual turn only after a real response."""
    if not client:
        raise ValueError("AI API 키가 연결되지 않아 응답을 만들 수 없어요.")
    if not str(excerpt or "").strip():
        raise ValueError("먼저 공부할 문단을 선택해 주세요.")
    q=str(question or "").strip()
    if not q:
        raise ValueError("궁금한 내용을 적어 주세요.")
    history=chat_messages(db,owner,course,limit=12)
    response=answer(client,model,course,topic,q,history,
                    excerpt=str(excerpt)[:4800],interest=interest_for(db,owner))
    put_chat(db,owner,course,"user",q)
    put_chat(db,owner,course,"assistant",response)
    return response


def active_view(db,owner,client,model,course,topic,material_id,paragraph_id):
    active=st.session_state.get("pdf_inline_chat")
    if (not isinstance(active,dict)
        or active.get("owner")!=owner or active.get("material_id")!=material_id
        or active.get("paragraph_id")!=paragraph_id):
        return
    with st.container(border=True):
        st.markdown("#### 💬 선택한 문단에 대한 AI 답변")
        st.caption("선택한 PDF 문단과 내 질문을 바탕으로 생성한 실제 AI 응답이에요. AI가 직접 확인하지 않은 내용은 강의자료의 사실로 단정하지 않아요.")
        for item in active.get("turns",[])[-8:]:
            with st.chat_message(item["role"]):
                st.write(item["text"])
        if not client:
            st.warning("AI 연결이 없어서 이어서 질문할 수 없어요.")
            return
        with st.form("pdf_inline_followup_"+paragraph_id,clear_on_submit=True):
            more=st.text_area("이 문단에 대해 이어서 질문하기",height=85,
                 placeholder="예: 조금 더 쉬운 예시로 설명해 줘. / 다른 개념과 어떻게 달라?")
            submitted=st.form_submit_button("AI에게 질문 보내기",type="primary")
        if submitted:
            try:
                with st.spinner("선택한 문단과 앞선 대화를 읽고 있어요"):
                    response=send_pdf_message(db,owner,client,model,course,topic,
                                              active["excerpt"],more)
                active["turns"].extend([{"role":"user","text":more.strip()},
                                         {"role":"assistant","text":response}])
                st.session_state["pdf_inline_chat"]=active
                st.rerun()
            except Exception as exc:
                st.error("AI 답변을 받지 못했어요 · "+safe_error_message(exc))
                st.caption("질문을 다시 입력할 수 있어요.")


def start_pdf_chat(db,owner,client,model,course,topic,material_id,paragraph_id,excerpt,kind,note):
    q=question_from_selection(kind,note)
    response=send_pdf_message(db,owner,client,model,course,topic,excerpt,q)
    st.session_state["study_chat_excerpt"]=excerpt
    st.session_state["pdf_inline_chat"]={
       "owner":owner,"material_id":material_id,"paragraph_id":paragraph_id,
       "course":course,"topic":topic,"excerpt":excerpt,
       "turns":[{"role":"user","text":q},{"role":"assistant","text":response}]}
    return response
