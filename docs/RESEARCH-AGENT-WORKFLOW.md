# 科研 Agent 写作工作流调研报告

> 研究日期: 2026-06-21
> 目标: 调研用于科研的「检索 → 综述 → 试验搭建 → 论文写作」全流程 Agent 工作流
> 覆盖: 4 路并行搜索，30+ 开源项目，6 种架构模式

---

## 一、全景图：科研 Agent 工作流的四个阶段

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  ① 检索     │ →  │  ② 综述     │ →  │  ③ 试验搭建 │ →  │  ④ 论文写作 │
│  Retrieval   │    │  Review     │    │  Experiment  │    │  Writing    │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
  文献搜索           文献综述/摘要       假设生成             LaTeX 生成
  引文追踪           多视角综合         实验设计             章节撰写
  新颖性检查         知识图谱推理       代码生成/执行         引文管理
  PDF 解析           系统性筛选         结果分析/可视化       同行评审模拟
```

---

## 二、端到端全流程系统 (覆盖全部 4 个阶段)

> 这些项目最值得深度研究——它们实现了从研究想法到完整论文的全自动化。

### 2.1 The AI Scientist (Sakana AI) ⭐ 最完整

- **GitHub**: [SakanaAI/AI-Scientist](https://github.com/SakanaAI/AI-Scientist) (v1: 14k+ ⭐)
- **v2**: [SakanaAI/AI-Scientist-v2](https://github.com/SakanaAI/AI-Scientist-v2) — 移除模板依赖
- **License**: Apache-2.0 (v1) / 自定义 (v2)
- **Tech Stack**: Python 3.11, PyTorch, LaTeX, Semantic Scholar API, OpenAlex API

**全流程覆盖**:

| 阶段 | 实现方式 |
|------|---------|
| ① 检索 | Semantic Scholar / OpenAlex 检查新颖性 + 收集引文 |
| ② 综述 | 新颖性检查 + 相关工作发现 |
| ③ 试验搭建 | LLM 生成实验代码 → 自主执行 (PyTorch/CUDA) → 生成图表 |
| ④ 论文写作 | 自动生成完整 LaTeX 论文 → pdflatex 编译为 PDF |
| ⑤ 评审 | LLM 模拟同行评审 (集成评分 + 反思 + 接收/拒稿决定) |

**架构**: 模板化模块系统。每个领域模板包含 `experiment.py`, `plot.py`, `prompt.json`, `seed_ideas.json`, `latex/`。v2 使用「渐进式 Agent 树搜索」探索实验路径。

**成本**: ~$15-20/篇 (实验) + ~$5 (写作)

**局限**: 目前主要适配 ML 研究模板，需要 NVIDIA GPU

**关键启示**:
- 模板化架构使得端到端自动化成为可能
- 新颖性检查 (Semantic Scholar) 是研究流程的关键环节
- 自动同行评审提供了质量闭环

---

### 2.2 AutoResearchClaw ⭐ 最成熟 (13.5k ⭐)

- **GitHub**: [aiming-lab/AutoResearchClaw](https://github.com/aiming-lab/AutoResearchClaw)
- **License**: MIT
- **Tech Stack**: Python, 多 Agent 架构

**全流程覆盖**:

| 阶段 | 实现方式 |
|------|---------|
| ① 检索 | OpenAlex + Semantic Scholar + arXiv 多源检索 |
| ② 综述 | 多 Agent 辩论进行假设生成和综合 |
| ③ 试验搭建 | 自修复代码生成 + GPU 执行 + 6 种人工干预模式 |
| ④ 论文写作 | 分章节撰写 (5000-6500 字)，会议模板 (NeurIPS/ICML/ICLR) |
| ⑤ 评审 | 多 Agent 辩论式同行评审 |

**核心创新**:
- **4 层引文验证**: arXiv ID → DOI (CrossRef/DataCite) → Semantic Scholar 标题匹配 → LLM 相关性评分，自动移除伪造引文
- **23 阶段 8 相位**流水线
- **自修复代码**: 实验代码失败时自动诊断和修复
- **领域专家**: 物理/生物/统计/化学专用 Agent

---

### 2.3 NanoResearch

- **GitHub**: [OpenRaiser/NanoResearch](https://github.com/OpenRaiser/NanoResearch)
- **License**: 开源

**9 阶段流水线**: Ideation → Planning → Setup → Coding → Execution → Analysis → Figure Generation → Writing → Review

**核心创新**:
- 运行真实 GPU/SLURM 作业，自动调试和重试
- **Evo 模式**: 跨会话自我进化，积累技能
- 支持 Claude Code 集成 + Codex 支持

---

### 2.4 Sibyl AutoResearch System

- **GitHub**: [Sibyl-Research-Team/AutoResearch-SibylSystem](https://github.com/Sibyl-Research-Team/AutoResearch-SibylSystem)
- **License**: MIT
- **Stars**: 256

**19 阶段流水线**: 文献搜索 → 6 Agent 辩论 → 实验规划 → 试点实验 → 全量 GPU 并行实验 → 结果辩论 → 决策/继续/转向 → 写作 → 评审 → 质量门

**核心创新**:
- **20+ 专业化 Agent** (Innovator, Skeptic, Empiricist 等)
- **PIVOT 机制**: 结果不理想时回滚到想法生成 (最多 6 轮)
- **双循环架构**: 系统从自身流程中学习，改进未来项目
- 基于 Claude Code 原生构建
- GPU 并行实验执行

---

### 2.5 AutoR

- **GitHub**: [AutoX-AI-Labs/AutoR](https://github.com/AutoX-AI-Labs/AutoR)

**9 阶段**: Intake → Literature Survey → Hypothesis Generation → Study Design → Implementation → Experimentation → Analysis → Writing → Dissemination

**核心创新**:
- **人机协作设计**: "AI 负责执行，人类掌控方向"
- 每个阶段需要人工审批才能推进
- 每次运行成为独立的、完全可审计的目录

---

### 2.6 PaperForge

- **GitHub**: [QJHWC/PaperForge](https://github.com/QJHWC/PaperForge)
- **Stars**: 577

**4 种工作流**: Research Partner, MVP, Scientist, Writeup

**核心创新**:
- 反 AI 检测写作风格
- 多 LLM 路由 + 可配置网关
- 支持 IEEE_TII, CJC 等会议/期刊模板

---

### 2.7 FAROS

- **GitHub**: [OpenNSWM-Lab/FAROS](https://github.com/OpenNSWM-Lab/FAROS)
- **Stars**: ~1k

**4 阶段**: 想法生成/精炼 → 实验脚手架 → 会议感知 LaTeX 论文生成 → 模拟同行评审

**核心创新**:
- Blueprint 驱动架构 (非单体 Agent)
- Provider 无关设计 + REST API
- 支持 ICML/NeurIPS/ICLR/ACL 模板

---

### 2.8 PaperOrchestra (Google Research)

- **GitHub**: [google-research/paper-orchestra](https://github.com/google-research/paper-orchestra)
- **License**: Apache-2.0

**多 Agent 流水线**: 大纲生成 → 文献综述 → 分节写作 → 内容精炼 → 绘图

**核心创新**:
- 支持 Gemini/Vertex AI + OpenAI
- 输出会议就绪的 LaTeX 手稿 (如 CVPR 2025 模板)
- Streamlit 演示前端

---

## 三、按阶段深度分析

### 3.1 阶段一：文献检索 (Retrieval)

| 项目 | GitHub | 核心能力 | 数据源 |
|------|--------|---------|--------|
| **GPT-Researcher** | [assafelovic/gpt-researcher](https://github.com/assafelovic/gpt-researcher) (27.8k ⭐) | Planner 分解查询 → 多 Crawler 并行搜索 → 过滤排序 → 报告生成 | Tavily, MCP, 本地文档 |
| **PaperQA2** | [Future-House/paper-qa](https://github.com/Future-House/paper-qa) (8.7k ⭐) | Agentic RAG — LLM 生成关键词 → 向量检索 → 上下文摘要 → 迭代精炼 | Semantic Scholar, Crossref, Unpaywall |
| **STORM** | [stanford-oval/storm](https://github.com/stanford-oval/storm) (29k ⭐) | 多视角提问 — 模拟写作者与主题专家对话，基于互联网搜索 | Bing, Google, Tavily, Brave, DuckDuckGo, SearXNG |
| **SciAgents** | [lamm-mit/SciAgentsDiscovery](https://github.com/lamm-mit/SciAgentsDiscovery) | 知识图谱推理 — 发现跨学科隐藏关系 | Semantic Scholar, 知识图谱 |
| **ASReview** | [asreview/asreview](https://github.com/asreview/asreview) | 主动学习筛选 — ML 模型从用户标注中学习，减少 50-95% 筛选时间 | 用户提供 (CSV/RIS/XLSX) |

**GPT-Researcher 架构**:
```
用户查询
    ↓
