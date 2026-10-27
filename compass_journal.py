"""Diary-led self-reflection with AI proposals that never become decisions by default."""
import json
import html
import streamlit as st
from sdl_upgrade.journal import analyze_diary
from sdl_upgrade.model_client import safe_error_message
from compass_store import all_rows,ident,now
from compass_progress import criterion_for,time_summaries,adjustments
from compass_independence import recent as recent_strategy_choices

CATEGORY={
  "studied":"오늘 배운 것","well":"잘된 점","difficult":"어려웠던 점",
  "strategy":"시도한 공부 방법","reason":"그렇게 느낀 이유",
  "emotion":"공부할 때 느낀 정서","interest":"관심이 생긴 내용",
  "next_topic":"더 알고 싶은 내용","perceived_change":"내가 느낀 변화"
}


def _journal_init(db):
    db.execute("""CREATE TABLE IF NOT EXISTS compass_diary_visibility
                  (owner TEXT NOT NULL,diary_id TEXT NOT NULL,hidden INTEGER NOT NULL DEFAULT 0,
                   PRIMARY KEY(owner,diary_id))""")


def rows_for_diary(db,owner,show_hidden=False,limit=50):
    _journal_init(db)
    return all_rows(db,"""SELECT d.*,COALESCE(v.hidden,0) AS hidden
        FROM demo_diaries d LEFT JOIN compass_diary_visibility v
          ON v.owner=d.owner AND v.diary_id=d.id
        WHERE d.owner=? """+("" if show_hidden else " AND COALESCE(v.hidden,0)=0 ")+
        "ORDER BY d.created DESC LIMIT ?",(owner,limit))


def set_hidden(db,owner,diary_id,hidden=True):
    _journal_init(db)
    db.execute("""INSERT INTO compass_diary_visibility(owner,diary_id,hidden) VALUES (?,?,?)
         ON CONFLICT(owner,diary_id) DO UPDATE SET hidden=excluded.hidden""",
         (owner,diary_id,1 if hidden else 0))


