/**
 * 轻量级 Markdown → HTML 渲染器
 * 用于不依赖 react-markdown 的简单场景（文献摘要、实验结论等）
 */

/** 转义 HTML 特殊字符 */
export function escapeHtml(text: string): string {
  return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

/** 将 Markdown 文本转换为 HTML 字符串 */
export function renderSimpleMarkdown(md: string): string {
  if (!md) return "";
  const codeBlocks: string[] = [];
  let result = md.replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) => {
    const idx = codeBlocks.length;
    codeBlocks.push(`<pre><code class="lang-${escapeHtml(lang)}">${escapeHtml(code.trim())}</code></pre>`);
    return `__CODEBLOCK_${idx}__`;
  });
  // 表格
  result = result.replace(/(?:^|\n)(\|.+\|)\n(\|[-| :]+\|)\n((?:\|.+\|\n?)+)/g, (_, header, _sep, body) => {
    const ths = header.split("|").filter((c: string) => c.trim()).map((c: string) => `<th>${c.trim()}</th>`).join("");
    const rows = body.trim().split("\n").map((row: string) => {
      const tds = row.split("|").filter((c: string) => c.trim()).map((c: string) => `<td>${c.trim()}</td>`).join("");
      return `<tr>${tds}</tr>`;
    }).join("");
    return `<table><thead><tr>${ths}</tr></thead><tbody>${rows}</tbody></table>`;
  });
  // 标题
  result = result.replace(/^#### (.+)$/gm, "<h4>$1</h4>");
  result = result.replace(/^### (.+)$/gm, "<h3>$1</h3>");
  result = result.replace(/^## (.+)$/gm, "<h2>$1</h2>");
  result = result.replace(/^# (.+)$/gm, "<h1>$1</h1>");
  // 行内格式
  result = result.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  result = result.replace(/\*(.+?)\*/g, "<em>$1</em>");
  result = result.replace(/`([^`]+)`/g, "<code>$1</code>");
  // 列表
  result = result.replace(/^- (.+)$/gm, "<li>$1</li>");
  result = result.replace(/^(\d+)\. (.+)$/gm, "<li>$2</li>");
  result = result.replace(/(<li>.*<\/li>\n?)+/g, (m) => `<ul>${m}</ul>`);
  // 引用、链接、分隔线
  result = result.replace(/^> (.+)$/gm, "<blockquote>$1</blockquote>");
  result = result.replace(/\[(.+?)\]\((.+?)\)/g, '<a href="$2" target="_blank">$1</a>');
  result = result.replace(/^---$/gm, "<hr>");
  // 段落与换行
  result = result.replace(/\n\n/g, "</p><p>");
  result = result.replace(/\n/g, "<br>");
  // 还原代码块
  result = result.replace(/__CODEBLOCK_(\d+)__/g, (_, idx) => codeBlocks[parseInt(idx)]);
  return result;
}
