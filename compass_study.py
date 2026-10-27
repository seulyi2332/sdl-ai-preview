"""PDF reading, passage marking, context strategies, direct practice and AI study chat."""
import json
import html
import streamlit as st
from compass_pdf import extract_pdf,render_page
from compass_pdf_selection import show_pdf_reader,selection_key,component_available
from compass_store import (all_rows,material_rows,get_material,add_material,interest_for,
                           put_mark,put_chat,chat_messages,ident,now)
from sdl_upgrade.strategies import StudyContext,recommend
from sdl_upgrade.ai import suggest_strategies
from sdl_upgrade.model_client import safe_error_message
from compass_chat import answer
from compass_feedback import make_feedback

KIND_TIP={"어려움":"이해가 어렵거나 다시 보고 싶은 문장",
          "흥미":"관심이 가거나 더 알고 싶은 내용",
          "핵심":"학습의 핵심이라고 내가 고른 내용",
          "질문":"나중에 확인하거나 질문하고 싶은 내용"}


def pdf_study(db,owner):
    """Upload -> read actual PDF page image -> mark chosen extracted paragraph."""
    st.markdown("### 강의자료에서 공부하기")
    st.caption("PDF를 읽고 내가 어렵거나 흥미롭게 느낀 문장을 표시할 수 있어요. AI가 자동으로 흥미를 판정하지 않아요.")
    uploaded=st.file_uploader("PDF 업로드",type=["pdf"],key="study_upload")
    if uploaded and st.button("이 자료를 내 자료함에 저장",key="study_upload_save"):
        try:
            data=uploaded.getvalue()
            paragraphs,pages=extract_pdf(data)
            title=uploaded.name[:150]
            mid=add_material(db,owner,title,data,paragraphs,pages)
            st.session_state["_study_pdf_next"]=mid
            st.success("PDF를 저장했어요. 다음 화면에서 이 자료를 볼 수 있어요.")
            st.rerun()
        except Exception as e:
            st.error(str(e) if isinstance(e,ValueError) else "PDF를 열 수 없어요. 다른 파일을 사용해 주세요.")
    docs=material_rows(db,owner)
    if not docs:
        st.info("PDF가 없어도 아래에서 교과목과 고민을 적고 학습전략 및 AI 도움을 받을 수 있어요.")
        return ""
    ids=[d["id"] for d in docs]
    if st.session_state.get("_study_pdf_next") in ids:
        st.session_state["study_pdf_selection"]=st.session_state.pop("_study_pdf_next")
    chosen=st.selectbox("내 학습자료",ids,format_func=lambda mid:next(d["title"] for d in docs if d["id"]==mid),
                        key="study_pdf_selection")
    material=get_material(db,owner,chosen)
    paragraphs=json.loads(material["paragraphs"])
    pages=int(material["page_count"])
    st.caption(f"총 {pages}쪽 · 읽을 수 있는 문단 {len(paragraphs)}개")
    if not paragraphs:
        st.warning("텍스트를 추출하지 못한 PDF예요. 스캔한 이미지 PDF일 수 있어요. 화면에서 읽을 수 있지만 AI에 자료 내용이 자동 전달되지는 않아요.")
    st.caption("원본 PDF를 아래로 스크롤하며 본문의 글을 드래그해서 표시할 수 있어요.")
    saved=db.execute("""SELECT * FROM compass_marks
        WHERE owner=? AND material_id=? AND state='active'
        ORDER BY created DESC""",(owner,chosen)).fetchall()
    saved_overlay=[]
    for m in saved:
        token=str(m["paragraph_id"])
        try:
            page=int(token.split("-")[1]) if token.startswith("drag-") else int(token.split("-")[0].lstrip("p"))
        except (ValueError,IndexError):
            page=0
        saved_overlay.append({"page":page,"text":m["text"]})
    if not component_available():
        st.warning("현재 Streamlit 버전에서는 PDF 드래그 구성요소를 사용할 수 없어 문단 선택을 제공해요.")
    else:
        try:
            selection=show_pdf_reader(
                 material["pdf"],chosen,saved_overlay,
                 scroll=st.session_state.get("study_pdf_scroll",0),
                 key="study_selectable_pdf")
            if isinstance(selection,dict) and selection.get("material_id")==chosen:
                event=str(selection.get("event_id") or "")
                excerpt=str(selection.get("text") or "").strip()
                kind=str(selection.get("kind") or "")
                pg=int(selection.get("page") or 0)
                if (event and event!=st.session_state.get("study_pdf_last_event")
                    and 1<=pg<=pages and len(excerpt)>=2 and len(excerpt)<=2500
                    and kind in KIND_TIP):
                    # Existing records remain available in '내 기록'.
                    put_mark(db,owner,chosen,selection_key(pg,excerpt),kind,excerpt)
                    st.session_state["study_pdf_last_event"]=event
                    st.session_state["study_pdf_scroll"]=max(0,float(selection.get("scroll") or 0))
                    st.session_state["study_chat_excerpt"]=excerpt
                    if kind=="어려움":
                        st.session_state["study_difficulty"]="내가 어렵다고 표시한 글: "+excerpt[:350]
                    if kind=="흥미":
                        st.session_state["study_chat_question"]="내가 흥미를 표시한 이 내용을 교과목과 관심 전공에 연결해서 설명해 주세요."
                    st.success("내가 드래그한 글을 '"+kind+"'로 저장했어요. '내 기록'에서 다시 볼 수 있어요.")
        except Exception as e:
            st.warning("연속 PDF 화면을 열지 못했어요. 아래 문단 선택 방식으로 계속할 수 있어요.")
            st.caption(type(e).__name__)

    with st.expander("문단 목록에서 선택해서 표시하기 · 대체 방법",expanded=not component_available()):
        page_no=st.number_input("보고 싶은 쪽",min_value=1,max_value=max(pages,1),
                                value=1,step=1,key="study_pdf_page")
        selected_page=[p for p in paragraphs if p["page"]==page_no]
        if not selected_page:
            st.caption("이 쪽은 텍스트가 추출되지 않았어요. 이미지 PDF라면 드래그를 지원하지 않을 수 있어요.")
        else:
            options=[p["id"] for p in selected_page]
            selected=st.selectbox("문단",options,key="study_para",
                                  format_func=lambda pid:next(p["text"][:90] for p in selected_page if p["id"]==pid))
            paragraph=next(p for p in selected_page if p["id"]==selected)
            st.markdown("> "+paragraph["text"][:1600].replace("\n","\n> "))
            kind=st.radio("어떻게 표시할까요?",list(KIND_TIP),key="study_mark_kind",
                          horizontal=True)
            note=st.text_input("메모 (선택)",key="study_mark_note")
            if st.button("선택한 문단 표시 저장",key="study_mark_save",type="primary"):
                put_mark(db,owner,chosen,selected,kind,paragraph["text"],note)
                st.session_state["study_chat_excerpt"]=paragraph["text"]
                st.success("내가 선택한 문단을 '"+kind+"'로 저장했어요.")
            if st.button("이 문단을 AI와 공부하기",key="study_to_chat"):
                st.session_state["study_chat_excerpt"]=paragraph["text"]
                if kind=="어려움":
                    st.session_state["study_difficulty"]="PDF에서 선택한 이 문단을 이해하고 싶어요: "+paragraph["text"][:320]
                    st.session_state["study_chat_question"]="이 문단이 어려워요. 핵심을 쉽게 설명하고 구체적인 예시를 들어 주세요."
                elif kind=="흥미":
                    st.session_state["study_chat_question"]="이 문단이 흥미로워요. 실제 적용 사례와 관심 전공에서의 연결을 설명해 주세요."
                else:
                    st.session_state["study_chat_question"]="제가 선택한 문단을 내 말로 설명할 수 있게 사례를 보여 주세요."
                st.success("선택한 문단을 공부 방법과 AI 대화에 연결했어요.")
    return st.session_state.get("study_chat_excerpt") or ""