[Planner Agent] → 分解为 N 个子问题
    ↓
[Crawler Agent 1] [Crawler Agent 2] ... [Crawler Agent N]  (并行)
    ↓
[Filter/Rank] → 去重 + 相关性排序
    ↓
[Publisher Agent] → 综合 20+ 源生成 2000+ 字报告
```

**PaperQA2 的 3 阶段算法**:
1. **Paper Search**: LLM 生成关键词查询 → 候选论文分块嵌入
2. **Evidence Gathering**: Top-k 向量检索 + LLM 重排 + 上下文摘要 (RCS)
3. **Generate Answer**: 最佳摘要放入 prompt，带内联引文

**关键启示**:
- **并行搜索**是提升检索效率的关键模式 (GPT-Researcher, STORM)
- **Agentic RAG** 比单次 RAG 更深入 (PaperQA2 的多轮迭代)
- **知识图谱**能发现传统搜索遗漏的跨学科关联 (SciAgents)

---

### 3.2 阶段二：文献综述 (Review)

| 项目 | 核心能力 | 综述模式 |
|------|---------|---------|
| **STORM** | 多视角综合 — 模拟不同领域专家的对话 | 全自动 + Co-STORM (人机协作) |
| **PaperQA2** | 科学问答 — "超人表现" 的科学 QA 基准 | Agentic RAG 迭代精炼 |
| **SciAgents** | 知识图谱推理 — 结构化 JSON 输出 (假设/结果/机制/设计原则) | 图路径采样 + 多 Agent 辩论 |
| **ASReview** | 系统性筛选 — 主动学习加速 | 人机协作标注 |

**STORM 的独特方法**:
1. **多视角提问**: 模拟写作者与多个主题专家的对话
2. **大纲生成**: 从策划知识中创建层次结构
3. **文章生成**: 填充大纲为全长文本 + 引文
4. **文章润色**: 摘要和去重

**SciAgents 的 Agent 角色**:
- **Ontologist**: 从知识图谱定义关键概念和关系
- **Scientist 1**: 制定详细研究提案
- **Scientist 2**: 扩展和精炼提案
- **Critic**: 进行审查并建议改进
- **Planner**: 制定详细执行计划
- **Assistant**: 检查假设新颖性

---

### 3.3 阶段三：试验搭建 (Experiment)

| 项目 | GitHub | 实验设计 | 代码生成 | 执行环境 |
|------|--------|---------|---------|---------|
| **AI Scientist v2** | [SakanaAI/AI-Scientist-v2](https://github.com/SakanaAI/AI-Scientist-v2) | 树搜索探索假设空间 | 全自主 | Docker + CUDA |
| **NanoResearch** | [OpenRaiser/NanoResearch](https://github.com/OpenRaiser/NanoResearch) | 结构化蓝图 (数据集/基线/指标/消融) | 完整可运行项目 | GPU/SLURM |
| **Sibyl** | [Sibyl-Research-Team/AutoResearch-SibylSystem](https://github.com/Sibyl-Research-Team/AutoResearch-SibylSystem) | 任务依赖图 | GPU 远程执行 | SSH MCP |
| **AutoR** | [AutoX-AI-Labs/AutoR](https://github.com/AutoX-AI-Labs/AutoR) | 人工审批的 Study Design | 可执行脚本 | 本地 |
| **Nano-Scientist** | [AI4Scientist/nano-scientist](https://github.com/AI4Scientist/nano-scientist) | Claim-driven 实验路线图 | 迭代精炼 | 本地/远程/Modal |
| **ChemCrow** | [ur-whitelab/chemcrow](https://github.com/ur-whitelab/chemcrow) | 合成路线规划 | 化学协议 (非代码) | 化学工具链 |
| **Coscientist** | (CMU, Nature 2023) | 自主实验设计 | 协议 + 机器人控制 | 实验室硬件 |

**AI Scientist v2 的实验流程**:
```
研究主题 (Markdown)
    ↓
