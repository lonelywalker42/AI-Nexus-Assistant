"""PDF 元数据提取服务 — 基于 PyMuPDF 布局分析 + 正则 + OpenAlex/Crossref + AI 四级提取"""

import re
import json
from typing import Optional


def extract_pdf_metadata(pdf_path: str) -> dict:
    """从 PDF 文件提取元数据（布局分析 → 内置元数据 → 正则 → OpenAlex/Crossref）

    Returns:
        dict: {title, authors, year, doi, abstract, journal, keywords, ...}
    """
    try:
        import fitz
    except ImportError:
        return {}

    meta = {}
    text = ""

    try:
        doc = fitz.open(pdf_path)

        # 1. 从 PDF 内置元数据提取
        pdf_info = doc.metadata or {}
        if pdf_info.get("title"):
            raw_title = pdf_info["title"].strip()
            if not _looks_generic_title(raw_title, pdf_path):
                meta["title"] = raw_title
        if pdf_info.get("author"):
            raw_authors = pdf_info["author"]
            authors = _parse_author_string(raw_authors)
            if authors:
                meta["authors"] = authors
        if pdf_info.get("subject"):
            meta["abstract"] = pdf_info["subject"].strip()
        if pdf_info.get("keywords"):
            meta["keywords"] = pdf_info["keywords"].strip()

        # 2. 提取全文文本用于正则提取
        for page in doc:
            text += page.get_text()
        doc.close()

        if not text.strip():
            return meta

        # 3. 布局分析提取标题（比首行推断更准确）
        if "title" not in meta:
            layout_title = _extract_title_from_layout(pdf_path)
            if layout_title:
                meta["title"] = layout_title

        # 4. 正则提取 DOI
        doi = _extract_doi(text)
        if doi:
            meta["doi"] = doi

        # 5. 正则提取年份
        year = _extract_year(text, pdf_info)
        if year:
            meta["year"] = year

        # 6. 正则提取摘要
        if "abstract" not in meta:
            abstract = _extract_abstract(text)
            if abstract:
                meta["abstract"] = abstract

        # 7. 正则提取期刊名
        journal = _extract_journal(text)
        if journal:
            meta["journal"] = journal

        # 8. 如果标题仍未提取，从文本首行推断（兜底）
        if "title" not in meta:
            title = _extract_title_from_text(text)
            if title:
                meta["title"] = title

        # 9. 从 DOI 查询 OpenAlex → Crossref 补充元数据
        if meta.get("doi"):
            oa_meta = _fetch_from_openalex(meta["doi"])
            if oa_meta:
                meta.update({k: v for k, v in oa_meta.items() if v and k not in meta})
            # Crossref 兜底（OpenAlex 缺少的字段）
            missing = [k for k in ("title", "authors", "year", "journal", "abstract") if not meta.get(k)]
            if missing:
                cr_meta = _fetch_from_crossref(meta["doi"])
                if cr_meta:
                    meta.update({k: v for k, v in cr_meta.items() if v and k not in meta})

    except Exception as e:
        print(f"[pdf_service] 提取元数据出错: {e}")

    return meta


def _parse_author_string(raw: str) -> list[str]:
    """解析作者字符串为列表"""
    if not raw:
        return []

    # 尝试不同分隔符
    for sep in [";", ",", " and ", " & "]:
        if sep in raw:
            authors = [a.strip() for a in raw.split(sep) if a.strip()]
            if len(authors) > 1:
                return authors

    # 单个作者
    return [raw.strip()] if raw.strip() else []


