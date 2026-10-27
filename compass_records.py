"""Learning traces: a student-curated collection of passages and past work."""
import json
import html
import streamlit as st
from compass_store import all_rows,marks,mark_status,material_rows,get_material
from compass_journal import rows_for_diary
from compass_independence import recent as recent_strategy_choices
from compass_highlights import label as difficulty_label,set_label as set_difficulty_label
from compass_major_links import record_exploration
from compass_selfcheck_links import records_section

COLORS={"어려움":("#ffd1d4","#873b44"),"흥미":("#cfe3ff","#305889"),
        "핵심":("#ffefab","#75591c"),"질문":("#c8f0d9","#246b49")}


def marked_section(db,owner,client,model):
    items=marks(db,owner)
    focus_id=st.session_state.pop("focus_mark_id",None)
    if focus_id and any(m["id"]==focus_id for m in items):
        items.sort(key=lambda m:(m["id"]!=focus_id))
        st.info("홈에서 선택한 어려움을 맨 위에 보여주고 있어요.")
    counts={kind:sum(x["kind"]==kind for x in items) for kind in COLORS}
    st.markdown("### 내가 표시한 학습 내용")
    st.caption("PDF에서 내가 직접 선택한 문단만 모았어요. 흥미 및 어려움은 AI가 판정한 값이 아니에요.")
    heads=st.columns(4)
    for col,(name,n) in zip(heads,counts.items()):
        col.metric(name,f"{n}개")
    selection=st.segmented_control("표시 유형",["전체"]+list(COLORS),
                                   default="전체",key="marks_filter")
    if selection and selection!="전체":
        items=[m for m in items if m["kind"]==selection]
    if not items:
        st.info("표시한 내용이 아직 없어요. PDF에서 '어려움'이나 '흥미' 등을 눌러 기록할 수 있어요.")
    for m in items:
        bg,fg=COLORS.get(m["kind"],("#f4f4f4","#444"))
        with st.container(border=True):
            st.markdown(f"<span style='display:inline-block;background:{bg};color:{fg};"
                        f"font-weight:700;border-radius:8px;padding:4px 10px;font-size:12px;'>"
                        f"{html.escape(m['kind'])}</span> "
                        f"<span style='color:#6a7a76;font-size:12px'>{html.escape(m['material_title'])}</span>",
                        unsafe_allow_html=True)
            st.markdown("<div class='note'>"+html.escape(m["text"][:1200])+"</div>",unsafe_allow_html=True)
            if m["note"]:
                st.caption("내가 남긴 메모: "+m["note"])
            if m["kind"]=="어려움":
                with st.expander("홈 키워드 이름 정하기 · 선택"):
                    st.caption("원문에서 가져온 문구를 홈에서 내가 알아보기 쉬운 이름으로 바꿀 수 있어요.")
                    with st.form("rename_mark_"+m["id"]):
                        keyword=st.text_input("내 키워드",value=difficulty_label(m),max_chars=65)
                        if st.form_submit_button("키워드 저장"):
                            try:
                                set_difficulty_label(db,owner,m["id"],keyword)
                                st.success("홈의 어려움 카드에 표시할 이름을 저장했어요.")
                            except ValueError as ex:
                                st.warning(str(ex))
            row=st.columns([1.1,1.1,2])
            if row[0].button("확인했어요",key="mark_resolved_"+m["id"],help="목록에서 숨기지 않고 점검 완료로 이동"):
                mark_status(db,owner,m["id"],"resolved")
                st.rerun()
            if row[1].button("숨기기",key="mark_hidden_"+m["id"]):
                mark_status(db,owner,m["id"],"hidden")
                st.rerun()
            if row[2].button("이 내용에 관해 공부하기",key="mark_study_"+m["id"]):
                st.session_state["study_chat_excerpt"]=m["text"]
                if m["kind"]=="어려움":
                    st.session_state["study_difficulty"]="내가 어렵다고 표시한 부분: "+m["text"][:340]
                    st.session_state["study_chat_question"]="제가 어려움을 표시한 이 문단을 쉽게 설명하고 예시로 보여 주세요."
                elif m["kind"]=="흥미":
                    st.session_state["study_chat_question"]="내가 흥미를 표시한 내용이에요. 교과목과 관심 전공에 연결해 자세히 알아보고 싶어요."
                else:
                    st.session_state["study_chat_question"]="제가 표시한 내용을 정확하게 이해할 수 있게 예시를 보여 주세요."
                st.session_state["_compass_go"]="공부하기"
                st.rerun()
    archived=[m for m in marks(db,owner,include_hidden=True) if m["state"] in ("hidden","resolved")]
    if archived:
        with st.expander(f"숨기거나 점검한 표시 {len(archived)}개"):
            for m in archived:
                a,b=st.columns([5,1],vertical_alignment="center")
                a.caption(m["kind"]+" · "+m["text"][:110]+" · "+("확인" if m["state"]=="resolved" else "숨김"))
                if b.button("다시 보기",key="mark_restore_"+m["id"]):
                    mark_status(db,owner,m["id"],"active")
                    st.rerun()


def records_view(db,owner,client,model):
    st.markdown('<div class="hero"><div class="eyebrow">LEARNING TRACE · 나의 학습 흔적</div>'
                '<h2>내가 중요하게 표시한 것들</h2>'
                '<p>어려웠던 내용, 흥미로운 문단, 직접 수행한 활동을 다시 찾아볼 수 있어요.</p></div>',
                unsafe_allow_html=True)
    mode=st.segmented_control("기록 보기",["하이라이트 모음","전체 기록"],
                               default="하이라이트 모음",key="records_mode")
    marked_section(db,owner,client,model)
    if mode=="하이라이트 모음":
        st.caption("선택한 문장만 모아서 보는 화면이에요. 전체 기록을 누르면 학습활동과 학습일지도 확인할 수 있어요.")
        return
    st.divider()
    record_exploration(db,owner)
    with st.expander("내가 선택한 학습전략 돌아보기 · 선택",expanded=False):
        history=recent_strategy_choices(db,owner,limit=20)
        if not history:
            st.caption("공부할 때 전략을 직접 고르거나 AI 제안을 보고 선택하면 여기에 기록돼요.")
        for selected in history:
            origin=("스스로 선택" if selected["choice_source"]=="student"
                    else "AI 제안을 보고 선택")
            st.caption(selected["created"][:16]+" · "+origin+" · "+selected["course"])
            st.markdown("**"+html.escape(selected["name"])+"**")
        st.caption("이 기록은 선택 경로를 보여 줄 뿐, 자기주도학습역량을 채점하지 않아요.")
    with st.expander("직접 해 본 학습활동",expanded=False):
        activities=all_rows(db,"SELECT * FROM demo_practice WHERE owner=? ORDER BY created DESC LIMIT 40",(owner,))
        if not activities:
            st.caption("아직 직접 수행한 학습기록이 없어요.")
        for a in activities:
            with st.container(border=True):
                st.caption(a["created"][:16]+" · "+(a["course"] or "과목 없음"))
                st.markdown("**"+(a["topic"] or "자유 학습")+" · "+a["strategy"]+"**")
                with st.expander("내가 쓴 답 보기"):
                    st.json(json.loads(a["student_work"]),expanded=False)
    with st.expander("이전 학습일지",expanded=False):
        diaries=rows_for_diary(db,owner,limit=20)
        if not diaries:
            st.caption("저장한 일지가 없어요.")
        for d in diaries:
            with st.container(border=True):
                st.caption(d["created"][:16])
                st.write(d["original"])
                if d["briefing"]:
                    st.caption("확인한 브리핑")
                    st.write(d["briefing"])
