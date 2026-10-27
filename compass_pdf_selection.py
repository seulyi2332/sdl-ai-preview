"""Continuous scroll selectable PDF, student-triggered drag and mark.

Images retain the original page layout; a transparent text layer supports
mouse text selection. All user/PDF text is passed as component data, never HTML.
"""
import base64
import hashlib
import fitz
import streamlit as st


@st.cache_data(show_spinner=False,max_entries=5)
def pdf_layers(raw):
    doc=fitz.open(stream=raw,filetype="pdf")
    if len(doc)>35:
        doc.close()
        raise ValueError("시연 앱은 최대 35쪽까지 지원해요.")
    result=[]
    for p in range(len(doc)):
        page=doc[p]
        width=float(page.rect.width)
        height=float(page.rect.height)
        if not width or not height:
            continue
        scale=min(1.55,820.0/width)
        pix=page.get_pixmap(matrix=fitz.Matrix(scale,scale),alpha=False)
        image=base64.b64encode(pix.tobytes("png")).decode("ascii")
        spans=[]
        docdict=page.get_text("dict",sort=True)
        for block in docdict.get("blocks",[]):
            if block.get("type")!=0: continue
            for line in block.get("lines",[]):
                for span in line.get("spans",[]):
                    fragment=span.get("text","")
                    x0,y0,x1,y1=span.get("bbox",(0,0,0,0))
                    if fragment.strip():
                        spans.append({
                          "text":fragment,"x":round(x0/width*100,4),
                          "y":round(y0/height*100,4),
                          "size":round(float(span.get("size",10))/width*100,4)
                        })
                    if len(spans)>=1100:break
                if len(spans)>=1100:break
            if len(spans)>=1100:break
        result.append({"page":p+1,"width":width,"height":height,
                       "image":"data:image/png;base64,"+image,"spans":spans})
    doc.close()
    return result


HTML="""<div class="pdf-selection-root">
  <div class="pdf-reader-head"><b>PDF 연속 읽기</b>
    <span>글자를 드래그하면 바로 색상 선택 메뉴가 열려요</span></div>
  <div class="pdf-mark-bar" hidden aria-live="polite">
    <div class="pdf-mark-bar-title">어떤 내용으로 표시할까요?</div>
    <span class="pdf-selected-quote"></span>
    <div class="pdf-mark-actions"></div>
    <button type="button" class="pdf-cancel">취소</button>
  </div>
  <div class="pdf-selection-fallback"><span class="pdf-selection-status" aria-live="polite">글자를 드래그하면 선택 메뉴가 나타나요.</span>
    <button type="button" class="pdf-retry-selection">선택한 글 표시하기</button></div>
  <div class="pdf-reader-viewport" tabindex="0" aria-label="PDF 연속 스크롤 및 형광펜 뷰어"></div>
  <div class="pdf-color-legend">
    <span style="background:#ffd1d4">어려움</span>
    <span style="background:#cfe3ff">흥미</span>
    <span style="background:#ffefab">핵심</span>
    <span style="background:#c8f0d9">질문</span>
  </div>
  <div class="pdf-reader-foot">표시는 선택한 구절에 색으로 남고 ‘내 기록’에 저장돼요. 글자 선택이 어려우면 아래 문단 선택을 이용해요.</div>
</div>"""

