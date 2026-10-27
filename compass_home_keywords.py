"""Compact home shortcuts to student-marked difficulties.

Shows the learner's own source words, not AI-generated difficulty diagnoses.
"""
import html
import streamlit as st
from compass_highlights import difficulty_items,label


def render_home_difficulties(db,owner):
    marked=difficulty_items(db,owner,limit=7)
    if not marked:
        return
    st.markdown("### 🌷 다시 보고 싶은 어려운 내용")
    st.caption("PDF에서 내가 ‘어려움’으로 표시한 내용을 다시 찾기 쉽게 모았어요. 제목은 원문 일부이며 직접 고칠 수도 있어요.")
    visible=marked[:6]
    for pos in range(0,len(visible),3):
        cols=st.columns(3,gap="small")
        for col,mark in zip(cols,visible[pos:pos+3]):
            with col.container(border=True):
                st.caption("어려움 · "+mark["material_title"][:32])
                st.markdown("**"+html.escape(label(mark))+"**",unsafe_allow_html=True)
                with st.expander("표시한 문장 확인"):
                    st.write(mark["text"][:950])
                    if mark["note"]:
                        st.caption("나의 메모: "+mark["note"])
                a,b=st.columns(2,gap="small")
                if a.button("다시 보기",key="home_review_difficulty_"+mark["id"],
                            use_container_width=True):
                    st.session_state["marks_filter"]="어려움"
                    st.session_state["records_mode"]="하이라이트 모음"
                    st.session_state["focus_mark_id"]=mark["id"]
                    st.session_state["_compass_go"]="내 기록"
                    st.rerun()
                if b.button("공부하기",key="home_study_difficulty_"+mark["id"],
                            use_container_width=True,type="primary"):
                    st.session_state["study_chat_excerpt"]=mark["text"]
                    st.session_state["study_difficulty"]="내가 어렵다고 표시한 내용: "+mark["text"][:320]
                    st.session_state["study_chat_question"]="내가 어려움으로 표시한 이 내용을 이해할 수 있도록 구체적인 사례와 단서를 제공해 주세요."
                    st.session_state["_compass_go"]="공부하기"
                    st.rerun()
    if len(marked)>6:
        st.caption("그 밖의 어려움은 ‘내 기록 → 하이라이트 모음’에서 다시 볼 수 있어요.")
