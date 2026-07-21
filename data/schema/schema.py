from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class AccountTier(str, Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class IssueCategory(str, Enum):
    BILLING = "billing"
    TECHNICAL = "technical"
    ACCOUNT = "account"
    OTHER = "other"


class IssuePriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class ResolutionStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    ESCALATED = "escalated"


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Customer(StrictBaseModel):
    name: str
    email: Optional[str] = None
    account_tier: Optional[AccountTier] = None


class Issue(StrictBaseModel):
    category: IssueCategory
    summary: str
    priority: Optional[IssuePriority] = None


class Resolution(StrictBaseModel):
    status: ResolutionStatus
    resolution_notes: Optional[str] = None
    assigned_agent: Optional[str] = None


class Metadata(StrictBaseModel):
    created_at: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class ExtractedDocument(StrictBaseModel):
    ticket_id: Optional[str] = None
    customer: Customer
    issue: Issue
    resolution: Resolution
    metadata: Metadata
