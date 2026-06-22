"""论文写作 Agent

参考 AutoResearchClaw 的分章节撰写模式。
"""

import asyncio
import json
from typing import Optional
from .workflow import WorkflowEngine, ResearchWorkflow, WorkflowStep, StepType


WRITING_SYSTEM_PROMPT = """你是一位资深的学术论文写作专家。你的任务是根据用户提供的研究主题和大纲，撰写高质量的学术论文。

写作规范：
1. 使用严谨的学术语言
2. 逻辑清晰，论证充分
3. 引用规范，使用 [1] [2] 格式
4. 每个章节独立成段，结构完整
5. 使用 Markdown 格式输出"""

CHAPTER_PROMPTS = {
    "abstract": """请撰写论文摘要，要求：
- 200-300 字
- 包含研究背景、方法、主要结果、结论
- 简洁精炼，突出创新点""",

    "introduction": """请撰写论文引言，要求：
- 研究背景和意义
- 国内外研究现状综述
- 现有研究的不足
- 本文的研究目标和贡献
- 论文结构说明""",

    "methodology": """请撰写方法论章节，要求：
- 研究方法的选择依据
- 详细的实验/研究设计
- 数据收集和处理方法
- 评估指标和方法""",

    "results": """请撰写结果章节，要求：
- 客观呈现实验/研究结果
- 使用图表辅助说明
- 数据分析和统计结果
- 与预期的对比""",

    "discussion": """请撰写讨论章节，要求：
- 结果的深入分析和解释
- 与已有研究的比较
- 研究的局限性
- 未来研究方向""",

    "conclusion": """请撰写结论章节，要求：
- 总结主要发现
- 强调研究贡献
- 实际应用价值
- 展望未来工作""",
}


class PaperWritingAgent(WorkflowEngine):
    """论文写作 Agent"""

    async def _execute_step(self, workflow: ResearchWorkflow, step: WorkflowStep) -> dict:
        if step.step_type == StepType.WRITING:
            return await self._execute_writing(workflow, step)
        else:
            raise ValueError(f"未知步骤类型: {step.step_type}")

    async def _execute_writing(self, workflow: ResearchWorkflow, step: WorkflowStep) -> dict:
        """执行论文写作"""
        config = workflow.config
        topic = config.get("topic", workflow.title)
        chapters = config.get("chapters", ["abstract", "introduction", "methodology", "results", "discussion", "conclusion"])
        model_id = config.get("model_id")
        references = config.get("references", [])
        outline = config.get("outline", "")

        # 构建参考文献文本
        refs_text = ""
        if references:
            refs_text = "\n\n参考文献:\n" + "\n".join(
                f"[{i+1}] {r}" for i, r in enumerate(references[:30])
            )

        # 逐章节撰写
        chapter_contents = {}
        total_tokens = 0

        for chapter in chapters:
            if chapter not in CHAPTER_PROMPTS:
                continue

            chapter_prompt = CHAPTER_PROMPTS[chapter]

            user_prompt = f"""研究主题: {topic}

{f'论文大纲: {outline}' if outline else ''}

{chapter_prompt}

{refs_text}

请直接输出该章节的内容，不要包含章节标题以外的说明文字。"""

            messages = [
                {"role": "system", "content": WRITING_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ]

            result = await asyncio.to_thread(self.ai_router.chat, messages, "writing", model_id)
            content = result.get("content", "")
            # 检查是否返回了错误信息
            if content.startswith("[ERROR]"):
                raise Exception(content)
            chapter_contents[chapter] = content

            # 统计 token
            usage = result.get("usage", {})
            total_tokens += usage.get("total_tokens", 0)

        # 组装完整论文
        full_paper = self._assemble_paper(topic, chapter_contents)

        return {
            "paper_content": full_paper,
            "chapters": chapter_contents,
            "topic": topic,
            "token_usage": total_tokens,
        }

    def _assemble_paper(self, topic: str, chapters: dict) -> str:
        """组装完整论文"""
        sections = []

        # 标题
        sections.append(f"# {topic}\n")

        # 按顺序组装章节
        chapter_order = ["abstract", "introduction", "methodology", "results", "discussion", "conclusion"]
        chapter_titles = {
            "abstract": "摘要",
            "introduction": "引言",
            "methodology": "方法论",
            "results": "结果",
            "discussion": "讨论",
            "conclusion": "结论",
        }

        for ch in chapter_order:
            if ch in chapters:
                title = chapter_titles.get(ch, ch)
                sections.append(f"## {title}\n\n{chapters[ch]}")

        return "\n\n".join(sections)

    async def write_paper(self, topic: str, chapters: list = None, model_id: str = None,
                          references: list = None, outline: str = None) -> dict:
        """便捷方法：直接撰写论文"""
        workflow = self.create_workflow(
            workflow_type="writing",
            title=f"论文写作: {topic}",
            config={
                "topic": topic,
                "chapters": chapters or ["abstract", "introduction", "methodology", "results", "discussion", "conclusion"],
                "model_id": model_id,
                "references": references or [],
                "outline": outline or "",
            },
        )

        workflow.add_step(StepType.WRITING, "论文撰写")

        result = await self.run_workflow(workflow.id)
        return result