def journal_form(db,owner,client,model):
    st.markdown('<div class="hero"><div class="eyebrow">REFLECT · 오늘의 성장 기록</div>'
                '<h2>나의 학습일지</h2><p>내 말로 오늘을 기록하면 AI가 내가 말한 근거를 정리해 줘요.'
                ' 바꿀 것은 내가 선택해요.</p></div>',unsafe_allow_html=True)
    recent=all_rows(db,"SELECT * FROM demo_practice WHERE owner=? ORDER BY created DESC LIMIT 4",(owner,))
    if recent:
        with st.expander("참고 · 최근 직접 해 본 활동"):
            for r in recent:
                st.caption(f"● {r['course'] or '교과목 미정'} · {r['topic'] or '자유 학습'}")
                st.write(r["strategy"])
    with st.expander("📎 성찰에 참고할 내 학습기록 · 필요할 때 펼치기",expanded=False):
        examples=all_rows(db,"""SELECT m.kind,m.text,d.title FROM compass_marks m
           JOIN compass_materials d ON d.id=m.material_id AND d.owner=m.owner
           WHERE m.owner=? AND m.state='active' ORDER BY m.created DESC LIMIT 4""",(owner,))
        times=time_summaries(db,owner,limit=3)
        if not examples and not times:
            st.caption("기록이 없어도 일기를 자유롭게 쓸 수 있어요.")
        log_table=db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='compass_feedback_log'").fetchone()
        if log_table:
            feedbacks=all_rows(db,"""SELECT feedback,created FROM compass_feedback_log
                              WHERE owner=? ORDER BY created DESC LIMIT 2""",(owner,))
            if feedbacks:
                st.caption("내가 요청했던 AI 학습 피드백 (참고)")
                for f in feedbacks:
                    st.write(f["feedback"][:430])
        for m in examples:
            st.caption("● 내가 표시한 "+m["kind"]+" · "+m["title"])
            st.write(m["text"][:350])
        if times:
            st.markdown("**내가 기록한 계획시간과 실제시간**")
            for row in times:
                estimate="미입력" if row["estimated"] is None else str(row["estimated"])+"분"
                actual="미입력" if row["actual"] is None else str(row["actual"])+"분"
                st.write(f"- {row['title']}: 예상 {estimate}, 실제 {actual}")
                if row["reason"]:
                    st.caption("내가 생각한 이유: "+row["reason"])
        chosen_methods=recent_strategy_choices(db,owner,limit=4)
        if chosen_methods:
            st.markdown("**최근 내가 선택했던 공부 방법**")
            for m in chosen_methods:
                label="내가 직접 고른 방법" if m["choice_source"]=="student" else "AI 제안을 보고 내가 고른 방법"
                st.caption(label+" · "+m["name"]+" · "+(m["course"] or "교과목 미설정"))
        st.caption("이 기록은 참고자료예요. 학습일지에 무엇을 쓸지는 내가 결정해요.")
    text=st.text_area("오늘의 공부 이야기",key="diary_story",height=210,
      placeholder="오늘 무엇을 공부했나요?\n어떤 부분이 도움이 됐고 무엇이 어려웠나요?\n흥미로웠던 주제나 다음에 해 보고 싶은 공부가 있다면 편하게 적어 보세요.")
    diary_controls=st.columns([1,1.6])
    if diary_controls[0].button("내 일지만 저장",key="diary_save_direct"):
        if text.strip():
            existing=db.execute("""SELECT id FROM demo_diaries
                 WHERE owner=? AND original=? AND briefing='' ORDER BY created DESC LIMIT 1""",
                 (owner,text.strip())).fetchone()
            if existing:
                st.info("이미 같은 내용의 일기를 저장했어요. 지난 학습일지에서 확인할 수 있어요.")
            else:
                db.execute("""INSERT INTO demo_diaries
                     (id,owner,original,briefing,analysis,created) VALUES(?,?,?,?,?,?)""",
                     (ident(),owner,text.strip(),"","{}",now()))
                st.success("AI 브리핑 없이 내가 쓴 일기를 그대로 저장했어요.")
        else:
            st.warning("일기에 오늘의 이야기를 먼저 작성해 주세요.")
    if diary_controls[1].button("AI에게 오늘의 브리핑 부탁하기",key="diary_analyze",type="primary"):
        if not text.strip():
            st.warning("먼저 오늘 공부한 이야기를 적어 주세요.")
        elif not client:
            st.error("OpenAI API 키가 없어 실제 AI 브리핑을 만들 수 없어요.")
        else:
            history=rows_for_diary(db,owner)[:3]
            previous="\n".join(r["original"][:1100] for r in history)
            try:
                with st.spinner("내가 쓴 표현을 기준으로 정리하는 중이에요"):
                    draft=analyze_diary(text,previous,client,model)
                draft["id"]=ident()
                st.session_state["diary_draft"]=draft
                st.session_state.pop("diary_error",None)
            except Exception as exc:
                st.session_state["diary_error"]=safe_error_message(exc)
    if st.session_state.get("diary_error"):
        st.error("AI 브리핑 생성 실패 · "+st.session_state["diary_error"])
        st.caption("일기 원문은 그대로 남아 있어요. API 키를 다른 사람에게 보내지 마세요.")
    draft=st.session_state.get("diary_draft")
    if not draft:
        saved_journal(db,owner)
        return
    if draft.get("original_diary") != text:
        st.info("일기 내용을 수정했어요. 다시 브리핑을 만들면 새 내용을 반영할 수 있어요.")
        saved_journal(db,owner)
        return
    st.markdown("### 내가 말한 오늘의 학습")
    confirmed=[(k,v) for k,v in draft.get("facts",{}).items() if isinstance(v,dict)]
    if not confirmed:
        st.caption("확인할 수 있는 표현이 있을 때만 뽑아 보여줘요.")
    else:
        cols=st.columns(2)
        for i,(key,value) in enumerate(confirmed):
            with cols[i%2].container(border=True):
                st.caption(CATEGORY.get(key,key))
                st.write(value.get("text") or "")
                st.caption("내 원문: "+(value.get("evidence") or ""))
    st.markdown("### 오늘의 AI 브리핑")
    st.caption("초안이에요. 내가 고쳐 저장해야 내 기록이 돼요.")
    briefing=st.text_area("내가 확인하고 다듬는 브리핑",value=draft.get("briefing_draft") or "",
                          height=145,key="brief_"+draft["id"])
    with st.container(border=True):
        a,b=st.columns(2)
        if a.button("내 일지와 브리핑 저장하기",type="primary",key="diary_save_"+draft["id"]):
            db.execute("""INSERT OR IGNORE INTO demo_diaries
                           (id,owner,original,briefing,analysis,created)
                           VALUES (?,?,?,?,?,?)""",
                (draft["id"],owner,text,briefing,
                 json.dumps(draft.get("facts") or {},ensure_ascii=False),now()))
            st.success("내가 확인한 학습일지와 브리핑을 저장했어요.")
        b.caption("AI는 학생의 자기평가를 대신하지 않아요.")
    with st.expander("내가 생각해 볼 질문 (선택)"):
        if not draft.get("questions"):
            st.caption("현재 글만으로 충분할 수 있어요.")
        for q in draft.get("questions") or []:
            st.write("• "+q)
    st.markdown("### 내일로 이어지는 작은 목표")
    st.caption("AI가 정리한 후보는 선택 전까지 저장되지 않아요.")
    if not draft.get("goal_candidates"):
        st.caption("일기 속 분명한 근거가 없으면 AI는 목표를 만들지 않아요.")
    for i,g in enumerate(draft.get("goal_candidates") or []):
        with st.container(border=True):
            proposed=st.text_input("목표 초안",value=g.get("title") or "",
                                   key=f"diary_goal_{draft['id']}_{i}")
            st.caption("내가 말한 근거 · "+(g.get("evidence") or ""))
            if st.button("내 목표에 추가",key=f"diary_goal_save_{draft['id']}_{i}"):
                if proposed.strip():
                    db.execute("INSERT OR IGNORE INTO demo_goals VALUES(?,?,?,?,?,?,?)",
                               (f"{draft['id']}:goal:{i}",owner,proposed.strip(),"","","active",now()))
                    st.success("내가 선택한 목표를 추가했어요. '목표와 계획'에서 확인하고 할 일을 연결할 수 있어요.")
    saved_journal(db,owner)