[Ideation Agent] → 头脑风暴 + 精炼想法
    ↓
[Novelty Check] → Semantic Scholar 新颖性检查
    ↓
[Experiment Manager] → 渐进式树搜索探索实验路径
    ↓
[Code Generator] → 生成 experiment.py (PyTorch)
    ↓
[Sandboxed Execution] → Docker 内自主执行
    ↓
[Plot Generator] → 结果可视化
    ↓
[Paper Writer] → 生成完整 LaTeX 论文
    ↓
[Reviewer] → LLM 同行评审
```

**Sibyl 的 PIVOT 机制**:
```
想法生成 → 实验规划 → 试点实验 → 全量实验
                                        ↓
                               结果不满意？
                                        ↓
                            [PIVOT] ← 回到想法生成 (最多 6 轮)
```

**关键启示**:
- **模板 + 自主代码生成**是实验自动化的关键模式
- **树搜索**比线性探索更有效 (AI Scientist v2)
- **PIVOT/回滚机制**确保实验质量 (Sibyl)
- **人机协作模式** (AutoR) 适合需要领域判断的实验

---

### 3.4 阶段四：论文写作 (Writing)

| 项目 | GitHub | 写作能力 | LaTeX | 引文管理 |
|------|--------|---------|-------|---------|
| **AI Scientist v2** | [SakanaAI/AI-Scientist-v2](https://github.com/SakanaAI/AI-Scientist-v2) | 全论文生成 | ✅ pdflatex | Semantic Scholar |
| **AutoResearchClaw** | [aiming-lab/AutoResearchClaw](https://github.com/aiming-lab/AutoResearchClaw) | 分章节撰写 (5000-6500 字) | ✅ 会议模板 | 4 层验证 |
| **PaperForge** | [QJHWC/PaperForge](https://github.com/QJHWC/PaperForge) | 端到端写作 | ✅ IEEE/CJC 模板 | BibTeX/OpenAlex |
| **PaperOrchestra** | [google-research/paper-orchestra](https://github.com/google-research/paper-orchestra) | 多 Agent 协作写作 | ✅ 会议模板 | 自动化 |
| **Auto-Academic-Paper** | [keithligh/Auto-Academic-Paper](https://github.com/keithligh/Auto-Academic-Paper) | 6 阶段写作 | ✅ + TikZ | 2 层验证 |
| **paper-agent** | [andyshen1121/paper-agent](https://github.com/andyshen1121/paper-agent) | 论文全流程 | ❌ .docx | Semantic Scholar/CrossRef |
| **GPT-Academic** | [binary-husky/gpt_academic](https://github.com/binary-husky/gpt_academic) (70.9k ⭐) | 润色/翻译/校对 | 辅助 | Google Scholar |
| **Econ Writing Skill** | [hanlulong/econ-writing-skill](https://github.com/hanlulong/econ-writing-skill) | Agent Skill 文件 | 指导 | 完整性检查 |

**Auto-Academic-Paper 的 6 阶段写作**:
1. **Strategist** — 规划论文结构
2. **Librarian** — 文献检索
3. **Thinker** — 草稿撰写
4. **Peer Reviewer** — 验证
5. **Rewriter** — 综合修改
6. **Editor** — 引文格式化

**AutoResearchClaw 的 4 层引文验证**:
```
引文来源 → [1] arXiv ID 验证
         → [2] DOI 验证 (CrossRef/DataCite)
         → [3] Semantic Scholar 标题匹配
         → [4] LLM 相关性评分
         → 伪造引文自动移除
