"""Student-owned self-evaluation: one source shown in goal and learning records."""
import streamlit as st
from compass_store import all_rows


def latest_for_goal(db,owner,goal_id):
    rows=all_rows(db,"""SELECT evaluation,memo,created FROM compass_selfcheck
        WHERE owner=? AND goal_id=? ORDER BY created DESC,rowid DESC LIMIT 1""",
        (owner,goal_id))
    return rows[0] if rows else None


def recent_with_goals(db,owner,limit=20):
    return all_rows(db,"""SELECT s.id,s.goal_id,s.evaluation,s.memo,s.created,
                 COALESCE(g.title,'이전에 설정한 목표') AS goal_title
        FROM compass_selfcheck s
        LEFT JOIN demo_goals g ON g.id=s.goal_id AND g.owner=s.owner
        WHERE s.owner=? ORDER BY s.created DESC,s.rowid DESC LIMIT ?""",
        (owner,limit))


def records_section(db,owner):
    history=recent_with_goals(db,owner,limit=20)
    with st.expander("✅ 목표별 자기평가 기록"+(f" · {len(history)}개" if history else ""),expanded=bool(history)):
        if not history:
            st.caption("아직 목표에 대한 자기평가가 없어요. 학습일지 아래에서 목표를 골라 평가할 수 있어요.")
        for row in history:
            with st.container(border=True):
                st.markdown("**"+row["goal_title"]+"**")
                st.caption(row["created"][:16]+" · "+row["evaluation"])
                if row["memo"]:
                    st.write("내가 판단한 근거와 다음에 바꿔 볼 점: "+row["memo"])
                if st.button("이 목표에서 평가 확인",key="record_selfcheck_goal_"+row["id"]):
                    st.session_state["goal_focus_id"]=row["goal_id"]
                    st.session_state["_compass_go"]="목표와 계획"
                    st.rerun()
    st.caption("자기평가는 완료 체크와 별개이며, 목표 수정이나 다음 계획 반영은 내가 선택해요.")
