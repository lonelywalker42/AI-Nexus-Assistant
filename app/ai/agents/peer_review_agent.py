"""同行评审 Agent

参考 AI Scientist + PaperQA2 的 LLM 同行评审模式。
"""

import asyncio
import json
from typing import Optional
from .workflow import WorkflowEngine, ResearchWorkflow, WorkflowStep, StepType


PEER_REVIEW_SYSTEM_PROMPT = """你是一位资深的学术审稿人。你的任务是对学术论文/文档进行严格的同行评审。

评审标准：
1. 创新性 (Novelty): 是否提出了新的观点、方法或发现？
2. 严谨性 (Rigor): 研究方法是否科学严谨？
3. 完整性 (Completeness): 论文结构是否完整，论证是否充分？
4. 可复现性 (Reproducibility): 实验是否可复现？
5. 表达质量 (Clarity): 语言表达是否清晰准确？

评分标准 (1-10):
- 1-3: 严重问题，建议拒稿
- 4-5: 较多问题，需要重大修改
- 6-7: 一般，需要修改
- 8-9: 良好，小修后可接受
- 10: 优秀，直接接受"""


REVIEW_PROMPT = """请对以下文档进行同行评审：

标题: {title}

内容:
{content}

请提供结构化评审报告，包含：

1. 总体评价 (1-2 句话)
2. 各维度评分 (1-10):
   - 创新性: X/10
   - 严谨性: X/10
   - 完整性: X/10
   - 可复现性: X/10
   - 表达质量: X/10
3. 主要优点 (3-5 条)
4. 主要问题 (3-5 条)
5. 具体修改建议 (按优先级排序)
6. 最终建议: Accept / Minor Revision / Major Revision / Reject

输出 JSON 格式:
{{
  "summary": "...",
  "scores": {{
    "novelty": X,
    "rigor": X,
    "completeness": X,
    "reproducibility": X,
    "clarity": X,
    "overall": X
  }},
  "strengths": ["..."],
  "weaknesses": ["..."],
  "suggestions": ["..."],
  "recommendation": "Accept|Minor Revision|Major Revision|Reject"
}}"""


class PeerReviewAgent(WorkflowEngine):
    """同行评审 Agent"""

    async def _execute_step(self, workflow: ResearchWorkflow, step: WorkflowStep) -> dict:
        if step.step_type == StepType.PEER_REVIEW:
            return await self._execute_review(workflow, step)
        else:
            raise ValueError(f"未知步骤类型: {step.step_type}")

    async def _execute_review(self, workflow: ResearchWorkflow, step: WorkflowStep) -> dict:
        """执行同行评审"""
        config = workflow.config
        title = config.get("title", workflow.title)
        content = config.get("content", "")
        model_id = config.get("model_id")

        if not content:
            return {"error": "未提供评审内容"}

        # 限制内容长度
        if len(content) > 10000:
            content = content[:10000] + "\n\n[内容已截断...]"

        prompt = REVIEW_PROMPT.format(title=title, content=content)

        messages = [
            {"role": "system", "content": PEER_REVIEW_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        result = await asyncio.to_thread(self.ai_router.chat, messages, "review", model_id)
        review_text = result.get("content", "")

        # 检查是否返回了错误信息
        if review_text.startswith("❌"):
            raise Exception(review_text)

        # 解析评审结果
        try:
            review_data = json.loads(review_text)
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'\{.*\}', review_text, re.DOTALL)
            if json_match:
                try:
                    review_data = json.loads(json_match.group())
                except:
                    review_data = {
                        "summary": review_text,
                        "scores": {"novelty": 5, "rigor": 5, "completeness": 5, "reproducibility": 5, "clarity": 5, "overall": 5},
                        "strengths": [],
                        "weaknesses": [],
                        "suggestions": [],
                        "recommendation": "Major Revision",
                    }
            else:
                review_data = {
                    "summary": review_text,
                    "scores": {"novelty": 5, "rigor": 5, "completeness": 5, "reproducibility": 5, "clarity": 5, "overall": 5},
                    "strengths": [],
                    "weaknesses": [],
                    "suggestions": [],
                    "recommendation": "Major Revision",
                }

        return {
            "review": review_data,
            "title": title,
        }

    async def review_document(self, title: str, content: str, model_id: str = None) -> dict:
        """便捷方法：直接评审文档"""
        workflow = self.create_workflow(
            workflow_type="review",
            title=f"同行评审: {title}",
            config={"title": title, "content": content, "model_id": model_id},
        )

        workflow.add_step(StepType.PEER_REVIEW, "同行评审")

        result = await self.run_workflow(workflow.id)
        return result