```

**关键启示**:
- **分章节独立写作**比一次性生成更可控
- **引文验证**是防止幻觉的关键环节
- **LaTeX 模板化**确保输出格式正确
- **Agent Skill 文件** (Econ Writing Skill) 是一种轻量级知识注入模式

---

## 四、多 Agent 编排框架

> 这些框架提供了构建科研 Agent 工作流的基础设施。

### 4.1 框架对比

| 框架 | GitHub | ⭐ | 编排模式 | 科研适用性 |
|------|--------|---|---------|-----------|
| **CrewAI** | [crewAIInc/crewAI](https://github.com/crewAIInc/crewAI) | 54k | 角色-based (Sequential/Hierarchical) | ⭐⭐⭐⭐⭐ 研究 Crew 模板 |
| **AutoGen** | [microsoft/autogen](https://github.com/microsoft/autogen) | 59k | 多 Agent 对话 (GroupChat) | ⭐⭐⭐⭐ 研究助手模式 |
| **LangGraph** | [langchain-ai/langgraph](https://github.com/langchain-ai/langgraph) | 35k | 图工作流 (StateGraph) | ⭐⭐⭐⭐ 深度研究循环 |
| **MetaGPT** | [geekan/MetaGPT](https://github.com/geekan/MetaGPT) | 69k | SOP 驱动 (公司模拟) | ⭐⭐⭐ 可适配 |
| **DSPy** | [stanfordnlp/dspy](https://github.com/stanfordnlp/dspy) | — | 声明式 LM 编程 | ⭐⭐⭐ 可优化管道 |

### 4.2 CrewAI 科研 Crew 示例

```yaml
# 研究写作 Crew 配置
agents:
  - role: "Senior Researcher"
    goal: "Gather comprehensive sources on the research topic"
    tools: [SerperDevTool, WebsiteSearchTool]
    
  - role: "Data Analyst"
    goal: "Synthesize and evaluate research findings"
    tools: [FileReadTool, CSVTool]
    
  - role: "Report Writer"
    goal: "Produce structured academic document"
    tools: [FileWriterTool]
    
  - role: "Quality Reviewer"
    goal: "Critique for accuracy and coherence"
    tools: [FileReadTool]