CSS="""
.pdf-selection-root{position:relative;font-family:system-ui,'Apple SD Gothic Neo',sans-serif;color:#203c37;}
.pdf-reader-head{display:flex;gap:10px;align-items:center;justify-content:space-between;padding:10px 12px;
 background:#e8f4ed;border-radius:12px 12px 0 0;font-size:13px;flex-wrap:wrap;}
.pdf-reader-head span{font-size:12px;color:#506963}
.pdf-reader-viewport{height:68vh;min-height:430px;overflow-y:auto;background:#e2e9e5;padding:14px 9px;
 border:1px solid #cddad4;overscroll-behavior:contain;touch-action:pan-y;}
.pdf-page{max-width:840px;min-width:240px;width:100%;position:relative;margin:0 auto 15px;
 box-shadow:0 4px 14px #1d39331b;background:white;container-type:inline-size;}
.pdf-page img{display:block;width:100%;height:auto;pointer-events:none;user-select:none;-webkit-user-drag:none;}
.pdf-page-num{position:absolute;bottom:2px;right:7px;font-size:11px;color:#657875;
 background:#ffffffd9;padding:2px 5px;border-radius:4px;z-index:5;pointer-events:none;}
.pdf-highlight-layer{position:absolute;inset:0;z-index:1;pointer-events:none;mix-blend-mode:multiply;overflow:hidden;}
.pdf-highlight-patch{position:absolute;border-radius:2px;opacity:.67;pointer-events:none;}
.pdf-text-layer{position:absolute;inset:0;z-index:2;overflow:hidden;user-select:text;-webkit-user-select:text;}
.pdf-text-span{position:absolute;white-space:pre;user-select:text;-webkit-user-select:text;
 font-family:Arial,sans-serif;line-height:1.1;color:transparent;cursor:text;transform-origin:top left;}
.pdf-text-span::selection{background:rgba(36,164,111,.40);color:transparent;}
.pdf-mark-bar{position:relative;z-index:30;display:flex;flex-direction:column;gap:7px;
 width:100%;box-sizing:border-box;padding:11px 12px;
 border:1px solid #d5e0d9;border-radius:13px;background:#fff;
 box-shadow:0 10px 28px rgba(21,48,43,.27);}
.pdf-mark-bar[hidden]{display:none!important;}
.pdf-selection-fallback{display:flex;align-items:center;justify-content:space-between;gap:12px;
 padding:8px 10px;background:#f6faf6;border:1px solid #cddad4;border-top:0;font-size:12px;
 color:#4c685f;flex-wrap:wrap;}
.pdf-retry-selection{background:#155d56;color:#fff;border-radius:10px;border:0;
 font-size:12px;padding:8px 12px;min-height:35px;cursor:pointer;font-weight:750;}
.pdf-mark-bar-title{font-size:12px;color:#566e66;font-weight:700;}
.pdf-selected-quote{font-size:12px;color:#405852;line-height:1.5;display:-webkit-box;
 -webkit-box-orient:vertical;-webkit-line-clamp:2;overflow:hidden;overflow-wrap:anywhere;}
.pdf-mark-actions{display:flex;gap:5px;flex-wrap:wrap;align-items:center;}
.pdf-mark-actions button{border-radius:999px;border:1px solid transparent;padding:8px 11px;
 font-weight:750;font-size:12px;cursor:pointer;color:#2e4541;min-height:36px;}
.pdf-mark-actions button:hover{filter:brightness(.95);transform:translateY(-1px);}
.pdf-mark-actions button:focus-visible{outline:3px solid #165e55;outline-offset:2px;}
.pdf-cancel{border:0;padding:6px 8px;font-size:12px;color:#54766d;background:transparent;
 cursor:pointer;align-self:flex-end;}
.pdf-reader-foot{font-size:11px;color:#63766f;margin-top:6px}
.pdf-color-legend{display:flex;gap:6px;flex-wrap:wrap;align-items:center;font-size:11px;margin-top:5px;}
.pdf-color-legend span{padding:3px 9px;border-radius:8px;font-weight:700;color:#33403d;}
"""