def strategy_and_practice(db,owner,client,model,course,topic,excerpt):
    st.markdown("### 내 상황에 맞는 공부 방법")
    st.caption("24가지 방법을 모두 보여주지 않고, 교과목 및 어려움에 맞는 방법 2~3개를 제안해요.")
    if st.session_state.get("study_chat_excerpt"):
        with st.expander("📌 내가 선택한 PDF 학습내용 · 참고",expanded=False):
            st.write(st.session_state["study_chat_excerpt"][:1200])
    difficulty=st.text_area("지금 공부하면서 막히는 점",key="study_difficulty",height=86,
                             placeholder="예: 심리학 이론이 비슷해서 구분하기 어려워요.")
    task=st.text_input("어떤 활동을 해 보고 싶나요? (선택)",key="study_task",
                        placeholder="예: 개념 차이 비교, 예제 풀이, 암기 후 점검")
    chosen_excerpt=st.session_state.get("study_chat_excerpt") or excerpt
    ctx=StudyContext(course=course,topic=topic,difficulty=difficulty,
                     task=task,material_excerpt=chosen_excerpt[:1800])
    snapshot=(owner,course,topic,difficulty,task,chosen_excerpt[:500])
    if st.session_state.get("study_strategy_ctx")!=snapshot:
        st.session_state["study_strategy_ctx"]=snapshot
        st.session_state.pop("study_strategies",None)
        st.session_state.pop("study_strategy_selected",None)
    if st.button("내 공부 방법 추천받기",type="primary",key="study_recommend"):
        if client:
            try:
                with st.spinner("학습 내용과 어려움에 맞는 방법을 찾고 있어요"):
                    results=suggest_strategies(ctx,client,model)
                st.session_state["study_strategies"]=results
                st.session_state["study_strategy_info"]="실제 AI가 방법을 구성했어요."
            except Exception as exc:
                st.session_state["study_strategies"]=recommend(ctx)
                st.session_state["study_strategy_info"]="AI 응답 실패 · 학습전략 카탈로그 안내 ("+safe_error_message(exc)+")"
        else:
            st.session_state["study_strategies"]=recommend(ctx)
            st.session_state["study_strategy_info"]="카탈로그 기반 안내 · 실제 AI 응답이 아니에요."
    cards=st.session_state.get("study_strategies") or []
    if not cards:
        return
    st.caption(st.session_state.get("study_strategy_info",""))
    cols=st.columns(len(cards),gap="small")
    for i,card in enumerate(cards):
        with cols[i].container(border=True):
            st.markdown("#### "+card["name"])
            st.write(card["reason"])
            with st.expander("진행 방법"):
                for j,step in enumerate(card["steps"],1):
                    st.markdown(f"{j}. {step}")
            if st.button("이 방법 해보기",key="study_pick_"+card["id"],type="primary",use_container_width=True):
                st.session_state["study_strategy_selected"]=card["id"]
                st.rerun()
    chosen=next((c for c in cards if c["id"]==st.session_state.get("study_strategy_selected")),None)
    if not chosen:
        return
    with st.container(border=True):
        st.markdown("### 직접 해 보기 · "+chosen["name"])
        st.caption("내가 먼저 풀거나 설명한 뒤 원하는 경우 AI 피드백을 받을 수 있어요.")
        if chosen.get("task_prompt"):
            st.info(chosen["task_prompt"])
        else:
            st.caption("내가 내용을 작성하고 필요한 경우에만 예시를 펼쳐봐요.")
        with st.form("study_practice_form",clear_on_submit=True):
            if chosen["kind"]=="comparison":
                a,b=st.columns(2)
                ca=a.text_input("첫 개념 또는 사례",placeholder="예: 단기기억")
                cb=b.text_input("비교할 개념 또는 사례",placeholder="예: 장기기억")
                criteria=st.text_input("비교 기준",value="정의, 차이, 예시")
                a,b=st.columns(2)
                ta=a.text_area("첫 개념의 특징",height=120)
                tb=b.text_area("두 번째 개념의 특징",height=120)
                work={"left":ca,"right":cb,"criteria":criteria,"left_work":ta,"right_work":tb}
                attempt=bool(ta.strip() or tb.strip())
            elif chosen["kind"]=="solve":
                q=st.text_area("문제 및 조건",height=80)
                a=st.text_area("내 풀이 과정",height=140)
                work={"question":q,"answer":a}
                attempt=bool(a.strip())
            else:
                response=st.text_area("내가 직접 해 본 내용",height=180,
                                      placeholder="설명, 회상, 관점 비교, 학습계획 등의 내용을 적어 보세요.")
                work={"response":response}
                attempt=bool(response.strip())
            selfcheck=st.selectbox("내가 느낀 이해 정도 (선택)",[None,"아직 잘 모르겠어요",
                                       "조금 이해했어요","내 말로 설명할 수 있어요"],
                                   format_func=lambda x:x or "나중에 평가할래요")
            saved=st.form_submit_button("내 학습기록에 저장",type="primary")
        if saved:
            if attempt:
                activity_id=ident()
                saved_work={"work":work,"student_selfcheck":selfcheck,
                            "method_name":chosen["name"],"context_difficulty":difficulty}
                db.execute("INSERT INTO demo_practice VALUES(?,?,?,?,?,?,?)",
                           (activity_id,owner,course,topic,chosen["id"],
                            json.dumps(saved_work,ensure_ascii=False),now()))
                st.session_state["study_last_work"]={
                   "id":activity_id,"owner":owner,"course":course,"topic":topic,
                   "strategy":chosen["id"],"strategy_name":chosen["name"],
                   "work":work,"excerpt":(st.session_state.get("study_chat_excerpt") or excerpt)[:4800]}
                st.session_state.pop("study_last_feedback",None)
                st.success("내가 직접 수행한 내용을 저장했어요.")
            else:
                st.warning("실제 수행한 내용을 먼저 적어 주세요.")
        with st.expander("막혔을 때 도움과 예시 보기"):
            for i,step in enumerate(chosen["steps"],1):
                st.markdown(f"{i}. {step}")
            if chosen.get("example"):
                st.info(chosen["example"])
    activity=st.session_state.get("study_last_work") or {}
    if activity.get("owner")==owner and activity.get("strategy")==chosen["id"]:
        with st.container(border=True):
            st.markdown("#### 내가 직접 작성한 답에 대한 AI 도움 · 선택")
            st.caption("작성한 답을 토대로 구체적인 보완점과 근거를 설명해요. 자동 채점이나 목표 성취 판단은 하지 않아요.")
            last=db.execute("SELECT id FROM demo_practice WHERE owner=? AND id=?",
                            (owner,activity["id"])).fetchone()
            if last:
                help_level=st.selectbox("어떤 도움을 받고 싶나요? (선택)",
                     ["구체적으로 잘된 점과 보완점","정답을 바로 말하기보다 단서부터",
                      "필요한 개념과 예시 자세히"],key="study_feedback_mode")
                if st.button("내 답에 AI 피드백 받기",key="study_feedback_btn",type="primary"):
                    if not client:
                        st.warning("실제 AI 키가 연결되어 있지 않아요. 저장한 내 답은 그대로 남아 있어요.")
                    else:
                        try:
                            with st.spinner("내가 직접 작성한 답을 살펴보고 있어요"):
                                feedback=make_feedback(client,model,activity["course"],activity["topic"],
                                    activity["strategy_name"],activity["work"],activity["excerpt"],help_level)
                            db.execute("""CREATE TABLE IF NOT EXISTS compass_feedback_log(
                                 id TEXT PRIMARY KEY,owner TEXT NOT NULL,activity_id TEXT NOT NULL,
                                 feedback TEXT NOT NULL,help_mode TEXT NOT NULL,created TEXT NOT NULL)""")
                            db.execute("INSERT INTO compass_feedback_log VALUES(?,?,?,?,?,?)",
                                (ident(),owner,activity["id"],feedback,help_level,now()))
                            st.session_state["study_last_feedback"]=feedback
                        except Exception as e:
                            st.error("AI 피드백에 문제가 생겼어요. "+safe_error_message(e))
                feedback=st.session_state.get("study_last_feedback")
                if feedback:
                    st.success("AI가 학생의 수행 내용을 참고해 만든 피드백이에요.")
                    st.write(feedback)
                    st.caption("AI의 설명이 강의내용과 다른지 직접 확인하고, 다시 시도하거나 다른 방법을 선택할 수 있어요.")
    if st.button("다른 학습전략 고르기",key="study_pick_again"):
        st.session_state.pop("study_strategy_selected",None)
        st.rerun()