def _extract_doi(text: str) -> str:
    """从文本中提取 DOI（标准化正则）"""
    # 标准 DOI 模式：10.NNNN/suffix
    patterns = [
        r'(?:doi|DOI)\s*[:\s]*\s*(10\.\d{4,9}/[-._;()/:A-Z0-9]+)',
        r'(?:https?://)?(?:dx\.)?doi\.org/(10\.\d{4,9}/[-._;()/:A-Z0-9]+)',
        r'\b(10\.\d{4,9}/[-._;()/:A-Z0-9]{5,})\b',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            doi = match.group(1).rstrip('.').rstrip(')')
            return doi
    return ""


def _extract_year(text: str, pdf_info: dict = None) -> int:
    """从文本中提取出版年份"""
    # 先从 PDF 元数据提取
    if pdf_info:
        creation_date = pdf_info.get("creationDate", "")
        if creation_date and len(creation_date) >= 4:
            try:
                year = int(creation_date[:4])
                if 1900 <= year <= 2030:
                    return year
            except ValueError:
                pass

    # 正则提取：常见年份模式
    # 模式1: "Published in 2024" / "© 2024"
    match = re.search(r'(?:Published|©|Copyright)\s*(?:in\s+)?(\d{4})', text[:2000])
    if match:
        year = int(match.group(1))
        if 1900 <= year <= 2030:
            return year

    # 模式2: "Received: ... Accepted: ..." 行中的年份
    match = re.search(r'(?:Received|Accepted|Published)\s*[:\s]+\d{1,2}\s+\w+\s+(\d{4})', text[:3000])
    if match:
        year = int(match.group(1))
        if 1900 <= year <= 2030:
            return year

    # 模式3: 首页独立的四位数年份（1990-2030）
    for line in text[:1000].split("\n"):
        match = re.search(r'\b((?:19|20)\d{2})\b', line.strip())
        if match:
            return int(match.group(1))

    return 0


def _extract_abstract(text: str) -> str:
    """从文本中提取摘要"""
    # 模式1: "Abstract" 标题后的内容
    patterns = [
        r'(?:Abstract|ABSTRACT|摘要)\s*[:\-\s]*\n?([\s\S]{50,1500}?)(?:\n\s*(?:Keywords|KEYWORDS|关键词|Introduction|INTRODUCTION|1\.|I\.))',
        r'(?:Abstract|ABSTRACT|摘要)\s*[:\-\s]*\n?([\s\S]{50,1500}?)(?:\n\s*\n)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text[:5000], re.IGNORECASE)
        if match:
            abstract = match.group(1).strip()
            # 清理多余空白
            abstract = re.sub(r'\s+', ' ', abstract)
            if len(abstract) > 50:
                return abstract[:2000]
    return ""


def _extract_journal(text: str) -> str:
    """从文本中提取期刊名"""
    # 模式1: "Published in Journal Name"
    match = re.search(r'Published\s+in\s*[:\s]*([A-Z][^\n]{5,100}?)(?:\n|,|\()', text[:2000])
    if match:
        return match.group(1).strip()

    # 模式2: "Journal of XXX" / "XXX Journal"
    match = re.search(r'\b(Journal\s+of\s+[A-Z][A-Za-z\s&]{5,80}|[A-Z][A-Za-z\s&]{3,50}\s+Journal)\b', text[:2000])
    if match:
        return match.group(1).strip()

    return ""


def _extract_title_from_text(text: str) -> str:
    """从文本首行推断标题"""
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if not lines:
        return ""

    # 第一行通常是标题（排除过短或全大写的行）
    for line in lines[:5]:
        # 跳过过短的行
        if len(line) < 10:
            continue
        # 跳过看起来像页眉的行
        if re.match(r'^(Page|Vol|Issue|DOI|http)', line, re.IGNORECASE):
            continue
        # 跳过全数字行
        if line.isdigit():
            continue
        return line[:200]
    return ""


def _fetch_from_openalex(doi: str) -> dict:
    """从 OpenAlex API 获取补充元数据"""
    import urllib.request
    import urllib.error

    try:
        url = f"https://api.openalex.org/works/doi:{doi}"
        req = urllib.request.Request(url, headers={"User-Agent": "AI-Nexus-Assistant/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())

        result = {}
        if data.get("title"):
            result["title"] = data["title"]
        if data.get("authorships"):
            authors = []
            for a in data["authorships"]:
                name = a.get("author", {}).get("display_name", "")
                if name:
                    authors.append(name)
            if authors:
                result["authors"] = authors
        if data.get("publication_year"):
            result["year"] = data["publication_year"]
        if data.get("primary_location", {}).get("source", {}).get("display_name"):
            result["journal"] = data["primary_location"]["source"]["display_name"]
        if data.get("abstract_inverted_index"):
            result["abstract"] = _reconstruct_abstract(data["abstract_inverted_index"])

        return result
    except Exception:
        return {}


def _reconstruct_abstract(inverted_index: dict) -> str:
    """从 OpenAlex 倒排索引重建摘要文本"""
    if not inverted_index:
        return ""
    word_positions = []
    for word, positions in inverted_index.items():
        for pos in positions:
            word_positions.append((pos, word))
    word_positions.sort()
    return " ".join(w for _, w in word_positions)


def _extract_title_from_layout(pdf_path: str) -> str:
    """基于 PyMuPDF 布局分析提取标题（字体大小 + 位置评分）

    借鉴 PaperQuay 的多策略标题提取：
    1. 字体大小分组：找到最大字体的连续行
    2. 评分函数：fontHeight * 3.2 + topPosition + lengthFit - penalties
    3. 通用标题过滤：排除软件名、出版商名等
    """
    try:
        import fitz
    except ImportError:
        return ""

    try:
        doc = fitz.open(pdf_path)
        if len(doc) == 0:
            doc.close()
            return ""

        page = doc[0]  # 只分析首页
        blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
        doc.close()

        # 收集所有文本行及其字体信息
        lines = []
        for block in blocks:
            if block.get("type") != 0:  # 只处理文本块
                continue
            for line in block.get("lines", []):
                spans = line.get("spans", [])
                if not spans:
                    continue
                text = "".join(s["text"] for s in spans).strip()
                if not text or len(text) < 3:
                    continue
                avg_height = sum(s["size"] for s in spans) / len(spans)
                top = line["bbox"][1]  # y0 坐标
                lines.append({
                    "text": text,
                    "avg_height": round(avg_height, 1),
                    "top": round(top, 1),
                })

        if not lines:
            return ""

        # 按 Y 坐标排序（PDF 坐标系 Y 轴向下）
        lines.sort(key=lambda l: l["top"])

        # 按字体大小分组，找到最大字体的连续行
        max_height = max(l["avg_height"] for l in lines)
        height_tolerance = 1.5  # 字体大小容差

        # 收集最大字体的连续行作为标题候选
        title_candidates = []
        for i, line in enumerate(lines):
            if abs(line["avg_height"] - max_height) <= height_tolerance:
                title_candidates.append((i, line))
            elif title_candidates:
                break  # 遇到不同大小的行就停止

        # 如果最大字体有多行，组合它们
        if title_candidates:
            combined_text = " ".join(t[1]["text"] for t in title_candidates)
            if 6 <= len(combined_text) <= 220 and not _looks_generic_title(combined_text, pdf_path):
                return combined_text

        # 单行评分模式
        scored = []
        for i, line in enumerate(lines):
            score = _title_score(line, i)
            scored.append((score, line["text"]))

        scored.sort(reverse=True)
        for score, text in scored:
            if 6 <= len(text) <= 220 and not _looks_generic_title(text, pdf_path):
                return text

        return ""
    except Exception as e:
        print(f"[pdf_service] 布局标题提取出错: {e}")
        return ""


def _title_score(line: dict, index: int) -> float:
    """标题评分函数（借鉴 PaperQuay）

    评分依据：
    - 字体大小：越大越可能是标题
    - 位置：越靠上越可能是标题
    - 长度适中：36 字符左右最佳
    - 惩罚：包含连续数字（年份）、以标点结尾（句子）
    """
    length_score = max(0, 36 - abs(len(line["text"]) - 36))
    top_score = max(0, 20 - index * 2)
    font_score = min(40, line["avg_height"] * 3.2)
    digit_penalty = 8 if re.search(r'\d{4,}', line["text"]) else 0
    punctuation_penalty = 6 if re.search(r'[;；。！？?]$', line["text"]) else 0
    return font_score + top_score + length_score - digit_penalty - punctuation_penalty


def _looks_generic_title(value: str, path: str) -> bool:
    """检测是否为通用/无意义标题（借鉴 PaperQuay）

    排除：软件名、出版商名、文件名等
    """
    lower = value.lower().strip()
    generic_patterns = [
        "untitled", "microsoft word", "wps office", "wps文字",
        "adobe", "acrobat", "pdf", "sciencedirect", "springer",
        "elsevier", "wiley", "taylor & francis",
        "中国知网", "cnki", "万方", "维普",
        "received manuscript", "accepted manuscript",
    ]
    for pat in generic_patterns:
        if pat in lower:
            return True

    # 如果标题和文件名相同，也认为是通用标题
    if path:
        import os
        stem = os.path.splitext(os.path.basename(path))[0].lower()
        if lower == stem:
            return True

    return False


def _fetch_from_crossref(doi: str) -> dict:
    """从 Crossref API 获取补充元数据（OpenAlex 的兜底）"""
    import urllib.request
    import urllib.error

    try:
        url = f"https://api.crossref.org/works/{doi}"
        req = urllib.request.Request(url, headers={
            "User-Agent": "AI-Nexus-Assistant/1.0 (mailto:nexus@example.com)",
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())

        item = data.get("message", {})
        result = {}

        if item.get("title"):
            result["title"] = item["title"][0] if isinstance(item["title"], list) else item["title"]
        if item.get("author"):
            authors = []
            for a in item["author"][:10]:
                name_parts = []
                if a.get("given"):
                    name_parts.append(a["given"])
                if a.get("family"):
                    name_parts.append(a["family"])
                if name_parts:
                    authors.append(" ".join(name_parts))
            if authors:
                result["authors"] = authors
        # 年份：从 published-print 或 published-online 或 created 提取
        for date_field in ["published-print", "published-online", "created"]:
            parts = item.get(date_field, {}).get("date-parts", [[]])
            if parts and parts[0] and parts[0][0]:
                year = parts[0][0]
                if 1900 <= year <= 2030:
                    result["year"] = year
                    break
        if item.get("container-title"):
            result["journal"] = item["container-title"][0] if isinstance(item["container-title"], list) else item["container-title"]
        if item.get("abstract"):
            # Crossref 摘要可能包含 HTML 标签
            abstract = re.sub(r'<[^>]+>', '', item["abstract"])
            result["abstract"] = abstract.strip()[:2000]

        return result
    except Exception:
        return {}


def title_similarity(a: str, b: str) -> float:
    """计算两个标题的相似度（Dice 系数）

    用于去重：阈值 0.78 以上认为是同一篇论文
    """
    if not a or not b:
        return 0.0

    def tokenize(s: str) -> set:
        # 提取字母数字 token（忽略大小写）
        return set(re.findall(r'[a-z0-9]+', s.lower()))

    tokens_a = tokenize(a)
    tokens_b = tokenize(b)

    if not tokens_a or not tokens_b:
        return 0.0

    intersection = tokens_a & tokens_b
    dice = 2 * len(intersection) / (len(tokens_a) + len(tokens_b))

    # 包含关系检查：短标题完全包含在长标题中
    if len(tokens_a) <= len(tokens_b):
        if tokens_a.issubset(tokens_b):
            dice = max(dice, 0.92)
    else:
        if tokens_b.issubset(tokens_a):
            dice = max(dice, 0.92)

    return dice
