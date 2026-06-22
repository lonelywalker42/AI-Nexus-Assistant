"""实验设计 Agent

参考 AI Scientist 的假设生成 + 实验规划模式。
"""

import asyncio
import json
from typing import Optional
from .workflow import WorkflowEngine, ResearchWorkflow, WorkflowStep, StepType


EXPERIMENT_SYSTEM_PROMPT = """你是一位资深的科研实验设计专家。你的任务是根据研究主题，设计完整的实验方案。

设计规范：
1. 假设明确、可验证
2. 变量控制清晰
3. 评估指标合理
4. 代码可执行
5. 结果可复现"""

HYPOTHESIS_PROMPT = """请根据研究主题生成 3-5 个可验证的研究假设，每个假设包含：
1. 假设陈述
2. 验证方法
3. 预期结果
4. 创新性说明

输出 JSON 格式:
[
  {
    "id": 1,
    "hypothesis": "...",
    "method": "...",
    "expected_result": "...",
    "novelty": "..."
  }
]"""

EXPERIMENT_PLAN_PROMPT = """请为选定的假设设计详细的实验方案，包含：

1. 实验目标
2. 数据集选择及理由
3. 基线方法 (Baseline)
4. 评估指标
5. 实验步骤（可转化为代码）
6. 预期结果和分析方法

输出 JSON 格式:
{
  "objective": "...",
  "datasets": ["..."],
  "baselines": ["..."],
  "metrics": ["..."],
  "steps": ["..."],
  "analysis_plan": "..."
}"""

CODE_GENERATION_PROMPT = """请根据实验方案生成可执行的 Python 代码骨架，要求：
1. 使用 PyTorch/TensorFlow
2. 包含数据加载、模型定义、训练循环、评估
3. 代码可运行（可能需要修改数据路径）
4. 添加详细注释"""


class ExperimentDesignAgent(WorkflowEngine):
    """实验设计 Agent"""

    async def _execute_step(self, workflow: ResearchWorkflow, step: WorkflowStep) -> dict:
        if step.step_type == StepType.RETRIEVAL:
            return await self._execute_retrieval(workflow, step)
        elif step.step_type == StepType.EXPERIMENT:
            return await self._execute_experiment(workflow, step)
        else:
            raise ValueError(f"未知步骤类型: {step.step_type}")

    async def _execute_retrieval(self, workflow: ResearchWorkflow, step: WorkflowStep) -> dict:
        """执行相关文献检索"""
        query = workflow.config.get("query", workflow.title)
        from app.search.engine import UnifiedSearchEngine
        engine = UnifiedSearchEngine()
        try:
            papers = await asyncio.to_thread(engine.search, query, None, 15, True)
        except Exception as e:
            print(f"[experiment_agent] 搜索异常: {e}", flush=True)
            papers = []

        paper_list = []
        for p in papers[:15]:
            paper_list.append({
                "title": p.title,
                "authors": p.authors,
                "year": p.year,
                "abstract": p.abstract[:200] if p.abstract else "",
            })

        return {"papers": paper_list, "total": len(paper_list)}

    async def _execute_experiment(self, workflow: ResearchWorkflow, step: WorkflowStep) -> dict:
        """执行实验设计"""
        config = workflow.config
        topic = config.get("query", workflow.title)
        model_id = config.get("model_id")
        selected_hypothesis = config.get("selected_hypothesis")

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
                for p in papers[:10]
            )

        # 步骤 1: 生成假设
        hypothesis_prompt = f"""研究主题: {topic}
{papers_context}

{HYPOTHESIS_PROMPT}"""

        messages = [
            {"role": "system", "content": EXPERIMENT_SYSTEM_PROMPT},
            {"role": "user", "content": hypothesis_prompt},
        ]

        hypothesis_result = await asyncio.to_thread(self.ai_router.chat, messages, "chat", model_id)
        hypothesis_text = hypothesis_result.get("content", "")

        # 检查是否返回了错误信息
        if hypothesis_text.startswith("[ERROR]"):
            raise Exception(hypothesis_text)

        # 解析假设
        try:
            hypotheses = json.loads(hypothesis_text)
        except json.JSONDecodeError:
            # 尝试提取 JSON
            import re
            json_match = re.search(r'\[.*\]', hypothesis_text, re.DOTALL)
            if json_match:
                try:
                    hypotheses = json.loads(json_match.group())
                except:
                    hypotheses = [{"id": 1, "hypothesis": hypothesis_text, "method": "", "expected_result": "", "novelty": ""}]
            else:
                hypotheses = [{"id": 1, "hypothesis": hypothesis_text, "method": "", "expected_result": "", "novelty": ""}]

        # 步骤 2: 生成实验方案
        target_hypothesis = selected_hypothesis or hypotheses[0] if hypotheses else {}

        plan_prompt = f"""研究主题: {topic}

选定假设: {json.dumps(target_hypothesis, ensure_ascii=False)}

{EXPERIMENT_PLAN_PROMPT}"""

        messages = [
            {"role": "system", "content": EXPERIMENT_SYSTEM_PROMPT},
            {"role": "user", "content": plan_prompt},
        ]

        plan_result = await asyncio.to_thread(self.ai_router.chat, messages, "chat", model_id)
        plan_text = plan_result.get("content", "")

        # 解析方案
        try:
            experiment_plan = json.loads(plan_text)
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'\{.*\}', plan_text, re.DOTALL)
            if json_match:
                try:
                    experiment_plan = json.loads(json_match.group())
                except:
                    experiment_plan = {"objective": plan_text, "datasets": [], "baselines": [], "metrics": [], "steps": [], "analysis_plan": ""}
            else:
                experiment_plan = {"objective": plan_text, "datasets": [], "baselines": [], "metrics": [], "steps": [], "analysis_plan": ""}

        # 步骤 3: 生成代码骨架
        code_prompt = f"""实验方案: {json.dumps(experiment_plan, ensure_ascii=False)}

{CODE_GENERATION_PROMPT}"""

        messages = [
            {"role": "system", "content": EXPERIMENT_SYSTEM_PROMPT},
            {"role": "user", "content": code_prompt},
        ]

        code_result = await asyncio.to_thread(self.ai_router.chat, messages, "chat", model_id)
        code_content = code_result.get("content", "")

        return {
            "hypotheses": hypotheses,
            "selected_hypothesis": target_hypothesis,
            "experiment_plan": experiment_plan,
            "code_skeleton": code_content,
            "topic": topic,
        }

    async def design_experiment(self, topic: str, model_id: str = None) -> dict:
        """便捷方法：直接设计实验"""
        workflow = self.create_workflow(
            workflow_type="experiment",
            title=f"实验设计: {topic}",
            config={"query": topic, "model_id": model_id},
        )

        workflow.add_step(StepType.RETRIEVAL, "文献检索")
        workflow.add_step(StepType.EXPERIMENT, "实验设计")

        result = await self.run_workflow(workflow.id)
        return result
