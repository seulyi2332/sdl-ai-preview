"""A compact task Kanban and goal map. Task completion is not goal achievement."""
import html
import streamlit as st
from compass_store import all_rows,task_rows,add_task,change_task,ident,now,STATES,interest_for,save_interest
from compass_progress import criterion_for,save_criterion,save_time,latest_time,revise_goal,adjustments
from compass_major_links import goal_exploration

VISIBLE=STATES[:4]
LABELS={"시작 전":"○ 시작 전","진행 중":"◐ 진행 중",
        "도움 필요":"↝ 도움 필요","완료":"✓ 완료"}


def _jump(page):
    st.session_state["_compass_go"]=page
    st.rerun()


def active_goals(db,owner):
    return all_rows(db,"SELECT * FROM demo_goals WHERE owner=? AND state!='hidden' ORDER BY created DESC",(owner,))


def task_board(db,owner,compact=False):
    tasks=task_rows(db,owner)
    counts={s:sum(t["status"]==s for t in tasks) for s in VISIBLE}
    a,b=st.columns([3,1],vertical_alignment="center")
    a.markdown("### 오늘의 할 일" if compact else "### 해야 할 일")
    b.caption(f"전체 {len(tasks)}개 · 완료 {counts['완료']}개")
    if not compact:
        search=st.text_input("할 일 찾기",key="board_query",placeholder="과목이나 과제 이름 검색",label_visibility="collapsed")
        if search:
            tasks=[t for t in tasks if search.lower() in (t["title"]+" "+t["note"]).lower()]
    cols=st.columns(4,gap="small")
    for ci,status in enumerate(VISIBLE):
        with cols[ci]:
            st.markdown(f"<div class='lane'>{LABELS[status]} <span style='float:right;color:#73857e'>{counts[status]}</span></div>",
                        unsafe_allow_html=True)
            lane=[t for t in tasks if t["status"]==status]
            if not lane:
                st.caption("아직 없어요.")
            for t in lane:
                with st.container(border=True):
                    st.markdown("**"+html.escape(t["title"])+"**",unsafe_allow_html=True)
                    if t["day"]:
                        st.caption("🗓 "+t["day"])
                    if t["note"]:
                        with st.expander("내용 보기"):
                            st.write(t["note"])
                    bar=st.columns([1,1.1,1],gap="small")
                    if status!="시작 전" and bar[0].button("←",key="bprev_"+t["id"],
                                                        help="앞 상태로"):
                        change_task(db,owner,t["id"],VISIBLE[VISIBLE.index(status)-1])
                        st.rerun()
                    if status!="완료" and bar[1].button("→",key="bnext_"+t["id"],type="primary" if status=="진행 중" else "secondary",
                                                         help="다음 상태로"):
                        change_task(db,owner,t["id"],VISIBLE[VISIBLE.index(status)+1])
                        st.rerun()
                    with bar[2].popover("⋯",help="상태 변경과 숨기기"):
                        new_status=st.selectbox("상태 변경",VISIBLE,key="bstatus_"+t["id"],index=VISIBLE.index(status))
                        if st.button("변경 적용",key="bapply_"+t["id"]):
                            change_task(db,owner,t["id"],new_status)
                            st.rerun()
                        if st.button("숨기기",key="bhide_"+t["id"]):
                            change_task(db,owner,t["id"],"숨김")
                            st.rerun()
    with st.expander("＋ 할 일 추가",expanded=not bool(tasks)):
        with st.form("board_add",clear_on_submit=True):
            title=st.text_input("무엇을 할까요?",placeholder="예: 심리학 3장 기억 개념 비교하기")
            a,b=st.columns(2)
            day=a.text_input("언제까지? (선택)",placeholder="예: 2026-10-30")
            goal_list=active_goals(db,owner)
            names=["연결할 목표 없음"]+[g["title"] for g in goal_list]
            goal_choice=b.selectbox("연결할 목표 (선택)",names)
            note=st.text_input("메모 (선택)",placeholder="예: 비교표 작성 후 연습문제 2개")
            if st.form_submit_button("할 일 추가",type="primary"):
                if title.strip():
                    gid=goal_list[names.index(goal_choice)-1]["id"] if names.index(goal_choice)>0 else ""
                    add_task(db,owner,title,day,goal_id=gid,note=note)
                    st.rerun()
                else:
                    st.warning("할 일을 적어 주세요.")
    if not compact and tasks:
        with st.expander("⏱ 계획한 시간과 실제 시간을 비교하기 · 필요할 때만",expanded=False):
            st.caption("시간은 성실성이나 역량 점수가 아니에요. 스스로 적어 둔 계획과 실제 경험을 비교해요.")
            options={t["id"]:t["title"] for t in tasks}
            chosen_id=st.selectbox("비교할 할 일",list(options),
                                   format_func=lambda k:options[k],key="time_task")
            old=latest_time(db,owner,chosen_id)
            if old:
                first="미입력" if old["estimated"] is None else str(old["estimated"])+"분"
                second="미입력" if old["actual"] is None else str(old["actual"])+"분"
                st.caption(f"최근 기록 · 예상 {first} / 실제 {second}")
                if old["estimated"] is not None and old["actual"] is not None:
                    delta=old["actual"]-old["estimated"]
                    st.write("예상보다 "+(f"{delta}분 더 걸렸어요." if delta>0 else
                           (f"{abs(delta)}분 덜 걸렸어요." if delta<0 else "예상과 같았어요.")))
            with st.form("time_reflection",clear_on_submit=True):
                a,b,c=st.columns(3)
                estimated=a.text_input("예상(분)",placeholder="예: 30")
                actual=b.text_input("실제(분)",placeholder="예: 45")
                next_one=c.text_input("다음 예상(분)",placeholder="예: 40")
                reason=st.text_input("차이가 발생한 이유 또는 조정할 점 (선택)")
                submitted=st.form_submit_button("내 시간기록 저장")
                if submitted:
                    def to_min(v):
                        if not v.strip():
                            return None
                        if not v.strip().isdigit():
                            raise ValueError("시간은 숫자로 적어 주세요.")
                        return int(v.strip())
                    try:
                        save_time(db,owner,chosen_id,to_min(estimated),to_min(actual),
                                  reason,to_min(next_one))
                        st.success("내가 작성한 시간 비교를 저장했어요.")
                    except ValueError as e:
                        st.warning(str(e))
    hidden=all_rows(db,"SELECT id,title FROM compass_tasks WHERE owner=? AND status='숨김'",(owner,))
    if hidden:
        with st.expander(f"숨긴 할 일 {len(hidden)}개"):
            for t in hidden:
                a,b=st.columns([5,1])
                a.write(t["title"])
                if b.button("복원",key="restore_task_"+t["id"]):
                    change_task(db,owner,t["id"],"시작 전")
                    st.rerun()