def saved_journal(db,owner):
    with st.expander("지난 학습일지와 브리핑",expanded=False):
        rows=rows_for_diary(db,owner,limit=15)
        if not rows:
            st.caption("아직 저장한 일지가 없어요.")
        for r in rows:
            with st.container(border=True):
                st.caption(r["created"][:16])
                st.write(r["original"])
                if r["briefing"]:
                    st.markdown("**AI 브리핑 · 내가 확인한 내용**")
                    st.write(r["briefing"])
                if st.button("숨기기",key="diary_hide_"+r["id"]):
                    set_hidden(db,owner,r["id"],True)
                    st.rerun()
        hidden=[r for r in rows_for_diary(db,owner,True) if r["hidden"]]
        if hidden:
            with st.expander(f"숨겨 둔 일지 {len(hidden)}개"):
                for r in hidden:
                    a,b=st.columns([5,1])
                    a.caption(r["created"][:16]+" · "+r["original"][:70])
                    if b.button("복원",key="diary_restore_"+r["id"]):
                        set_hidden(db,owner,r["id"],False)
                        st.rerun()


def selfcheck(db,owner):
    st.markdown("### 내가 평가한 목표 도달 정도")
    st.caption("완료한 할 일 수로 목표 성취율을 계산하지 않아요. 기준과 경험을 바탕으로 학생이 직접 평가해요.")
    goals=all_rows(db,"SELECT * FROM demo_goals WHERE owner=? AND state!='hidden'",(owner,))
    if not goals:
        st.caption("목표가 없으면 건너뛰어도 괜찮아요.")
        return
    options={g["id"]:g["title"] for g in goals}
    goal_id=st.selectbox("돌아볼 목표",list(options),format_func=lambda x:options[x],key="selfcheck_goal")
    criterion=criterion_for(db,owner,goal_id)
    if criterion:
        with st.container(border=True):
            st.caption("내가 목표에 설정한 확인 기준")
            st.write(criterion)
            st.caption("실제 수행한 내용과 이 기준을 비교하여 스스로 평가해 주세요.")
    else:
        st.caption("목표의 도달 기준은 '목표와 계획'에서 직접 정할 수 있어요.")
    previous=all_rows(db,"SELECT * FROM compass_selfcheck WHERE owner=? AND goal_id=? ORDER BY created DESC LIMIT 2",
                      (owner,goal_id))
    if previous:
        st.caption("이전 자기평가: "+", ".join(r["evaluation"] for r in previous))
    evaluation=st.radio("이번 학습을 통해 목표에 얼마나 가까워졌다고 느끼나요?",
                        ["잘 해냈다","어느 정도 했다","조정이 필요하다","아직 평가하기 어렵다"],
                        index=None,key="selfcheck_rating",horizontal=True)
    memo=st.text_area("그렇게 생각한 이유와 다음에 바꿔 볼 점 (선택)",key="selfcheck_memo",height=90)
    if st.button("내 자기평가 저장",key="selfcheck_save"):
        if not evaluation:
            st.warning("내가 선택한 평가를 먼저 골라 주세요.")
        else:
            db.execute("INSERT INTO compass_selfcheck VALUES(?,?,?,?,?,?)",
                       (ident(),owner,goal_id,evaluation,memo,now()))
            st.success("직접 내린 평가를 저장했어요.")