JS=r"""
export default function ({parentElement,data,setTriggerValue}) {
  const root=parentElement.querySelector(".pdf-selection-root");
  const viewport=root?.querySelector(".pdf-reader-viewport");
  const toolbar=root?.querySelector(".pdf-mark-bar");
  const quote=root?.querySelector(".pdf-selected-quote");
  const actions=root?.querySelector(".pdf-mark-actions");
  const cancel=root?.querySelector(".pdf-cancel");
  const retry=root?.querySelector(".pdf-retry-selection");
  const status=root?.querySelector(".pdf-selection-status");
  if(!root || !viewport || !toolbar || !data) return;

  const palette={
    "어려움":{fill:"#ff9fa5",button:"#ffd1d4",border:"#db8890"},
    "흥미":{fill:"#9ac6ff",button:"#cfe3ff",border:"#8dafde"},
    "핵심":{fill:"#ffe478",button:"#ffefab",border:"#e0c556"},
    "질문":{fill:"#9be4bc",button:"#c8f0d9",border:"#84cda3"}
  };
  const documentId=data.material_id;
  const pages=Array.isArray(data.pages)?data.pages:[];
  const marks=Array.isArray(data.marks)?data.marks.slice():[];
  let selected=null;
  let dragStart=null;
  let dragEnd=null;
  let lastPointerPage=null;
  const sameDocument=viewport.dataset.documentId===documentId;
  const previousScroll=sameDocument?viewport.scrollTop:null;

  viewport.replaceChildren();
  viewport.dataset.documentId=documentId;
  for(const pg of pages) {
    const wrapper=document.createElement("div");
    wrapper.className="pdf-page";
    wrapper.dataset.page=String(pg.page);
    wrapper.style.aspectRatio=pg.width+" / "+pg.height;
    const img=document.createElement("img");
    img.src=pg.image;
    img.alt="PDF "+pg.page+"쪽";
    img.loading=pg.page>4?"lazy":"eager";
    img.draggable=false;
    const ink=document.createElement("div");
    ink.className="pdf-highlight-layer";
    const layer=document.createElement("div");
    layer.className="pdf-text-layer";
    for(const span of (pg.spans||[])) {
      const el=document.createElement("span");
      el.className="pdf-text-span";
      el.style.left=span.x+"%";
      el.style.top=span.y+"%";
      el.style.fontSize=span.size+"cqw";
      el.textContent=span.text+" ";
      layer.appendChild(el);
    }
    const badge=document.createElement("span");
    badge.className="pdf-page-num";
    badge.textContent=pg.page+" / "+pages.length+"쪽";
    wrapper.append(img,ink,layer,badge);
    viewport.appendChild(wrapper);
  }
  if(previousScroll!==null) viewport.scrollTop=previousScroll;
  else if(Number.isFinite(data.scroll) && data.scroll>=0) viewport.scrollTop=data.scroll;

  function currentSelection() {
    // Text selection can be attached to either the component shadow root
    // or the document; prefer a selection containing readable text.
    const tree=root.getRootNode();
    const candidates=[];
    try {if(tree && typeof tree.getSelection==="function") candidates.push(tree.getSelection());} catch(e) {}
    try {candidates.push(window.getSelection());} catch(e) {}
    try {candidates.push(document.getSelection());} catch(e) {}
    return candidates.find(s=>s && !s.isCollapsed && s.toString().trim())||null;
  }
  function caretAt(event) {
    const doc=root.ownerDocument;
    const tree=root.getRootNode();
    try {
      const options=tree!==doc ? {shadowRoots:[tree]} : {};
      const pos=doc.caretPositionFromPoint?.(event.clientX,event.clientY,options);
      if(pos?.offsetNode) return {node:pos.offsetNode,offset:pos.offset};
    } catch(e) {}
    try {
      const range=doc.caretRangeFromPoint?.(event.clientX,event.clientY);
      if(range) return {node:range.startContainer,offset:range.startOffset};
    } catch(e) {}
    return null;
  }
  function rangeFromDrag(start,end) {
    if(!start?.node || !end?.node) return null;
    try {
      const r=document.createRange();
      r.setStart(start.node,start.offset);
      const point=r.comparePoint(end.node,end.offset);
      if(point<0) {
        r.setStart(end.node,end.offset);
        r.setEnd(start.node,start.offset);
      } else {
        r.setEnd(end.node,end.offset);
      }
      return r.toString().trim()?r:null;
    } catch(e) {return null;}
  }
  function clearSelection() {
    selected=null;
    toolbar.hidden=true;
    const s=currentSelection();
    if(s) s.removeAllRanges();
    dragStart=null;
    dragEnd=null;
  }
  function closestPage(node) {
    const el=node?.nodeType===1?node:node?.parentElement;
    return el?.closest?.(".pdf-page")||null;
  }
  function clamp(number,low,high) {return Math.max(low,Math.min(number,high));}
  function addRect(ink,rect,fill) {
    if(!rect||typeof rect!=="object")return;
    const values=["x","y","w","h"].map(k=>Number(rect[k]));
    if(values.some(v=>!Number.isFinite(v)))return;
    const [x,y,w,h]=values;
    if(x<0||y<0||w<=0||h<=0||x+w>100.6||y+h>100.6)return;
    const patch=document.createElement("div");
    patch.className="pdf-highlight-patch";
    patch.style.left=x+"%";patch.style.top=y+"%";
    patch.style.width=w+"%";patch.style.height=h+"%";
    patch.style.background=fill;
    ink.appendChild(patch);
  }
  function drawMarks() {
    for(const page of viewport.querySelectorAll(".pdf-page")) {
      const ink=page.querySelector(".pdf-highlight-layer");
      ink.replaceChildren();
      const pageNum=Number(page.dataset.page);
      const pageMarks=marks.filter(m=>Number(m.page)===pageNum && palette[m.kind]);
      for(const mark of pageMarks) {
        const fill=palette[mark.kind].fill;
        const rects=Array.isArray(mark.rects)?mark.rects:[];
        if(rects.length) {
          for(const rect of rects) addRect(ink,rect,fill);
        } else {
          // Older PDF marks used only text. Retain their visible tint without
          // claiming exact coordinates for previously stored selections.
          const normalized=String(mark.text||"").replace(/\s+/g,"");
          if(!normalized)continue;
          for(const span of page.querySelectorAll(".pdf-text-span")) {
            const term=(span.textContent||"").trim().replace(/\s+/g,"");
            if(term.length>=4 && normalized.includes(term)) {
              span.style.background=fill;
              span.style.opacity=".52";
            }
          }
        }
      }
    }
  }
  drawMarks();

  // Measure only selected text rectangles, relative to the original PDF page.
  function selectionRects(range,page) {
    const bounds=page.getBoundingClientRect();
    if(!bounds.width||!bounds.height) return [];
    const rects=[];
    for(const rectangle of Array.from(range.getClientRects()).slice(0,85)) {
      const x=clamp(rectangle.left-bounds.left,0,bounds.width);
      const y=clamp(rectangle.top-bounds.top,0,bounds.height);
      const w=clamp(rectangle.right-bounds.left,0,bounds.width)-x;
      const h=clamp(rectangle.bottom-bounds.top,0,bounds.height)-y;
      if(w<1.5||h<2)continue;
      rects.push({x:+(x/bounds.width*100).toFixed(3),
                  y:+(y/bounds.height*100).toFixed(3),
                  w:+(w/bounds.width*100).toFixed(3),
                  h:+(h/bounds.height*100).toFixed(3)});
    }
    return rects;
  }

  function showBar() {
    const selection=currentSelection();
    let range=selection?.rangeCount?selection.getRangeAt(0):null;
    let text=selection?selection.toString().trim().replace(/\s+/g," "):"";
    // Some browsers retarget shadow DOM selections to the host element.
    // Recover the exact selected range from the pointer endpoints if necessary.
    if(!text || !range || !viewport.contains(range.startContainer)) {
      const dragged=rangeFromDrag(dragStart,dragEnd);
      if(dragged && viewport.contains(dragged.startContainer)) {
        range=dragged;
        text=dragged.toString().trim().replace(/\s+/g," ");
      }
    }
    if(text.length<2 || text.length>1600) {
      if(status)status.textContent="선택한 문장을 읽지 못했어요. 다시 드래그하거나 아래 문단 목록을 이용해 주세요.";
      return;
    }
    // A text range selected inside Streamlit's component shadow root
    // can be retargeted to the host. Recover the page by its viewport box.
    const r=range?range.getBoundingClientRect():null;
    let page=range?closestPage(range.startContainer):null;
    if(!page && r) {
      page=Array.from(viewport.querySelectorAll(".pdf-page")).find(el=>{
        const box=el.getBoundingClientRect();
        return r.top<box.bottom && r.bottom>box.top &&
               r.right>box.left && r.left<box.right;
      })||null;
    }
    if(!page && lastPointerPage && viewport.contains(lastPointerPage)) page=lastPointerPage;
    if(!page||!viewport.contains(page)) {
      if(status)status.textContent="선택한 쪽을 확인하지 못했어요. 한 쪽 안에서 다시 드래그해 주세요.";
      return;
    }
    const last=range?closestPage(range.endContainer):null;
    if(last && last!==page)return; // Cross-page selections are not saved.
    let rects=range?selectionRects(range,page):[];
    if(!rects.length && r && r.width>1 && r.height>1) {
      const bounds=page.getBoundingClientRect();
      const x=clamp(r.left-bounds.left,0,bounds.width);
      const y=clamp(r.top-bounds.top,0,bounds.height);
      rects=[{x:+(x/bounds.width*100).toFixed(3),y:+(y/bounds.height*100).toFixed(3),
        w:+(clamp(r.right-bounds.left,0,bounds.width)-x)/bounds.width*100,
        h:+(clamp(r.bottom-bounds.top,0,bounds.height)-y)/bounds.height*100}];
    }
    selected={text,page:Number(page.dataset.page),doc:documentId,rects};
    quote.textContent="선택한 글: "+text.slice(0,160)+(text.length>160?"…":"");
    toolbar.hidden=false;
    if(status) status.textContent="선택한 글 "+text.length+"자 · 위에서 표시 유형을 선택하세요.";
    // Keep the toolbar above the inner PDF scroller so it cannot be clipped
    // by Streamlit's expander or appear outside the visible reader area.
  }
  let selectionTimer=null;
  const pointerPage=event=>{
    const path=typeof event.composedPath==="function"?event.composedPath():[];
    return path.find(n=>n?.classList?.contains?.("pdf-page"))||
           event.target?.closest?.(".pdf-page")||null;
  };
  const onPointerDown=event=>{
    dragStart=caretAt(event);
    dragEnd=null;
    lastPointerPage=pointerPage(event);
  };
  const onMouseUp=event=>{
    dragEnd=caretAt(event);
    lastPointerPage=pointerPage(event)||lastPointerPage;
    setTimeout(showBar,45);
  };
  const onTouchEnd=event=>{
    lastPointerPage=pointerPage(event)||lastPointerPage;
    setTimeout(showBar,350);
  };
  const onSelectionChange=()=>{
    if(selectionTimer!==null)clearTimeout(selectionTimer);
    selectionTimer=setTimeout(showBar,450);
  };
  viewport.addEventListener("pointerdown",onPointerDown);
  viewport.addEventListener("mouseup",onMouseUp);
  viewport.addEventListener("pointerup",onMouseUp);
  viewport.addEventListener("touchend",onTouchEnd);
  document.addEventListener("selectionchange",onSelectionChange);
  const rootNode=root.getRootNode();
  if(rootNode!==document) rootNode.addEventListener("selectionchange",onSelectionChange);
  if(retry) {
    retry.onpointerdown=e=>e.preventDefault();
    retry.onmousedown=e=>e.preventDefault();
    retry.onclick=showBar;
  }
  toolbar.addEventListener("mousedown",e=>e.preventDefault());
  actions.replaceChildren();

  for(const kind of Object.keys(palette)) {
    const btn=document.createElement("button");
    const c=palette[kind];
    btn.type="button";
    btn.textContent=kind;
    btn.style.background=c.button;
    btn.style.borderColor=c.border;
    btn.setAttribute("aria-label","선택한 글을 "+kind+" 색으로 표시");
    btn.onmousedown=e=>e.preventDefault();
    btn.onclick=()=>{
      if(!selected || selected.doc!==documentId)return;
      const item={page:selected.page,text:selected.text,kind,rects:selected.rects};
      marks.push(item);
      drawMarks(); // Color appears immediately, before the app saves the record.
      const eventId=(typeof crypto!=="undefined" && crypto.randomUUID)?
          crypto.randomUUID():String(Date.now())+Math.random();
      setTriggerValue("marked",{
        event_id:eventId,material_id:documentId,page:selected.page,
        text:selected.text,kind,rects:selected.rects,scroll:viewport.scrollTop
      });
      clearSelection();
    };
    actions.appendChild(btn);
  }
  cancel.onclick=clearSelection;
  const onScroll=()=>{if(!toolbar.hidden)toolbar.hidden=true;};
  viewport.addEventListener("scroll",onScroll,{passive:true});
  return ()=>{
    viewport.removeEventListener("pointerdown",onPointerDown);
    viewport.removeEventListener("mouseup",onMouseUp);
    viewport.removeEventListener("pointerup",onMouseUp);
    viewport.removeEventListener("touchend",onTouchEnd);
    document.removeEventListener("selectionchange",onSelectionChange);
    if(rootNode!==document)rootNode.removeEventListener("selectionchange",onSelectionChange);
    if(retry)retry.onclick=null;
    if(selectionTimer!==null)clearTimeout(selectionTimer);
    viewport.removeEventListener("scroll",onScroll);
  };
}
"""
def component_available():
    try:
        return hasattr(st.components,"v2") and hasattr(st.components.v2,"component")
    except AttributeError:
        return False


