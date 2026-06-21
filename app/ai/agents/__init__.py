"""科研 Agent 模块

提供文献综述、论文写作、实验设计、同行评审、多 Agent 辩论等 Agent。
"""

from .workflow import ResearchWorkflow, WorkflowStep
from .review_agent import LiteratureReviewAgent
from .writing_agent import PaperWritingAgent
from .experiment_agent import ExperimentDesignAgent
from .peer_review_agent import PeerReviewAgent
from .debate_agent import DebateAgent

__all__ = [
    "ResearchWorkflow",
    "WorkflowStep",
    "LiteratureReviewAgent",
    "PaperWritingAgent",
    "ExperimentDesignAgent",
    "PeerReviewAgent",
    "DebateAgent",
]
