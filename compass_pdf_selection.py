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
    <span>본문 드래그 → 어려움, 흥미, 핵심, 질문 표시</span></div>
  <div class="pdf-reader-viewport" tabindex="0" aria-label="PDF 연속 스크롤 뷰어"></div>
  <div class="pdf-mark-bar" hidden aria-live="polite">
    <span class="pdf-selected-quote"></span>
    <div class="pdf-mark-actions"></div>
    <button type="button" class="pdf-cancel">취소</button>
  </div>
  <div class="pdf-reader-foot">드래그가 어려우면 아래 문단 목록에서도 선택할 수 있어요.</div>
</div>"""

CSS="""
.pdf-selection-root{font-family:system-ui,'Apple SD Gothic Neo',sans-serif;color:#203c37;}
.pdf-reader-head{display:flex;gap:12px;align-items:center;justify-content:space-between;padding:9px 12px;
 background:#e8f4ed;border-radius:12px 12px 0 0;font-size:13px;}
.pdf-reader-head span{font-size:12px;color:#506963}
.pdf-reader-viewport{height:68vh;min-height:450px;overflow-y:auto;background:#e2e9e5;padding:14px 9px;
 border:1px solid #cddad4;overscroll-behavior:contain;touch-action:pan-y;}
.pdf-page{max-width:840px;min-width:240px;width:100%;position:relative;margin:0 auto 15px;
 box-shadow:0 4px 14px #1d39331b;background:white;container-type:inline-size;}
.pdf-page img{display:block;width:100%;height:auto;pointer-events:none;user-select:none;-webkit-user-drag:none;}
.pdf-page-num{position:absolute;bottom:2px;right:7px;font-size:11px;color:#657875;
 background:#ffffffd9;padding:2px 5px;border-radius:4px;z-index:2;pointer-events:none;}
.pdf-text-layer{position:absolute;inset:0;overflow:hidden;user-select:text;-webkit-user-select:text;}
.pdf-text-span{position:absolute;white-space:pre;user-select:text;-webkit-user-select:text;
 font-family:Arial,sans-serif;line-height:1.1;color:transparent;cursor:text;transform-origin:top left;}
.pdf-text-span::selection{background:rgba(36,164,111,.48);color:transparent;}
.pdf-text-span.saved{background:rgba(248,188,79,.36);border-radius:1px;}
.pdf-mark-bar{display:flex;flex-direction:column;gap:8px;padding:11px 13px;background:#f5faf5;
 border:1px solid #bdd3c7;border-radius:0 0 12px 12px;}
.pdf-mark-bar[hidden]{display:none!important;}
.pdf-selected-quote{display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:2;overflow:hidden;
 font-size:13px;line-height:1.45;}
.pdf-mark-actions{display:flex;gap:7px;flex-wrap:wrap;}
.pdf-mark-actions button,.pdf-cancel{border-radius:10px;border:1px solid #afc9bc;
 padding:7px 11px;font-weight:600;font-size:12px;background:white;color:#165449;cursor:pointer;}
.pdf-mark-actions button:hover{background:#dcefe4;}
.pdf-reader-foot{font-size:11px;color:#63766f;margin-top:5px}
"""

JS=r"""
export default function ({parentElement,data,setTriggerValue}) {
  const root=parentElement.querySelector(".pdf-selection-root");
  const viewport=root.querySelector(".pdf-reader-viewport");
  const toolbar=root.querySelector(".pdf-mark-bar");
  const quote=root.querySelector(".pdf-selected-quote");
  const actions=root.querySelector(".pdf-mark-actions");
  const cancel=root.querySelector(".pdf-cancel");
  if(!viewport || !data) return;
  const documentId=data.material_id;
  const selectedTypes=["어려움","흥미","핵심","질문"];
  let selected=null;
  const pages=Array.isArray(data.pages)?data.pages:[];
  const marked=Array.isArray(data.marks)?data.marks:[];

  // Replace children of this data placeholder only, never parentElement.innerHTML.
  viewport.replaceChildren();
  for(const pg of pages) {
    const wrapper=document.createElement("div");
    wrapper.className="pdf-page";
    wrapper.dataset.page=String(pg.page);
    const img=document.createElement("img");
    img.src=pg.image;
    img.alt="PDF "+pg.page+"쪽";
    img.loading=pg.page>4?"lazy":"eager";
    img.draggable=false;
    const layer=document.createElement("div");
    layer.className="pdf-text-layer";
    for(const span of (pg.spans||[])) {
      const el=document.createElement("span");
      el.className="pdf-text-span";
      el.style.left=span.x+"%";
      el.style.top=span.y+"%";
      el.style.fontSize=span.size+"cqw";
      el.textContent=span.text;
      el.appendChild(document.createTextNode(" "));
      const plain=span.text.trim();
      if(plain && marked.some(m=>m.page===pg.page &&
            (m.text.includes(plain) || (plain.length>8 && plain.includes(m.text))))) {
         el.classList.add("saved");
      }
      layer.appendChild(el);
    }
    const badge=document.createElement("span");
    badge.className="pdf-page-num";
    badge.textContent=pg.page+" / "+pages.length;
    wrapper.append(img,layer,badge);
    viewport.appendChild(wrapper);
  }
  if(Number.isFinite(data.scroll) && data.scroll>=0) viewport.scrollTop=data.scroll;

  function clearSelection() {
    selected=null;
    toolbar.hidden=true;
    const s=window.getSelection();
    if(s) s.removeAllRanges();
  }
  const onPointerUp=()=>{
    const selection=window.getSelection();
    if(!selection || selection.isCollapsed) return;
    let value=selection.toString().trim().replace(/\s+/g," ");
    if(value.length<2 || value.length>2500) return;
    const node=selection.anchorNode;
    const elem=node?.nodeType===1?node:node?.parentElement;
    const from=elem?.closest?.(".pdf-text-layer");
    if(!from || !viewport.contains(from)) return;
    const page=from.closest(".pdf-page");
    if(!page) return;
    const pageNumber=Number(page.dataset.page);
    selected={text:value,page:pageNumber,doc:documentId};
    quote.textContent="선택한 글: "+value.slice(0,300)+(value.length>300?"…":"");
    toolbar.hidden=false;
  };
  viewport.addEventListener("mouseup",onPointerUp);
  viewport.addEventListener("touchend",onPointerUp);
  actions.replaceChildren();
  for(const kind of selectedTypes) {
    const btn=document.createElement("button"); btn.type="button";btn.textContent=kind;
    btn.onclick=()=>{
      if(!selected || selected.doc!==documentId) return;
      const eventId=(typeof crypto!=="undefined"&&crypto.randomUUID)?
          crypto.randomUUID():String(Date.now())+Math.random();
      setTriggerValue("marked",{
         event_id:eventId,material_id:documentId,page:selected.page,
         text:selected.text,kind:kind,scroll:viewport.scrollTop
      });
      clearSelection();
    };
    actions.appendChild(btn);
  }
  cancel.onclick=clearSelection;
  return ()=>{ viewport.removeEventListener("mouseup",onPointerUp);
                viewport.removeEventListener("touchend",onPointerUp); };
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
