"""Browsable, purposeful learning strategy cards for student independent choice.

The library has many possibilities but displays a limited number per page.
AI never auto-selects or logs a strategy as if the student chose it.
"""
import math
import streamlit as st
from sdl_upgrade.strategies import CATALOG,GROUPS
from compass_independence import choice as log_choice,student_chosen_card,recent

PER_PAGE=9


def filtered_cards(group="전체",query=""):
    q=" ".join((query or "").lower().split())
    cards=CATALOG
    if group!="전체":
        cards=[c for c in cards if c["group"]==group]
    if q:
        cards=[c for c in cards if q in " ".join([
            c["name"],c["benefit"],c["group"]," ".join(c["steps"]),
            " ".join(c["contexts"])," ".join(c["difficulties"])
        ]).lower()]
    return cards


def open_library(db,owner,course,topic):
    with st.expander("🗂️ 내가 골라 쓰는 학습전략 카드 모음",expanded=False):
        st.caption("읽기, 기억, 이해, 문제풀이, 학습계획, 성찰 등 여러 방법을 직접 비교해 보고 선택해요. AI 추천은 아래에서 따로 받을 수 있어요.")
        recent_items=recent(db,owner,course,limit=3)
        if recent_items:
            st.caption("최근 내가 선택한 방법: "+", ".join(dict.fromkeys(x["name"] for x in recent_items)))
        categories=["전체"]+list(GROUPS)
        group=st.selectbox("학습전략 유형",categories,key="strategy_library_group")
        query=st.text_input("공부 방법 찾기",key="strategy_library_query",
                            placeholder="예: 기억, 비교, 그래프, 오답, 계획")
        selected=filtered_cards(group,query)
        count=len(selected)
        st.caption(f"{len(CATALOG)}가지 학습전략 중 {count}개 표시 · 한 번에 9개씩 둘러보기")
        if not selected:
            st.info("검색된 학습전략이 없어요. 다른 단어로 찾아보세요.")
            return
        scope=(owner,group,query)
        if st.session_state.get("_strategy_library_scope")!=scope:
            st.session_state["_strategy_library_scope"]=scope
            st.session_state["strategy_library_page"]=1
        pages=math.ceil(count/PER_PAGE)
        page=min(max(int(st.session_state.get("strategy_library_page",1)),1),pages)
        st.session_state["strategy_library_page"]=page
        page_cards=selected[(page-1)*PER_PAGE:page*PER_PAGE]
        for start in range(0,len(page_cards),3):
            cols=st.columns(3,gap="small")
            for col,c in zip(cols,page_cards[start:start+3]):
                with col.container(border=True):
                    st.caption(c["group"])
                    st.markdown("**"+c["name"]+"**")
                    st.write(c["benefit"])
                    with st.expander("어떻게 공부하나요?"):
                        for i,step in enumerate(c["steps"],1):
                            st.caption(f"{i}. {step}")
                    if st.button("이 방법 선택",key="study_library_choose_"+c["id"],
                                 use_container_width=True):
                        # Click -> explicit student choice -> record, never by rerun.
                        log_choice(db,owner,course,topic,c["id"],"student")
                        st.session_state["study_strategy_selected"]=c["id"]
                        st.session_state["study_strategy_self_card"]=student_chosen_card(c["id"])
                        st.session_state["study_strategy_info"]="내가 직접 선택한 학습전략이에요. 아래에서 직접 해 볼 수 있어요."
                        st.rerun()
        a,b,c=st.columns([1,1.8,1],vertical_alignment="center")
        if a.button("이전 카드",key="strategy_library_prev",disabled=page<=1,use_container_width=True):
            st.session_state["strategy_library_page"]=page-1
            st.rerun()
        c.caption(f"{page} / {pages} 페이지")
        if b.button("다음 카드",key="strategy_library_next",disabled=page>=pages,
                    use_container_width=True):
            st.session_state["strategy_library_page"]=page+1
            st.rerun()
