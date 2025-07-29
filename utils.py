from docxtpl import DocxTemplate, InlineImage
from docx.shared import Mm
from docx2pdf import convert
import os
import re
from functools import wraps
from flask_login import current_user
from flask import abort
from bs4 import BeautifulSoup, NavigableString, Tag
import pythoncom
import mistune
from PIL import Image

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def _resolve_image_path(src: str) -> str:
    """
    將 HTML 圖片 src 轉換為本地檔案絕對路徑
    支援 /static/... 路徑與相對路徑
    """
    if src.startswith('/'):
        static_index = src.find('/static/')
        if static_index != -1:
            img_path_rel = src[static_index+1:]  # 移除開頭斜線
            return os.path.join(BASE_DIR, img_path_rel)
    return os.path.join(BASE_DIR, src.lstrip('/'))

import logging

DEBUG_LOG = True  # 設定為 False 可關閉 debug 訊息

def _process_markdown_sections(doc, md_content):
    from bs4 import BeautifulSoup, Tag
    from PIL import Image
    from docxtpl import InlineImage
    from docx.shared import Mm

    def log(msg):
        if DEBUG_LOG:
            print(f"[DEBUG] {msg}")

    def resolve_image(src):
        if src.startswith('/'):
            static_index = src.find('/static/')
            if static_index != -1:
                path_rel = src[static_index + 1:]
                return os.path.join(BASE_DIR, path_rel)
        return os.path.join(BASE_DIR, src.lstrip('/'))

    def extract_table_text(table_tag):
        lines = []
        for i, row in enumerate(table_tag.find_all("tr")):
            cells = row.find_all(["td", "th"])
            row_text = " | ".join(cell.get_text(strip=True) for cell in cells)
            lines.append(row_text)
            if i == 0:
                lines.append(" | ".join(["---"] * len(cells)))
        return "\n".join(lines)

    results = []
    if not md_content:
        log("Markdown content is empty")
        return results

    html = mistune.html(md_content)
    soup = BeautifulSoup(html, 'lxml')

    for elem in soup.body.children:
        if isinstance(elem, Tag):
            if elem.name == 'table':
                table_text = extract_table_text(elem)
                log(f"[表格] {table_text}")
                results.append({'text': table_text, 'image': None})
                continue

            if elem.name in ['p', 'div']:
                for child in elem.children:
                    if isinstance(child, Tag) and child.name == 'img' and child.has_attr('src'):
                        try:
                            img_path = resolve_image(child['src'])
                            if os.path.exists(img_path):
                                with Image.open(img_path) as im:
                                    width_px = im.width
                                    width_mm = min(width_px * 25.4 / 96, 130)
                                    image = InlineImage(doc, img_path, width=Mm(width_mm))
                                    log(f"[圖片] {img_path}, 寬: {width_mm:.2f} mm")
                                    results.append({'text': None, 'image': image})
                            else:
                                log(f"[警告] 圖片不存在: {img_path}")
                        except Exception as e:
                            log(f"[錯誤] 圖片處理失敗: {e}")
                    else:
                        text = child.get_text(strip=True) if hasattr(child, 'get_text') else str(child).strip()
                        if text:
                            log(f"[文字] {text}")
                            results.append({'text': text, 'image': None})
    return results





def fill_template(values, template_path, output_word_path, output_pdf_path):
    from docxtpl import DocxTemplate
    import pythoncom
    from docx2pdf import convert

    doc = DocxTemplate(template_path)

    # 填入 context，None 改為空字串
    context = {k: (v if v is not None else '') for k, v in values.items()}

    # 更新後版本：處理 Markdown → sections（支援圖片+表格+段落）
    context["change_before_sections"] = _process_markdown_sections(doc, context.get("change_before", ""))
    context["change_after_sections"] = _process_markdown_sections(doc, context.get("change_after", ""))

    # 渲染
    doc.render(context)
    doc.save(output_word_path)

    # 轉 PDF
    try:
        pythoncom.CoInitialize()
        convert(output_word_path, output_pdf_path)
    except Exception as e:
        print(f"PDF conversion failed: {e}")
        raise
    finally:
        pythoncom.CoUninitialize()




def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            abort(403)  # Forbidden
        return f(*args, **kwargs)
    return decorated_function

def editor_or_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ['editor', 'admin']:
            abort(403) # Forbidden
        return f(*args, **kwargs)
    return decorated_function

def add_history_log(spec_id, action, details=""):
    """新增一筆操作歷史紀錄"""
    from models import db, SpecHistory
    
    history_entry = SpecHistory(
        spec_id=spec_id,
        user_id=current_user.id,
        action=action,
        details=details
    )
    db.session.add(history_entry)
