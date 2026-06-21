"""导出服务 — DOCX / Markdown 参考文献列表"""

import json
from typing import Optional
from sqlalchemy.orm import Session


def _check_docx_available() -> bool:
    """检查 python-docx 是否可用"""
    try:
        import docx
        return True
    except ImportError:
        return False


def export_docx(content: str, output_path: str, title: str = "文档") -> dict:
    """将 Markdown 内容导出为 DOCX"""
    if not _check_docx_available():
        return {"status": "error", "message": "python-docx 未安装，请运行: pip install python-docx"}

    from docx import Document
    from docx.shared import Pt, Inches
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    import re

    doc = Document()

    # 设置默认字体
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Times New Roman'
    font.size = Pt(12)

    # 解析 Markdown 并添加到文档
    lines = content.split('\n')
    in_code_block = False
    code_content = []

    for line in lines:
        # 代码块
        if line.strip().startswith('```'):
            if in_code_block:
                # 结束代码块
                if code_content:
                    p = doc.add_paragraph()
                    p.style = doc.styles['Normal']
                    run = p.add_run('\n'.join(code_content))
                    run.font.name = 'Courier New'
                    run.font.size = Pt(10)
                code_content = []
            in_code_block = not in_code_block
            continue

        if in_code_block:
            code_content.append(line)
            continue

        # 标题
        if line.startswith('#'):
            level = len(line) - len(line.lstrip('#'))
            text = line.lstrip('#').strip()
            if level <= 3:
                doc.add_heading(text, level=level)
            else:
                p = doc.add_paragraph()
                run = p.add_run(text)
                run.bold = True
            continue

        # 列表
        if line.strip().startswith('- ') or line.strip().startswith('* '):
            text = line.strip()[2:]
            doc.add_paragraph(text, style='List Bullet')
            continue

        if re.match(r'^\d+\.\s', line.strip()):
            text = re.sub(r'^\d+\.\s', '', line.strip())
            doc.add_paragraph(text, style='List Number')
            continue

        # 粗体和斜体
        text = line
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        text = re.sub(r'\*(.*?)\*', r'\1', text)

        # 普通段落
        if text.strip():
            doc.add_paragraph(text)
        else:
            doc.add_paragraph()

    doc.save(output_path)
    return {"status": "ok", "path": output_path}


def export_markdown_refs(db: Session, paper_ids: list[str] = None,
                         style: str = "gb7714") -> str:
    """导出 Markdown 参考文献列表"""
    from app.models.paper import Paper
    from app.search.citation import format_gb

    if paper_ids:
        papers = db.query(Paper).filter(Paper.id.in_(paper_ids)).all()
    else:
        papers = db.query(Paper).all()

    if not papers:
        return ""

    refs = []
    for i, p in enumerate(papers, 1):
        paper_dict = {
            "title": p.title,
            "authors": json.loads(p.authors) if p.authors else [],
            "year": p.year,
            "doi": p.doi,
            "journal": p.journal,
            "paper_type": p.paper_type,
        }

        if style == "gb7714":
            ref = format_gb(paper_dict, i)
        elif style == "apa":
            ref = _format_apa(paper_dict)
        elif style == "ieee":
            ref = _format_ieee(paper_dict, i)
        elif style == "mla":
            ref = _format_mla(paper_dict)
        else:
            ref = format_gb(paper_dict, i)

        refs.append(f"[{i}] {ref}")

    return "\n\n".join(refs)


def _format_apa(paper: dict) -> str:
    """APA 7th edition"""
    authors = paper.get("authors", [])
    year = paper.get("year", "n.d.")
    title = paper.get("title", "")
    journal = paper.get("journal", "")
    doi = paper.get("doi", "")

    if not authors:
        author_str = "Unknown Author"
    elif len(authors) == 1:
        parts = authors[0].split()
        author_str = f"{parts[-1]}, {' '.join(p[0] + '.' for p in parts[:-1])}" if len(parts) > 1 else authors[0]
    elif len(authors) <= 20:
        formatted = []
        for a in authors:
            parts = a.split()
            if len(parts) > 1:
                formatted.append(f"{parts[-1]}, {' '.join(p[0] + '.' for p in parts[:-1])}")
            else:
                formatted.append(a)
        author_str = ", ".join(formatted[:-1]) + ", & " + formatted[-1]
    else:
        parts = authors[0].split()
        first = f"{parts[-1]}, {' '.join(p[0] + '.' for p in parts[:-1])}" if len(parts) > 1 else authors[0]
        author_str = f"{first}, ... {authors[-1].split()[-1]}"

    s = f"{author_str} ({year}). {title}."
    if journal:
        s += f" *{journal}*."
    if doi:
        s += f" https://doi.org/{doi}"
    return s


def _format_ieee(paper: dict, idx: int = 1) -> str:
    """IEEE"""
    authors = paper.get("authors", [])
    year = paper.get("year", "")
    title = paper.get("title", "")
    journal = paper.get("journal", "")

    formatted = []
    for a in authors:
        parts = a.split()
        if len(parts) > 1:
            formatted.append(f"{' '.join(p[0] + '.' for p in parts[:-1])} {parts[-1]}")
        else:
            formatted.append(a)
    author_str = ", ".join(formatted) if formatted else "Unknown"

    s = f"[{idx}] {author_str}, \"{title}\""
    if journal:
        s += f", *{journal}*"
    if year:
        s += f", {year}"
    s += "."
    return s


def _format_mla(paper: dict) -> str:
    """MLA 9th edition"""
    authors = paper.get("authors", [])
    year = paper.get("year", "")
    title = paper.get("title", "")
    journal = paper.get("journal", "")

    if not authors:
        author_str = "Unknown Author"
    elif len(authors) == 1:
        parts = authors[0].split()
        author_str = f"{parts[-1]}, {' '.join(parts[:-1])}" if len(parts) > 1 else authors[0]
    elif len(authors) == 2:
        parts = authors[0].split()
        first = f"{parts[-1]}, {' '.join(parts[:-1])}" if len(parts) > 1 else authors[0]
        author_str = f"{first}, and {authors[1]}"
    else:
        parts = authors[0].split()
        author_str = f"{parts[-1]}, {' '.join(parts[:-1])}, et al." if len(parts) > 1 else f"{authors[0]}, et al."

    s = f'{author_str}. "{title}."'
    if journal:
        s += f" *{journal}*"
    if year:
        s += f", {year}"
    s += "."
    return s