process: sequential  # or hierarchical
```

### 4.3 LangGraph 深度研究工作流

```python
from langgraph.graph import StateGraph

# 定义状态
class ResearchState(TypedDict):
    query: str
    sub_questions: list[str]
    sources: list[dict]
    synthesis: str
    draft: str
    review: str

# 构建图
graph = StateGraph(ResearchState)
graph.add_node("planner", planner_agent)
graph.add_node("searcher", search_agent)
graph.add_node("synthesizer", synthesis_agent)
graph.add_node("writer", writing_agent)
graph.add_node("reviewer", review_agent)

# 条件路由
graph.add_conditional_edges("reviewer", {
    "pass": END,
    "revise": "writer"  # 循环修改
})
```

### 4.4 7 种架构模式

| 模式 | 描述 | 代表项目 |
|------|------|---------|
| **Planner-Executor** | 规划 Agent 分解任务，执行 Agent 并行完成 | GPT-Researcher, STORM |
| **Phase-Based Pipeline** | 顺序阶段，每阶段不同 Agent 角色 | ChatDev, AI Scientist, MetaGPT |
| **Conversational/Debate** | 多 Agent 讨论辩论提升推理 | AutoGen GroupChat, SciAgents |
| **Graph-Based Workflow** | Agent 为有向图节点，条件路由 | LangGraph |
| **Handoff-Based** | Agent 动态转移控制权 | OpenAI Swarm, Agency Swarm |
| **SOP-Driven** | 标准化操作流程编码领域知识 | MetaGPT |
| **Optimizable Pipeline** | 声明式规范可自动优化 | DSPy |

---

## 五、领域专用科研 Agent

### 5.1 化学领域

| 项目 | GitHub | 核心能力 |
|------|--------|---------|
| **ChemCrow** | [ur-whitelab/chemcrow](https://github.com/ur-whitelab/chemcrow) | 18 个化学工具 — 分子查找/反应搜索/合成规划/安全检查 |
| **Coscientist** | (CMU, Nature 2023) | GPT-4 + 机器人实验室 — 自主设计/规划/执行化学实验 |

### 5.2 生物/医学领域

| 项目 | GitHub | 核心能力 |
|------|--------|---------|
| **Medea** | [mims-harvard/Medea](https://github.com/mims-harvard/Medea) | 单细胞数据分析 + 多 Agent 辩论 + 生物背景验证 |
| **BioAgents** | [bio-xyz/BioAgents](https://github.com/bio-xyz/BioAgents) | 迭代假设驱动调查 + 文献综述 + 数据分析 |
| **CRISPR-GPT** | — | 基因编辑实验自动化 |

### 5.3 ML/AI 领域

| 项目 | GitHub | 核心能力 |
|------|--------|---------|
| **AI Scientist** | [SakanaAI/AI-Scientist](https://github.com/SakanaAI/AI-Scientist) | 端到端 ML 研究自动化 |
| **NanoResearch** | [OpenRaiser/NanoResearch](https://github.com/OpenRaiser/NanoResearch) | 9 阶段 ML 实验流水线 |
| **The Station** | [dualverse-ai/station](https://github.com/dualverse-ai/station) | 开放世界多 Agent 科学生态系统 |

### 5.4 跨学科技能库

| 项目 | GitHub | 核心能力 |
|------|--------|---------|
| **Scientific Agent Skills** | [K-Dense-AI/scientific-agent-skills](https://github.com/K-Dense-AI/scientific-agent-skills) | 147 个预构建技能 — 实验设计 (DOE)/假设生成/78 个公共数据库 |
| **SciAtlas** | [zjunlp/SciAtlas](https://github.com/zjunlp/SciAtlas) | 大规模科学知识图谱 — 论文/作者/机构/关键词/引文 |

---

## 六、完整的 Pipeline Stage 覆盖矩阵

| 项目 | ① 检索 | ② 综述 | ③ 试验设计 | ③ 代码执行 | ④ 论文写作 | ⑤ 自动评审 |
|------|--------|--------|-----------|-----------|-----------|-----------|
| **AI Scientist v2** | ✅ | ✅ | ✅ | ✅ | ✅ LaTeX | ✅ |
| **AutoResearchClaw** | ✅ | ✅ | ✅ | ✅ | ✅ LaTeX | ✅ |
| **NanoResearch** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Sibyl** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **AutoR** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **PaperForge** | ✅ | ✅ | ✅ | ✅ | ✅ LaTeX | ✅ |
| **FAROS** | ✅ | ✅ | 部分 | 脚手架 | ✅ LaTeX | ✅ |
| **PaperOrchestra** | ✅ | ✅ | — | — | ✅ LaTeX | — |
| **STORM** | ✅ | ✅ | — | — | ✅ 文章 | — |
| **GPT-Researcher** | ✅ | ✅ | — | — | ✅ 报告 | — |
| **PaperQA2** | ✅ | ✅ | — | — | — | — |
| **SciAgents** | ✅ | ✅ | 部分 | — | ✅ | ✅ |
| **GPT-Academic** | 部分 | — | — | — | ✅ 润色 | 部分 |
| **ASReview** | — | ✅ 筛选 | — | — | — | — |
| **ChemCrow** | 部分 | — | ✅ | 协议 | — | — |
| **Coscientist** | ✅ | — | ✅ | ✅ 机器人 | — | — |

---

## 七、对 AI Nexus Assistant 的启示

### 7.1 可集成的 Agent 工作流

基于调研结果，AI Nexus Assistant 可以参考以下模式构建科研 Agent 工作流：

```
┌─────────────────────────────────────────────────────────┐
│                   AI Nexus Assistant                     │
│                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐  │
│  │ 文献搜索  │  │ 知识库    │  │ 实验管理  │  │ AI Chat│  │
│  │ (现有)    │  │ (现有)    │  │ (现有)    │  │ (现有)  │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └───┬────┘  │
│       │              │              │             │       │
│       └──────────────┴──────────────┴─────────────┘       │
│                          ↓                                │
│              ┌──────────────────────┐                     │
│              │  Research Agent Hub  │  ← 新增模块          │
│              │                      │                     │
│              │  ① 检索 Agent        │  参考 GPT-Researcher │
│              │  ② 综述 Agent        │  参考 STORM          │
│              │  ③ 实验设计 Agent    │  参考 AI Scientist   │
│              │  ④ 论文写作 Agent    │  参考 AutoResearchClaw│
│              │  ⑤ 评审 Agent        │  参考 PaperQA2       │
│              └──────────────────────┘                     │
└─────────────────────────────────────────────────────────┘
```

### 7.2 优先级建议

| 优先级 | 功能 | 参考项目 | 预估工作量 | 说明 |
|--------|------|---------|-----------|------|
| **P0** | 文献综述 Agent | STORM, GPT-Researcher | 1-2 周 | 多源检索 + 综合报告生成，复用现有搜索能力 |
| **P0** | 论文写作 Agent | AutoResearchClaw | 2-3 周 | 分章节撰写 + LaTeX 输出 + 引文管理 |
| **P1** | 实验设计 Agent | AI Scientist | 3-4 周 | 假设生成 + 实验规划 + 代码生成 |
| **P1** | 引文验证 | AutoResearchClaw 4 层验证 | 1 周 | 防止引文幻觉 |
| **P2** | 自动评审 | AI Scientist | 1-2 周 | LLM 同行评审 + 改进建议 |
| **P2** | 多 Agent 辩论 | SciAgents, Sibyl | 2-3 周 | 多视角推理提升质量 |

### 7.3 架构建议

**推荐采用 CrewAI + LangGraph 混合架构**:

```python
# 研究工作流定义
research_workflow = {
    "retrieval": CrewAgent(
        role="Literature Researcher",
        tools=[SemanticScholarTool, ArxivTool, WebSearchTool],
        llm="claude-sonnet"
    ),
    "review": CrewAgent(
        role="Literature Reviewer", 
        tools=[PDFParserTool, CitationTool],
        llm="claude-sonnet"
    ),
    "experiment": CrewAgent(
        role="Experiment Designer",
        tools=[CodeGeneratorTool, PythonExecutorTool],
        llm="claude-opus"  # 复杂任务用更强模型
    ),
    "writing": CrewAgent(
        role="Paper Writer",
        tools=[LaTeXTool, CitationFormatterTool],
        llm="claude-sonnet"
    ),
    "review_agent": CrewAgent(
        role="Peer Reviewer",
        tools=[FactCheckTool, NoveltyCheckTool],
        llm="claude-opus"
    )
}

