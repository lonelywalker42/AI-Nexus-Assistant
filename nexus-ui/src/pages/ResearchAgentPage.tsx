import { useState, useCallback } from "react";
import { agentApi } from "../api/client";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { IconBook, IconEdit, IconFlask, IconClipboard, IconChat, IconBrain, IconClock, IconX, IconCheck } from "../components/Icons";

const WORKFLOW_TYPES = [
  { key: "review", label: "文献综述", iconName: "book", desc: "多源检索 + 综合报告生成" },
  { key: "writing", label: "论文写作", iconName: "edit", desc: "分章节撰写学术论文" },
  { key: "experiment", label: "实验设计", iconName: "flask", desc: "假设生成 + 实验方案 + 代码骨架" },
  { key: "peer_review", label: "同行评审", iconName: "clipboard", desc: "AI 模拟同行评审并给出改进建议" },
  { key: "debate", label: "多视角讨论", iconName: "chat", desc: "多 Agent 从不同角度讨论，提升推理质量" },
];

const ICON_MAP: Record<string, React.ComponentType<any>> = {
  book: IconBook, edit: IconEdit, flask: IconFlask, clipboard: IconClipboard, chat: IconChat,
};

export default function ResearchAgentPage() {
  const [workflowType, setWorkflowType] = useState("review");
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState("");
  const [config, setConfig] = useState({
    chapters: ["abstract", "introduction", "methodology", "results", "discussion", "conclusion"],
    content: "",
  });

  const handleRun = useCallback(async () => {
    if (!query.trim() || loading) return;

    setLoading(true);
    setError("");
    setResult(null);

    try {
      const res = await agentApi.run({
        query: query.trim(),
        workflow_type: workflowType,
        config: workflowType === "peer_review" ? { content: config.content } : { chapters: config.chapters },
      });

      if (res.error) {
        setError(res.error + (res.traceback ? `\n\n${res.traceback}` : ""));
      } else if (res.status === "failed") {
        // 工作流执行失败，获取错误信息
        const failedStep = (res.steps || []).find((s: any) => s.status === "failed");
        setError(failedStep?.error || "工作流执行失败");
      } else {
        setResult(res);
      }
    } catch (err: any) {
      setError(err.message || "执行失败");
    } finally {
      setLoading(false);
    }
  }, [query, workflowType, config, loading]);

  const getResultContent = () => {
    if (!result) return "";

    if (workflowType === "review") {
      const steps = result.steps || [];
      const reviewStep = steps.find((s: any) => s.step_type === "review");
      return reviewStep?.output_data?.review_content || result.result?.review_content || "";
    }

    if (workflowType === "writing") {
      const steps = result.steps || [];
      const writingStep = steps.find((s: any) => s.step_type === "writing");
      return writingStep?.output_data?.paper_content || result.result?.paper_content || "";
    }

    if (workflowType === "experiment") {
      const steps = result.steps || [];
      const expStep = steps.find((s: any) => s.step_type === "experiment");
      const data = expStep?.output_data || result.result || {};

      let md = "";
      if (data.hypotheses) {
        md += "## 研究假设\n\n";
        data.hypotheses.forEach((h: any, i: number) => {
          md += `### 假设 ${h.id || i + 1}\n`;
          md += `- **假设**: ${h.hypothesis}\n`;
          md += `- **方法**: ${h.method}\n`;
          md += `- **预期结果**: ${h.expected_result}\n`;
          md += `- **创新性**: ${h.novelty}\n\n`;
        });
      }
      if (data.experiment_plan) {
        md += "## 实验方案\n\n";
        md += "```json\n" + JSON.stringify(data.experiment_plan, null, 2) + "\n```\n\n";
      }
      if (data.code_skeleton) {
        md += "## 代码骨架\n\n" + data.code_skeleton;
      }
      return md;
    }

    if (workflowType === "peer_review") {
      const steps = result.steps || [];
      const reviewStep = steps.find((s: any) => s.step_type === "peer_review");
      const data = reviewStep?.output_data?.review || result.result?.review || {};

      let md = "## 评审报告\n\n";
      if (data.summary) md += `**总体评价**: ${data.summary}\n\n`;
      if (data.scores) {
        md += "### 评分\n\n";
        md += `- 创新性: ${data.scores.novelty}/10\n`;
        md += `- 严谨性: ${data.scores.rigor}/10\n`;
        md += `- 完整性: ${data.scores.completeness}/10\n`;
        md += `- 可复现性: ${data.scores.reproducibility}/10\n`;
        md += `- 表达质量: ${data.scores.clarity}/10\n`;
        md += `- **总分: ${data.scores.overall}/10**\n\n`;
      }
      if (data.strengths?.length) {
        md += "### 优点\n\n" + data.strengths.map((s: string) => `- ${s}`).join("\n") + "\n\n";
      }
      if (data.weaknesses?.length) {
        md += "### 问题\n\n" + data.weaknesses.map((w: string) => `- ${w}`).join("\n") + "\n\n";
      }
      if (data.suggestions?.length) {
        md += "### 修改建议\n\n" + data.suggestions.map((s: string) => `- ${s}`).join("\n") + "\n\n";
      }
      if (data.recommendation) {
        md += `### 最终建议: **${data.recommendation}**\n`;
      }
      return md;
    }

    if (workflowType === "debate") {
      const steps = result.steps || [];
      const debateStep = steps.find((s: any) => s.step_type === "review");
      const data = debateStep?.output_data || result.result || {};

      let md = "## 多视角讨论报告\n\n";

      if (data.debate_history) {
        data.debate_history.forEach((round: any) => {
          md += `### 第 ${round.round} 轮讨论\n\n`;
          round.perspectives?.forEach((p: any) => {
            md += `#### ${p.perspective}\n\n${p.content}\n\n`;
          });
        });
      }

      if (data.synthesis) {
        md += "## 综合分析\n\n" + data.synthesis;
      }

      return md;
    }

    return JSON.stringify(result, null, 2);
  };

  return (
    <div className="flex flex-col gap-4 h-full">
      <h2 className="text-base font-bold flex items-center gap-2" style={{ color: "var(--text-primary)" }}>
        <IconBrain size={18} /> 科研 Agent 工作流
      </h2>

      {/* 工作流类型选择 */}
      <div className="grid grid-cols-2 gap-2">
        {WORKFLOW_TYPES.map((wt) => (
          <button
            key={wt.key}
            className="glass-card p-3 text-left cursor-pointer transition-all"
            style={{
              border: workflowType === wt.key ? "2px solid var(--accent-blue)" : "2px solid transparent",
              opacity: loading ? 0.6 : 1,
            }}
            onClick={() => !loading && setWorkflowType(wt.key)}
          >
            <div className="flex items-center gap-2">
              {(() => { const Icon = ICON_MAP[wt.iconName]; return Icon ? <Icon size={18} style={{ color: "var(--accent-blue)" }} /> : null; })()}
              <span className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
                {wt.label}
              </span>
            </div>
            <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
              {wt.desc}
            </p>
          </button>
        ))}
      </div>

      {/* 输入区域 */}
      <div className="glass-card p-3 flex flex-col gap-3">
        <textarea
          className="w-full bg-transparent border-none outline-none resize-none text-sm"
          style={{ color: "var(--text-primary)" }}
          placeholder={
            workflowType === "review"
              ? "输入研究主题，如: 深度学习在目标检测中的应用"
              : workflowType === "writing"
              ? "输入论文主题，如: 基于 Transformer 的图像分类方法研究"
              : workflowType === "experiment"
              ? "输入研究方向，如: 图神经网络在社交网络分析中的应用"
              : "输入待评审的文档标题"
          }
          rows={2}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          disabled={loading}
        />

        {workflowType === "peer_review" && (
          <textarea
            className="w-full bg-transparent border-none outline-none resize-none text-xs"
            style={{ color: "var(--text-secondary)", border: "1px solid var(--border-color)", borderRadius: "8px", padding: "8px" }}
            placeholder="粘贴待评审的文档内容..."
            rows={4}
            value={config.content}
            onChange={(e) => setConfig((prev) => ({ ...prev, content: e.target.value }))}
            disabled={loading}
          />
        )}

        <div className="flex justify-between items-center">
          <span className="text-xs" style={{ color: "var(--text-muted)" }}>
            {loading ? <span className="flex items-center gap-1"><IconClock size={13} /> 正在执行...</span> : result ? <span className="flex items-center gap-1"><IconCheck size={13} /> 执行完成</span> : "就绪"}
          </span>
          <button
            className="btn-gradient btn-click"
            onClick={handleRun}
            disabled={loading || !query.trim()}
          >
            {loading ? "执行中..." : "开始执行"}
          </button>
        </div>
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="glass-card p-3" style={{ border: "1px solid #ef4444" }}>
          <p className="text-sm flex items-center gap-1" style={{ color: "#ef4444" }}><IconX size={13} /> {error}</p>
        </div>
      )}

      {/* 结果展示 */}
      {result && (
        <div className="glass-card p-4 flex-1 overflow-y-auto">
          <div className="markdown-body text-sm">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {getResultContent()}
            </ReactMarkdown>
          </div>
        </div>
      )}
    </div>
  );
}
