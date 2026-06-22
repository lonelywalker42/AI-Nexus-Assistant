"""文献综述 Agent

参考 GPT-Researcher + STORM 的多源检索 + 综合报告生成模式。
"""

import asyncio
import json
from typing import Optional
from .workflow import WorkflowEngine, ResearchWorkflow, WorkflowStep, StepType


REVIEW_SYSTEM_PROMPT = """你是一位资深的学术研究助理，擅长文献综述。你的任务是：

1. 根据用户提供的研究主题，进行全面的文献检索和综述
2. 从多个角度分析研究现状（方法论、应用场景、技术路线）
3. 识别研究空白和未来方向
4. 使用规范的学术引用格式

输出要求：
- 使用 Markdown 格式
- 包含引言、主体（按主题分节）、结论、参考文献
- 引用时使用 [1] [2] 等编号格式
- 保持客观、严谨的学术风格"""


class LiteratureReviewAgent(WorkflowEngine):
    """文献综述 Agent"""

    async def _execute_step(self, workflow: ResearchWorkflow, step: WorkflowStep) -> dict:
        if step.step_type == StepType.RETRIEVAL:
            return await self._execute_retrieval(workflow, step)
        elif step.step_type == StepType.REVIEW:
            return await self._execute_review(workflow, step)
        else:
            raise ValueError(f"未知步骤类型: {step.step_type}")

    async def _execute_retrieval(self, workflow: ResearchWorkflow, step: WorkflowStep) -> dict:
        """执行文献检索"""
        query = workflow.config.get("query", workflow.title)
        max_results = workflow.config.get("max_results", 30)

        # 使用搜索引擎（在线程池中执行，避免阻塞事件循环）
        from app.search.engine import UnifiedSearchEngine
        engine = UnifiedSearchEngine()
        try:
            papers = await asyncio.to_thread(engine.search, query, None, max_results, True)
        except Exception as e:
            print(f"[review_agent] 搜索异常: {e}", flush=True)
            papers = []

        # 转换为字典格式
        paper_list = []
        for p in papers[:max_results]:
            paper_list.append({
                "title": p.title,
                "authors": p.authors,
                "year": p.year,
                "doi": p.doi,
                "abstract": p.abstract,
                "journal": p.journal,
                "source": p.source,
                "url": p.url,
                "citation": p.citation,
            })

        return {
            "papers": paper_list,
            "total": len(paper_list),
            "query": query,
        }

    async def _execute_review(self, workflow: ResearchWorkflow, step: WorkflowStep) -> dict:
        """执行文献综述生成"""
        # 获取检索结果
        retrieval_step = None
        for s in workflow.steps:
            if s.step_type == StepType.RETRIEVAL and s.output_data:
                retrieval_step = s
                break

        papers = retrieval_step.output_data.get("papers", []) if retrieval_step else []
        query = workflow.config.get("query", workflow.title)

        # 构建 prompt
        paper_summaries = []
        for i, p in enumerate(papers[:20], 1):
            summary = f"[{i}] {p.get('title', '')} ({p.get('year', '')})"
            if p.get('authors'):
                authors = p['authors'][:3]
                summary += f" - {', '.join(authors)}"
            if p.get('abstract'):
                summary += f"\n摘要: {p['abstract'][:200]}..."
            paper_summaries.append(summary)

        papers_text = "\n\n".join(paper_summaries)

        user_prompt = f"""研究主题: {query}

检索到的相关文献:
{papers_text}

请基于以上文献，撰写一份全面的文献综述。要求：
1. 包含引言、主体（按主题分节）、结论
2. 识别研究现状、主要方法、应用领域
3. 指出研究空白和未来方向
4. 使用 [1] [2] 等引用格式
5. 字数 2000-3000 字"""

        # 调用 LLM
        messages = [
            {"role": "system", "content": REVIEW_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        model_id = workflow.config.get("model_id")
        try:
            result = await asyncio.to_thread(self.ai_router.chat, messages, "review", model_id)
        except Exception as e:
            raise Exception(f"AI 调用失败: {e}")

        content = result.get("content", "")
        # 检查是否返回了错误信息
        if content.startswith("[ERROR]"):
            raise Exception(content)

        return {
            "review_content": content,
            "paper_count": len(papers),
            "query": query,
        }

    async def generate_review(self, query: str, model_id: str = None) -> dict:
        """便捷方法：直接生成综述"""
        workflow = self.create_workflow(
            workflow_type="review",
            title=f"文献综述: {query}",
            config={"query": query, "model_id": model_id},
        )

        # 添加步骤
        workflow.add_step(StepType.RETRIEVAL, "文献检索")
        workflow.add_step(StepType.REVIEW, "综述生成")

        # 执行
        result = await self.run_workflow(workflow.id)
        return result