@st.cache_resource(show_spinner=False)
def _reader_component():
    return st.components.v2.component("compass_selectable_pdf",html=HTML,css=CSS,js=JS)


def show_pdf_reader(raw,material_id,saved_marks,scroll=0,key="compass_pdf_reader"):
    if not component_available():
        return None
    reader=_reader_component()
    pages=pdf_layers(raw)
    result=reader(data={
        "material_id":material_id,"pages":pages,
        "marks":saved_marks,"scroll":scroll,
    },on_marked_change=lambda:None,key=key)
    return result.marked


def selection_key(page,selected_text):
    normalized=" ".join(selected_text.split())
    return "drag-"+str(page)+"-"+hashlib.sha256(normalized.encode("utf8")).hexdigest()[:18]



def readable_ratio(text):
    """Reuse the PDF legibility check validated in the older Claude prototype.

    A damaged embedded font can yield nonsense even when a text selection exists.
    The check only decides whether the selected quotation is trustworthy.
    """
    import re
    if not text:
        return 0.0
    allowed=len(re.findall(
        r"""[가-힣ㄱ-ㅎㅏ-ㅣa-zA-Z0-9\s.,;:!?()\[\]{}'"“”‘’·\-–—~%/+=<>*&#@^_|°×÷…→←↑↓①-⑳ⅠⅡⅢ•▪●■□○◦]""",text))
    return allowed/len(text)
