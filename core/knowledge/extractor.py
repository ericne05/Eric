"""
Experience Extractor.
Extracts Knowledge & Experience Nodes and Edges from executed Goals & GoalArtifacts.
"""

from typing import Optional

from core.goals.models import Goal, GoalArtifact
from core.knowledge.enums import KnowledgeNodeType, KnowledgeRelationType
from core.knowledge.interfaces import IKnowledgeExtractor
from core.knowledge.models import ExperienceScore, KnowledgeGraph, KnowledgeNode


class ExperienceExtractor(IKnowledgeExtractor):
    """
    Extracts Experience & Knowledge from completed or failed Goal executions.
    Populates Runtime, Tool, Environment, Artifact, and Error Nodes.
    """

    def extract_experience(self, goal: Goal, artifact: Optional[GoalArtifact] = None) -> KnowledgeGraph:
        graph = KnowledgeGraph()
        is_success = (goal.result.success if goal.result else (goal.state == "completed"))

        # Calculate quantitative ExperienceScore
        dur = goal.progress.elapsed_seconds or (goal.cost_estimate.estimated_seconds if goal.cost_estimate else 1.0)
        rec = goal.progress.recovery_count
        exp_calculator = ExperienceScore(
            success=is_success,
            token_cost=goal.cost_estimate.estimated_tokens if goal.cost_estimate else 0,
            duration_seconds=dur,
            recovery_count=rec,
        )
        score = exp_calculator.calculate()

        # 1. Goal Node
        goal_node = KnowledgeNode(
            id=f"goal_{goal.id}",
            node_type=KnowledgeNodeType.PATTERN if is_success else KnowledgeNodeType.ENTITY,
            name=goal.spec.title or goal.spec.description[:50],
            attributes={
                "description": goal.spec.description,
                "intent": goal.spec.intent,
                "goal_type": goal.spec.goal_type.value,
                "success": is_success,
            },
            experience_score=score,
            success_rate=1.0 if is_success else 0.0,
        )
        graph.add_node(goal_node)

        # 2. Environment Node (Windows 11)
        env_node = KnowledgeNode(
            id="env_windows11",
            node_type=KnowledgeNodeType.ENVIRONMENT,
            name="Windows 11",
        )
        graph.add_node(env_node)
        graph.add_edge(goal_node.id, env_node.id, KnowledgeRelationType.EXECUTED_ON, confidence=1.0)

        # 3. Steps & Runtime / Tool Nodes
        if goal.plan and goal.plan.steps:
            for step in goal.plan.steps:
                # Step SubGoal Node
                sg_node = KnowledgeNode(
                    id=f"step_{step.id}",
                    node_type=KnowledgeNodeType.CONCEPT,
                    name=step.action_name,
                    attributes={"args": step.arguments},
                )
                graph.add_node(sg_node)
                graph.add_edge(goal_node.id, sg_node.id, KnowledgeRelationType.HAS_STEP, confidence=0.95)

                # Tool Node
                tool_name = step.action_name
                tool_node = KnowledgeNode(
                    id=f"tool_{tool_name}",
                    node_type=KnowledgeNodeType.TOOL,
                    name=tool_name,
                )
                graph.add_node(tool_node)
                graph.add_edge(sg_node.id, tool_node.id, KnowledgeRelationType.USES_TOOL, confidence=0.95)

                # Runtime Node from CapabilityRequirement
                if step.capability_requirement and step.capability_requirement.preferred:
                    for rt_name in step.capability_requirement.preferred:
                        rt_node = KnowledgeNode(
                            id=f"runtime_{rt_name}",
                            node_type=KnowledgeNodeType.RUNTIME,
                            name=rt_name,
                        )
                        graph.add_node(rt_node)
                        graph.add_edge(sg_node.id, rt_node.id, KnowledgeRelationType.USES_RUNTIME, confidence=0.90 if is_success else 0.40)

        # 4. Error Nodes (if recoveries / failures occurred)
        if not is_success or rec > 0:
            err_node = KnowledgeNode(
                id=f"error_{goal.id}",
                node_type=KnowledgeNodeType.ERROR,
                name=f"ExecutionError_rec_{rec}",
                attributes={"error": goal.result.error if goal.result else "Step recovery triggered"},
            )
            graph.add_node(err_node)
            rel_type = KnowledgeRelationType.RECOVERED_BY if is_success else KnowledgeRelationType.FAILED_ON
            graph.add_edge(goal_node.id, err_node.id, rel_type, confidence=0.85)

        # 5. Goal Artifact Node
        if artifact or goal.artifact:
            art = artifact or goal.artifact
            art_node = KnowledgeNode(
                id=f"artifact_{art.id}",
                node_type=KnowledgeNodeType.GOAL_ARTIFACT,
                name=art.title,
                attributes={"summary": art.summary, "logs_count": len(art.logs)},
            )
            graph.add_node(art_node)
            graph.add_edge(goal_node.id, art_node.id, KnowledgeRelationType.GENERATED, confidence=1.0)

        return graph
