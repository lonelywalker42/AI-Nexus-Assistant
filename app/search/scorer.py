"""相似度评分算法 — 从 ai-literature (JS) 移植到 Python

包含：Levenshtein 距离、中文二元分词、停用词过滤、综合相似度评分
"""

import re
from typing import List, Set

# ── 停用词表 ──────────────────────────────────────────────────
STOP_WORDS: Set[str] = {
    "a", "an", "the", "and", "or", "of", "in", "on", "for", "to", "with", "by",
    "from", "at", "is", "are", "was", "were", "be", "been", "being", "it", "its",
    "this", "that", "these", "those", "as", "via", "into", "over", "based",
    "using", "use", "used", "new", "novel", "approach", "approaches", "method",
    "methods", "study", "analysis", "review", "survey", "paper", "system",
    "model", "models", "data", "case", "results", "result", "towards", "toward",
    "between", "through", "across", "about", "our", "we", "their", "they",
    "can", "do", "does", "not", "no", "all", "some", "any", "each", "both",
    "more", "most", "other", "another", "such", "than", "too", "very", "just",
    "also", "how", "what", "which", "when", "where", "who", "why", "if", "but",
    "so", "up", "out", "off", "down", "under",
    "等", "研究", "方法", "基于", "分析", "应用", "问题", "系统", "模型", "一种",
    "利用", "采用", "设计", "实现", "探讨", "相关", "比较", "综合", "不同",
    "方面", "技术", "论文", "文章",
}


def levenshtein(a: str, b: str) -> int:
    """编辑距离"""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)

    la, lb = len(a), len(b)
    dp = [[0] * (lb + 1) for _ in range(la + 1)]
    for i in range(la + 1):
        dp[i][0] = i
    for j in range(lb + 1):
        dp[0][j] = j

    for i in range(1, la + 1):
        for j in range(1, lb + 1):
            if a[i - 1] == b[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])
    return dp[la][lb]


def word_similar(a: str, b: str) -> float:
    """词相似度 (0-1)"""
    if a == b:
        return 1.0
    if len(a) <= 2 or len(b) <= 2:
        return 1.0 if a == b else 0.0
    dist = levenshtein(a, b)
    max_len = max(len(a), len(b))
    return 1.0 - dist / max_len


def tokenize(text: str) -> List[str]:
    """分词：中文二元分词 + 英文分词 + 停用词过滤"""
    lower = text.lower()
    tokens = []

    # 按中英文分割
    parts = re.split(r'([一-鿿]+)', lower)
    for part in parts:
        if not part:
            continue
        if re.match(r'^[一-鿿]+$', part):
            # 中文：二元分词
            if len(part) >= 2:
                for i in range(len(part) - 1):
                    tokens.append(part[i:i + 2])
        else:
            # 英文/数字：按空格和标点分割
            eng_tokens = re.sub(r'[^a-z0-9\s]', ' ', part).split()
            tokens.extend(eng_tokens)

    return [w for w in tokens if w not in STOP_WORDS]


def sim_score(query: str, title: str) -> float:
    """计算查询与标题的综合相似度 (0-1)"""
    q = tokenize(query)
    t = tokenize(title)
    if not q or not t:
        return 0.0

    t_matched = set()
    match = 0.0

    for qw in q:
        best_sim = 0.0
        best_idx = -1
        for i, tw in enumerate(t):
            if i in t_matched:
                continue
            sim = word_similar(qw, tw)
            if sim > best_sim:
                best_sim = sim
                best_idx = i
        if best_sim >= 0.8 and best_idx >= 0:
            match += best_sim
            t_matched.add(best_idx)

    return match / max(len(q), len(t))