def home_view(db,owner,client,model):
    goals=active_goals(db,owner)
    undone=[x for x in task_rows(db,owner) if x["status"]!="완료"]
    summary=(goals[0]["title"] if goals else "이번 공부의 목표를 직접 정해 볼까요?")
    st.markdown('<div class="hero"><div class="eyebrow">TODAY · 내 학습의 방향</div>'
                '<h2>오늘은 어디부터 해볼까요?</h2>'
                '<p>내가 정한 목표와 해야 할 일을 확인하고, 필요한 도움을 선택할 수 있어요.</p></div>',unsafe_allow_html=True)
    a,b,c=st.columns(3)
    a.metric("내 목표",f"{len(goals)}개")
    b.metric("남은 할 일",f"{len(undone)}개")
    c.metric("직접 학습한 활동",str(db.execute("SELECT COUNT(*) FROM demo_practice WHERE owner=?",(owner,)).fetchone()[0])+"번")
    with st.container(border=True):
        st.caption("가장 최근에 설정한 목표")
        st.markdown("**"+html.escape(summary)+"**",unsafe_allow_html=True)
        c1,c2,c3=st.columns(3)
        if c1.button("목표와 계획",use_container_width=True):
            _jump("목표와 계획")
        if c2.button("공부 시작",type="primary",use_container_width=True):
            _jump("공부하기")
        if c3.button("오늘 돌아보기",use_container_width=True):
            _jump("학습일지")
    from compass_home_keywords import render_home_difficulties
    render_home_difficulties(db,owner)
    from compass_major_links import home_exploration
    home_exploration(db,owner)
    task_board(db,owner,compact=True)
    n=db.execute("SELECT COUNT(*) FROM compass_marks WHERE owner=? AND state='active'",(owner,)).fetchone()[0]
    if n:
        st.caption(f"📎 내가 남긴 PDF 학습 표시 {n}개 · '내 기록'에서 필요한 부분만 펼쳐 볼 수 있어요.")
    # A concise learning trail, not an auto-scored student profile.
    from compass_journal import rows_for_diary
    diary=rows_for_diary(db,owner,limit=1)
    highlights=all_rows(db,"""SELECT kind,text,note FROM compass_marks
          WHERE owner=? AND state='active' AND kind IN ('흥미','어려움')
          ORDER BY created DESC LIMIT 2""",(owner,))
    if interest_for(db,owner):
        st.caption("🌿 내가 설정한 관심 분야: "+interest_for(db,owner))
    if diary or highlights:
        st.markdown("### 내가 남긴 학습의 흔적")
        left,right=st.columns(2,gap="medium")
        with left.container(border=True):
            st.markdown("**✍️ 최근 학습일지**")
            if diary:
                st.caption(diary[0]["created"][:16])
                st.write((diary[0]["briefing"] or diary[0]["original"])[:360])
            else:
                st.caption("기록된 학습일지가 아직 없어요.")
            if st.button("나의 학습일지 열기",key="home_open_diary"):
                _jump("학습일지")
        with right.container(border=True):
            st.markdown("**📌 내가 표시한 내용**")
            for marked in highlights:
                st.caption("● "+marked["kind"])
                st.write(marked["text"][:115]+("…" if len(marked["text"])>115 else ""))
            if st.button("표시한 문장 모아보기",key="home_open_marks"):
                _jump("내 기록")
    with st.expander("💬 지금 AI에게 물어보기 · 선택",expanded=False):
        st.caption("어려움을 말하면 AI가 내용 설명과 실제 예시를 제공해요. 목표나 계획을 자동 변경하지 않아요.")
        from compass_store import chat_messages,put_chat
        from compass_chat import answer
        from sdl_upgrade.model_client import safe_error_message
        past=chat_messages(db,owner,"오늘",limit=4)
        for h in past:
            with st.chat_message(h["role"]):
                st.write(h["text"])
        with st.form("home_chat_form",clear_on_submit=True):
            question=st.text_area("오늘 공부에 관해 궁금한 점",height=74,key="home_chat_question",
                placeholder="예: 어떻게 공부를 시작할지 모르겠어요.")
            sent=st.form_submit_button("AI에게 질문하기",type="primary")
        if sent and question.strip():
            if not client:
                st.error("실제 AI 연결이 설정되지 않았어요.")
            else:
                try:
                    reply=answer(client,model,"오늘의 학습","",question,past,interest=interest_for(db,owner))
                    put_chat(db,owner,"오늘","user",question)
                    put_chat(db,owner,"오늘","assistant",reply)
                    st.rerun()
                except Exception as e:
                    st.error("AI 연결 오류: "+safe_error_message(e))


