"""
Knowledge & Experience Graph Enums (Sprint 15).
"""

from enum import Enum


class KnowledgeNodeType(str, Enum):
    ENTITY = "entity"              # Apps, Files, URLs
    CONCEPT = "concept"            # Domain concepts
    GOAL_ARTIFACT = "goal_artifact"# Goal output artifacts
    PREFERENCE = "preference"      # User preferences
    PATTERN = "pattern"            # Successful workflow patterns
    RUNTIME = "runtime"            # Runtime nodes (Browser, Desktop, Vision)
    TOOL = "tool"                  # Tool nodes (click, search, ocr, navigate, download)
    ENVIRONMENT = "environment"    # System environments (Windows 11, Chrome, Excel)
    ERROR = "error"                # Encountered errors (SelectorNotFound, Timeout)


class KnowledgeRelationType(str, Enum):
    HAS_STEP = "has_step"
    USES_RUNTIME = "uses_runtime"
    USES_TOOL = "uses_tool"
    BELONGS_TO = "belongs_to"
    PREFERS = "prefers"
    RECOVERED_BY = "recovered_by"
    FAILED_ON = "failed_on"
    EXECUTED_ON = "executed_on"
    GENERATED = "generated"
    SIMILAR_GOAL = "similar_goal"
    LEARNED_FROM = "learned_from"
    CAUSES = "causes"