# 使用 LangGraph 编排
workflow = StateGraph(ResearchState)
workflow.add_node("retrieve", retrieval_crew)
workflow.add_node("review_lit", review_crew)
workflow.add_node("design_exp", experiment_crew)
workflow.add_node("write", writing_crew)
workflow.add_node("peer_review", review_agent)

# 条件路由：评审不通过则返回修改
workflow.add_conditional_edges("peer_review", {
    "pass": END,
    "revise": "write"
})
```

### 7.4 关键技术决策

| 决策点 | 推荐方案 | 参考 |
|--------|---------|------|
| LLM 抽象层 | LiteLLM (100+ Provider) | LiteLLM |
| 学术数据源 | Semantic Scholar + OpenAlex + arXiv | PaperQA2, AI Scientist |
| 引文验证 | 4 层验证 (ID → DOI → 标题匹配 → LLM 评分) | AutoResearchClaw |
| 实验执行 | 沙箱化 Docker + 可选 GPU | AI Scientist |
| 论文输出 | LaTeX + 多会议模板 | PaperForge, FAROS |
| Agent 编排 | CrewAI (角色) + LangGraph (流程) | CrewAI, LangGraph |
| 人工介入 | 6 种干预模式 | AutoResearchClaw |

---

## 八、参考资源

### 核心参考论文

- **The AI Scientist**: "Towards Fully Automated Open-Ended Scientific Discovery" (Sakana AI, 2024)
- **STORM**: "Assisting in Writing Wikipedia-like Articles from Scratch with LLMs" (Stanford, NAACL 2024)
- **SciAgents**: "Scientific Discovery via Knowledge Graphs" (MIT, 2024)
- **Coscientist**: "Autonomous chemical research with large language models" (CMU, Nature 2023)
- **ChemCrow**: "ChemCrow: Augmenting large-language models with chemistry tools" (ACS 2023)

### 学术综述

- [awesome-ai-auto-research](https://github.com/worldbench/awesome-ai-auto-research) — AI 自动研究项目全景
- [awesome-ai-scientific-research](https://github.com/ysymyth/awesome-ai-scientific-research) — AI 科研工具列表

### 商业工具对比

| 工具 | 定位 | 核心优势 |
|------|------|---------|
| **Jenni AI** | 全周期论文写作 | 2600+ 引文格式, 6M+ 用户 |
| **Writefull** | 语言润色 | TeXGPT Overleaf 集成 |
| **Elicit** | 文献综述 | 200M+ 论文语义搜索 |
| **Consensus** | 科学搜索引擎 | 证据支持的答案 |
| **scite.ai** | 引文分析 | 支持/反对/提及分类 |

---

> 本文档基于 4 路并行搜索，覆盖 30+ 开源项目和 7 种架构模式，聚焦「检索 → 综述 → 试验搭建 → 论文写作」全流程。