def goal_view(db,owner,client,model):
    st.markdown("### 목표와 계획")
    st.caption("큰 방향과 이번에 해 볼 목표를 직접 정해요. 할 일 완료와 목표 도달 자기평가는 구분해요.")
    with st.expander("🌿 전공 및 진로 탐색 · 교과목 학습과 연결",expanded=True):
        current=interest_for(db,owner)
        st.caption("전공 추천이나 적합도 진단이 아니에요. 내가 선택한 관심 분야만 AI 설명의 맥락으로 활용해요.")
        with st.form("interest_form"):
            majors=st.text_input("관심 있는 전공이나 분야",value=current,placeholder="예: 심리학, 사회복지학 또는 아직 고민 중")
            if st.form_submit_button("내 관심 분야 저장"):
                save_interest(db,owner,majors)
                st.success("내가 입력한 관심 분야를 저장했어요.")
        goal_exploration(db,owner)
    st.caption("관심 전공 정보가 없어도 모든 기능을 이용할 수 있어요.")
    goals=active_goals(db,owner)
    if not goals:
        st.info("설정한 목표가 없어도 바로 학습을 시작할 수 있어요.")
    for goal in goals:
        with st.container(border=True):
            cs=st.columns([5,2,1.3],vertical_alignment="center")
            cs[0].markdown("**"+html.escape(goal["title"])+"**",unsafe_allow_html=True)
            cs[1].caption(("장기 목표: "+goal["parent"]) if goal["parent"] else "독립 목표")
            cs[1].caption("기간: "+(goal["period"] or "직접 정하기"))
            done=goal["state"]=="done"
            changed=cs[2].checkbox("완료 표시",value=done,key="goal_done_"+goal["id"],help="자기평가와 별개의 완료 체크")
            if changed!=done:
                db.execute("UPDATE demo_goals SET state=? WHERE owner=? AND id=?",
                           ("done" if changed else "active",owner,goal["id"]))
                st.rerun()
            linked=all_rows(db,"SELECT status FROM compass_tasks WHERE owner=? AND goal_id=? AND status!='숨김'",
                            (owner,goal["id"]))
            if linked:
                n=sum(x["status"]=="완료" for x in linked)
                st.caption(f"연결된 할 일 {n}/{len(linked)}개 완료 · 목표 달성률은 아니에요.")
            with st.expander("목표 수정 및 관리"):
                st.caption("내가 확인할 목표 도달 기준을 직접 적어 둘 수 있어요.")
                with st.form("edit_goal_"+goal["id"]):
                    title=st.text_input("목표",value=goal["title"])
                    parent=st.text_input("연결할 장기 목표 (선택)",value=goal["parent"])
                    period=st.text_input("기간",value=goal["period"])
                    criteria=st.text_area("스스로 확인할 목표 도달 기준 (선택)",value=criterion_for(db,owner,goal["id"]),height=80,
                       placeholder="예: 자료를 덮고 개념 두 가지의 차이를 말할 수 있다.")
                    if st.form_submit_button("변경 저장") and title.strip():
                        db.execute("UPDATE demo_goals SET title=?,parent=?,period=? WHERE id=? AND owner=?",
                                   (title.strip(),parent.strip(),period.strip(),goal["id"],owner))
                        save_criterion(db,owner,goal["id"],criteria)
                        st.rerun()
                if st.button("이 목표 숨기기",key="hide_goal_"+goal["id"]):
                    db.execute("UPDATE demo_goals SET state='hidden' WHERE id=? AND owner=?",(goal["id"],owner))
                    st.rerun()
            criterion=criterion_for(db,owner,goal["id"])
            if criterion:
                st.caption("내가 정한 확인 기준 · "+criterion[:200])
            with st.expander("돌아본 뒤 목표를 바꾸고 싶다면 · 선택",expanded=False):
                with st.form("revise_goal_"+goal["id"],clear_on_submit=True):
                    revision=st.text_input("새 목표",value=goal["title"])
                    why=st.text_area("목표를 바꾸려는 이유 (학생의 생각)",height=75,
                                     placeholder="예: 강의자료에서 아직 이해하지 못한 부분을 확인해서")
                    if st.form_submit_button("수정 이유와 함께 반영"):
                        try:
                            revise_goal(db,owner,goal["id"],revision,why)
                            st.success("내가 수정한 목표와 이유를 기록했어요.")
                            st.rerun()
                        except ValueError as e:
                            st.warning(str(e))
                history=adjustments(db,owner,goal["id"])[:2]
                for prev in history:
                    st.caption("이전 "+prev["before_text"]+" → 변경 "+prev["after_text"])
                    st.caption("내가 남긴 이유: "+prev["reason"])
    with st.expander("＋ 새로운 목표 추가",expanded=not bool(goals)):
        with st.form("add_goal",clear_on_submit=True):
            title=st.text_input("설정할 목표",placeholder="예: 기억의 원리를 내 말로 설명하기")
            a,b=st.columns(2)
            parent=a.text_input("장기 목표 (선택)",placeholder="예: 심리학과 관련된 관심 탐색")
            period=b.text_input("기간 (선택)",placeholder="예: 이번 주")
            criteria=st.text_input("목표 도달을 어떻게 확인할까요? (선택)",placeholder="예: 자료 없이 핵심개념 설명하기")
            if st.form_submit_button("내 목표에 추가",type="primary"):
                if title.strip():
                    gid=ident()
                    db.execute("INSERT INTO demo_goals VALUES(?,?,?,?,?,?,?)",
                               (gid,owner,title.strip(),parent.strip(),period.strip(),"active",now()))
                    if criteria.strip():
                        save_criterion(db,owner,gid,criteria)
                    st.rerun()
                else:
                    st.warning("목표를 적어 주세요.")
    hidden=all_rows(db,"SELECT * FROM demo_goals WHERE owner=? AND state='hidden'",(owner,))
    if hidden:
        with st.expander(f"숨긴 목표 {len(hidden)}개"):
            for g in hidden:
                a,b=st.columns([5,1])
                a.write(g["title"])
                if b.button("복원",key="restore_goal_"+g["id"]):
                    db.execute("UPDATE demo_goals SET state='active' WHERE id=? AND owner=?",(g["id"],owner))
                    st.rerun()
    st.divider()
    task_board(db,owner)
