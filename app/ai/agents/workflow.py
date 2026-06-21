"""科研 Agent 工作流引擎

参考 CrewAI + LangGraph 的 Phase-based Pipeline 模式。
"""

import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional


class WorkflowStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepType(str, Enum):
    RETRIEVAL = "retrieval"
    REVIEW = "review"
    EXPERIMENT = "experiment"
    WRITING = "writing"
    PEER_REVIEW = "peer_review"


@dataclass
class WorkflowStep:
    """工作流步骤"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    step_type: StepType = StepType.RETRIEVAL
    name: str = ""
    status: WorkflowStatus = WorkflowStatus.PENDING
    input_data: dict = field(default_factory=dict)
    output_data: dict = field(default_factory=dict)
    agent_model: str = ""
    token_usage: int = 0
    duration_ms: int = 0
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "step_type": self.step_type.value,
            "name": self.name,
            "status": self.status.value,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "agent_model": self.agent_model,
            "token_usage": self.token_usage,
            "duration_ms": self.duration_ms,
            "error": self.error,
        }


@dataclass
class ResearchWorkflow:
    """科研工作流"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    workflow_type: str = "review"  # review | writing | experiment | full
    status: WorkflowStatus = WorkflowStatus.PENDING
    config: dict = field(default_factory=dict)
    steps: list[WorkflowStep] = field(default_factory=list)
    result: dict = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "workflow_type": self.workflow_type,
            "status": self.status.value,
            "config": self.config,
            "steps": [s.to_dict() for s in self.steps],
            "result": self.result,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def add_step(self, step_type: StepType, name: str) -> WorkflowStep:
        step = WorkflowStep(step_type=step_type, name=name)
        self.steps.append(step)
        return step

    def get_current_step(self) -> Optional[WorkflowStep]:
        for step in self.steps:
            if step.status in (WorkflowStatus.PENDING, WorkflowStatus.RUNNING):
                return step
        return None

    def complete_step(self, step_id: str, output_data: dict, token_usage: int = 0):
        for step in self.steps:
            if step.id == step_id:
                step.status = WorkflowStatus.COMPLETED
                step.output_data = output_data
                step.token_usage = token_usage
                step.duration_ms = int((time.time() - self.updated_at) * 1000)
                break
        self.updated_at = time.time()

    def fail_step(self, step_id: str, error: str):
        for step in self.steps:
            if step.id == step_id:
                step.status = WorkflowStatus.FAILED
                step.error = error
                break
        self.status = WorkflowStatus.FAILED
        self.updated_at = time.time()


class WorkflowEngine:
    """工作流执行引擎"""

    def __init__(self, ai_router=None):
        self.ai_router = ai_router
        self.workflows: dict[str, ResearchWorkflow] = {}

    def create_workflow(self, workflow_type: str, title: str, config: dict = None) -> ResearchWorkflow:
        workflow = ResearchWorkflow(
            title=title,
            workflow_type=workflow_type,
            config=config or {},
        )
        self.workflows[workflow.id] = workflow
        return workflow

    def get_workflow(self, workflow_id: str) -> Optional[ResearchWorkflow]:
        return self.workflows.get(workflow_id)

    def list_workflows(self) -> list[dict]:
        return [w.to_dict() for w in sorted(
            self.workflows.values(),
            key=lambda w: w.created_at,
            reverse=True,
        )]

    def delete_workflow(self, workflow_id: str) -> bool:
        if workflow_id in self.workflows:
            del self.workflows[workflow_id]
            return True
        return False

    async def run_workflow(self, workflow_id: str, progress_callback: Callable = None) -> dict:
        """执行工作流"""
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            return {"error": "工作流不存在"}

        workflow.status = WorkflowStatus.RUNNING

        try:
            for step in workflow.steps:
                if step.status != WorkflowStatus.PENDING:
                    continue

                step.status = WorkflowStatus.RUNNING
                if progress_callback:
                    await progress_callback(workflow.to_dict())

                # 执行步骤
                try:
                    result = await self._execute_step(workflow, step)
                    workflow.complete_step(step.id, result)
                except Exception as e:
                    workflow.fail_step(step.id, str(e))
                    return workflow.to_dict()

                if progress_callback:
                    await progress_callback(workflow.to_dict())

            workflow.status = WorkflowStatus.COMPLETED
            workflow.updated_at = time.time()
            return workflow.to_dict()

        except Exception as e:
            workflow.status = WorkflowStatus.FAILED
            workflow.updated_at = time.time()
            return workflow.to_dict()

    async def _execute_step(self, workflow: ResearchWorkflow, step: WorkflowStep) -> dict:
        """执行单个步骤"""
        # 由子类实现
        raise NotImplementedError("子类必须实现 _execute_step")