def conversation(db,owner,client,model,course,topic,excerpt):
    st.markdown("### 💬 AI와 공부하기")
    st.caption("질문을 자유롭게 해 주세요. AI는 설명과 선택지를 제공하고 목표 및 기록을 마음대로 바꾸지 않아요.")
    hist=chat_messages(db,owner,course,limit=10)
    for message in hist[-6:]:
        with st.chat_message(message["role"]):
            st.write(message["text"])
    if st.session_state.get("study_chat_excerpt"):
        st.caption("선택한 문단을 질문의 근거로 활용해요.")
        excerpt=st.session_state["study_chat_excerpt"]
    with st.form("study_chat_form",clear_on_submit=True):
        q=st.text_area("AI에게 물어보기",key="study_chat_question",height=80,
                       placeholder="예: 단기기억과 장기기억이 실제 공부할 때 어떻게 다른가요?")
        submit=st.form_submit_button("질문 보내기",type="primary")
    if submit:
        if not q.strip():
            st.warning("궁금한 점을 적어 주세요.")
        elif not client:
            st.error("OpenAI API 키가 설정되지 않아 실제 AI 대화는 사용할 수 없어요.")
        else:
            try:
                with st.spinner("질문에 맞게 설명하고 있어요"):
                    reply=answer(client,model,course,topic,q,hist,excerpt,interest=interest_for(db,owner))
                put_chat(db,owner,course,"user",q)
                put_chat(db,owner,course,"assistant",reply)
                st.rerun()
            except Exception as e:
                st.error("AI 응답 실패: "+safe_error_message(e))
                st.caption("질문 내용은 그대로 유지해 다시 시도할 수 있어요.")


def study_view(db,owner,client,model):
    st.markdown('<div class="hero"><div class="eyebrow">STUDY · 나에게 맞는 학습</div>'
                '<h2>읽고, 표시하고, 직접 해봐요</h2>'
                '<p>내 자료와 고민에 따라 필요한 도움을 선택할 수 있어요.</p></div>',unsafe_allow_html=True)
    a,b=st.columns(2)
    course=a.text_input("교과목",value="심리학개론",key="study_course",
                        placeholder="예: 심리학개론")
    topic=b.text_input("오늘 공부할 주제",key="study_topic",
                       placeholder="예: 기억과 학습")
    with st.expander("📚 내 학습자료 읽기, 연속 스크롤 및 드래그 표시",expanded=True):
        excerpt=pdf_study(db,owner)
    st.divider()
    strategy_and_practice(db,owner,client,model,course,topic,excerpt)
    st.divider()
    conversation(db,owner,client,model,course,topic,excerpt)
