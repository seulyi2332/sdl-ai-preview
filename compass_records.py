"""Learning traces: a student-curated collection of passages and past work."""
import json
import html
import streamlit as st
from compass_store import all_rows,marks,mark_status,material_rows,get_material
from compass_journal import rows_for_diary

COLORS={"어려움":("#fff0ea","#a14c2b"),"흥미":("#eff4ff","#355fa8"),
        "핵심":("#fff9df","#8b6d17"),"질문":("#ebf7f0","#226e54")}


def marked_section(db,owner,client,model):
    items=marks(db,owner)
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
            row=st.columns([1.1,1.1,2])
            if row[0].button("확인했어요",key="mark_resolved_"+m["id"],help="목록에서 숨기지 않고 점검 완료로 이동"):
                mark_status(db,owner,m["id"],"resolved")
                st.rerun()
            if row[1].button("숨기기",key="mark_hidden_"+m["id"]):
                mark_status(db,owner,m["id"],"hidden")
                st.rerun()
            if row[2].button("이 내용에 관해 공부하기",key="mark_study_"+m["id"]):
                st.session_state["study_chat_excerpt"]=m["text"]
                st.session_state["study_chat_question"]="제가 표시한 다음 내용을 더 쉽게 설명하고 활용 예시를 보여 주세요."
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
    marked_section(db,owner,client,model)
    st.divider()
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
