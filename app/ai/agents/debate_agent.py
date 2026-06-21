"""多 Agent 辩论系统

参考 SciAgents + Sibyl 的多 Agent 辩论模式。
通过多个 Agent 从不同角度讨论，提升推理质量。
"""

import asyncio
import json
from typing import Optional
from .workflow import WorkflowEngine, ResearchWorkflow, WorkflowStep, StepType


DEBATE_SYSTEM_PROMPT = """你是一位资深的学术研究者，参与一场关于研究主题的学术讨论。

你的角色是：{role}

讨论规则：
1. 基于事实和逻辑进行论证
2. 尊重其他参与者的观点
3. 提出建设性的质疑和建议
4. 使用学术语言和引用支持观点

请从你的专业角度出发，对以下主题发表见解："""


PERSPECTIVES = [
    {
        "role": "方法论专家",
        "focus": "从研究方法论角度分析，评估研究设计的科学性和严谨性。",
    },
    {
        "role": "领域专家",
        "focus": "从领域知识角度分析，评估研究的创新性和贡献。",
    },
    {
        "role": "批判性思维者",
        "focus": "从批判性角度分析，指出潜在的问题和局限性。",
    },
    {
        "role": "实践应用者",
        "focus": "从实际应用角度分析，评估研究的实用价值和可行性。",
    },
]


class DebateAgent(WorkflowEngine):
    """多 Agent 辩论系统"""

    async def _execute_step(self, workflow: ResearchWorkflow, step: WorkflowStep) -> dict:
        if step.step_type == StepType.RETRIEVAL:
            return await self._execute_retrieval(workflow, step)
        elif step.step_type == StepType.REVIEW:
            return await self._execute_debate(workflow, step)
        else:
            raise ValueError(f"未知步骤类型: {step.step_type}")

    async def _execute_retrieval(self, workflow: ResearchWorkflow, step: WorkflowStep) -> dict:
        """执行文献检索"""
        query = workflow.config.get("query", workflow.title)
        from app.search.engine import UnifiedSearchEngine
        engine = UnifiedSearchEngine()
        papers = engine.search(query, max_results=10, enrich=True)

        paper_list = []
        for p in papers[:10]:
            paper_list.append({
                "title": p.title,
                "authors": p.authors,
                "year": p.year,
                "abstract": p.abstract[:200] if p.abstract else "",
            })

        return {"papers": paper_list, "total": len(paper_list)}

    async def _execute_debate(self, workflow: ResearchWorkflow, step: WorkflowStep) -> dict:
        """执行多 Agent 辩论"""
        config = workflow.config
        topic = config.get("query", workflow.title)
        model_id = config.get("model_id")
        rounds = config.get("rounds", 2)

        # 获取检索结果
        retrieval_step = None
        for s in workflow.steps:
            if s.step_type == StepType.RETRIEVAL and s.output_data:
                retrieval_step = s
                break

        papers = retrieval_step.output_data.get("papers", []) if retrieval_step else []

        # 构建上下文
        papers_context = ""
        if papers:
            papers_context = "\n\n相关文献:\n" + "\n".join(
                f"- {p['title']} ({p['year']}): {p.get('abstract', '')[:100]}"
                for p in papers[:5]
            )

        # 多轮辩论
        debate_history = []
        total_tokens = 0

        for round_num in range(rounds):
            round_results = []

            # 并发执行多个视角的分析
            tasks = []
            for perspective in PERSPECTIVES:
                task = self._analyze_perspective(
                    topic, perspective, papers_context, debate_history, model_id
                )
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    round_results.append({
                        "perspective": PERSPECTIVES[i]["role"],
                        "content": f"分析失败: {result}",
                    })
                else:
                    round_results.append(result)
                    total_tokens += result.get("tokens", 0)

            debate_history.append({
                "round": round_num + 1,
                "perspectives": round_results,
            })

        # 综合分析
        synthesis = await self._synthesize_debate(topic, debate_history, model_id)

        return {
            "debate_history": debate_history,
            "synthesis": synthesis.get("content", ""),
            "topic": topic,
            "total_tokens": total_tokens + synthesis.get("tokens", 0),
        }

    async def _analyze_perspective(self, topic: str, perspective: dict,
                                    papers_context: str, debate_history: list,
                                    model_id: str) -> dict:
        """从特定视角分析"""
        prompt = DEBATE_SYSTEM_PROMPT.format(role=perspective["role"])

        user_prompt = f"""研究主题: {topic}

{perspective['focus']}
{papers_context}

"""

        # 添加历史讨论
        if debate_history:
            user_prompt += "\n\n之前的讨论:\n"
            for round_data in debate_history[-2:]:  # 只取最近 2 轮
                for p in round_data["perspectives"]:
                    user_prompt += f"\n{p['perspective']}: {p['content'][:200]}...\n"

        user_prompt += "\n请从你的专业角度发表见解，字数 300-500 字。"

        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_prompt},
        ]

        result = await asyncio.to_thread(
            self.ai_router.chat, messages, "chat", model_id
        )

        content = result.get("content", "")
        if content.startswith("❌"):
            raise Exception(content)

        return {
            "perspective": perspective["role"],
            "content": content,
            "tokens": result.get("usage", {}).get("total_tokens", 0),
        }

    async def _synthesize_debate(self, topic: str, debate_history: list,
                                  model_id: str) -> dict:
        """综合辩论结果"""
        # 构建辩论摘要
        debate_summary = ""
        for round_data in debate_history:
            debate_summary += f"\n\n第 {round_data['round']} 轮讨论:\n"
            for p in round_data["perspectives"]:
                debate_summary += f"\n{p['perspective']}:\n{p['content']}\n"

        prompt = f"""研究主题: {topic}

以下是多视角讨论的内容:
{debate_summary}

请综合以上讨论，形成一份全面的分析报告，包含：
1. 各视角的主要观点总结
2. 共识和分歧点
3. 研究的优势和局限性
4. 建议的改进方向
5. 最终结论

字数 500-800 字。"""

        messages = [
            {"role": "system", "content": "你是一位学术研究综合分析师，擅长整合多方观点形成全面的分析报告。"},
            {"role": "user", "content": prompt},
        ]

        result = await asyncio.to_thread(
            self.ai_router.chat, messages, "review", model_id
        )

        content = result.get("content", "")
        if content.startswith("❌"):
            raise Exception(content)

        return {
            "content": content,
            "tokens": result.get("usage", {}).get("total_tokens", 0),
        }

    async def run_debate(self, topic: str, model_id: str = None, rounds: int = 2) -> dict:
        """便捷方法：运行多 Agent 辩论"""
        workflow = self.create_workflow(
            workflow_type="debate",
            title=f"多视角讨论: {topic}",
            config={"query": topic, "model_id": model_id, "rounds": rounds},
        )

        workflow.add_step(StepType.RETRIEVAL, "文献检索")
        workflow.add_step(StepType.REVIEW, "多视角辩论")

        result = await self.run_workflow(workflow.id)
        return result
