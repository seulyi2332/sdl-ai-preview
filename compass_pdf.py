"""PDF page extraction for paragraph-level learner highlighting. No OCR is performed."""
import fitz


def extract_pdf(data,max_pages=35,max_bytes=12_000_000):
    if not data or len(data)>max_bytes:
        raise ValueError("PDF 파일은 12MB 이하만 업로드할 수 있어요.")
    try:
        doc=fitz.open(stream=data,filetype="pdf")
    except Exception as exc:
        raise ValueError("PDF를 열 수 없습니다. 다른 파일로 시도해 주세요.") from exc
    if doc.page_count>max_pages:
        raise ValueError("빠른 시연에서는 35쪽 이하의 PDF를 사용해 주세요.")
    paragraphs=[]
    for p in range(doc.page_count):
        page=doc[p]
        blocks=page.get_text("blocks",sort=True)
        count=0
        for block in blocks:
            if len(block)<7 or block[6]!=0:  # skip picture blocks
                continue
            text=str(block[4] or "").strip()
            text=" ".join(text.split())
            if len(text)<8:
                continue
            # Preserve paragraph chunks, cap user-upload size in prompt.
            for i in range(0,len(text),1000):
                chunk=text[i:i+1000]
                paragraphs.append({"id":f"p{p+1}-{count}","page":p+1,"text":chunk})
                count+=1
                if len(paragraphs)>=750:
                    break
            if len(paragraphs)>=750:
                break
        if len(paragraphs)>=750:
            break
    pages=doc.page_count
    doc.close()
    return paragraphs,pages


def render_page(data,page_num,width=800):
    doc=fitz.open(stream=data,filetype="pdf")
    if not 1<=page_num<=doc.page_count:
        doc.close()
        raise ValueError("쪽 번호가 올바르지 않아요.")
    page=doc[page_num-1]
    scale=min(width/page.rect.width,2.0)
    pix=page.get_pixmap(matrix=fitz.Matrix(scale,scale),alpha=False)
    png=pix.tobytes("png")
    doc.close()
    return png
