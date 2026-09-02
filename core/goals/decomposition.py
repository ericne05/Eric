"""
Goal Decomposer.
Decomposes High-Level GoalSpecifications into SubGoals with CapabilityRequirements and SuccessCriteria.
"""

from core.goals.enums import GoalType, RelationType
from core.goals.models import (
    CapabilityRequirement,
    Goal,
    GoalDependencyGraph,
    GoalSpecification,
    SubGoal,
    SuccessCriterion,
)


class GoalDecomposer:
    """
    Decomposes High-Level GoalSpecifications into SubGoals and DAG relations.
    """

    def decompose(self, spec: GoalSpecification) -> Goal:
        goal = Goal(spec=spec)
        graph = GoalDependencyGraph()

        desc_lower = (spec.description or spec.title or spec.intent).lower()

        # Build default SuccessCriteria if empty
        if not spec.success_criteria:
            spec.success_criteria.append(
                SuccessCriterion(criterion_type="execution_success", target="all_required_steps", expected_value=True)
            )

        if "report" in desc_lower or "download" in desc_lower or "browser" in desc_lower:
            sg_open = SubGoal(
                id="sg_open_browser",
                title="Open Browser",
                description="Launch browser and navigate to target URL",
                capability_requirement=CapabilityRequirement(required=["navigation"], preferred=["browser"]),
            )
            sg_login = SubGoal(
                id="sg_login",
                title="Login to Service",
                description="Authenticate with credentials",
                capability_requirement=CapabilityRequirement(required=["dom_interaction"], preferred=["browser"]),
            )
            sg_export = SubGoal(
                id="sg_export",
                title="Export Data",
                description="Trigger export / download action",
                capability_requirement=CapabilityRequirement(required=["download"], preferred=["browser"]),
            )
            sg_save = SubGoal(
                id="sg_save",
                title="Save File to Disk",
                description="Save downloaded file into local filesystem",
                capability_requirement=CapabilityRequirement(required=["mouse"], preferred=["desktop"]),
            )
            sg_verify_vision = SubGoal(
                id="sg_verify_vision",
                title="Verify Visual Confirmation",
                description="Use vision runtime to verify success text on screen",
                capability_requirement=CapabilityRequirement(required=["ocr"], preferred=["vision"], optional=["desktop"]),
            )

            graph.add_subgoal(sg_open)
            graph.add_subgoal(sg_login)
            graph.add_subgoal(sg_export)
            graph.add_subgoal(sg_save)
            graph.add_subgoal(sg_verify_vision)

            graph.add_relation(sg_open.id, sg_login.id, RelationType.REQUIRED)
            graph.add_relation(sg_login.id, sg_export.id, RelationType.REQUIRED)
            graph.add_relation(sg_export.id, sg_save.id, RelationType.REQUIRED)
            graph.add_relation(sg_save.id, sg_verify_vision.id, RelationType.OPTIONAL)

        else:
            sg_observe = SubGoal(
                id="sg_observe",
                title="Observe Environment",
                description="Capture screen and active windows",
                capability_requirement=CapabilityRequirement(required=["screenshot"], preferred=["desktop", "vision"]),
            )
            # Use spec.intent as the action name and preserve spec.parameters as result_data
            action_title = spec.intent if spec.intent else "execute_desktop_action"
            sg_interact = SubGoal(
                id="sg_interact",
                title=action_title,
                description=spec.description or spec.intent,
                capability_requirement=CapabilityRequirement(required=["mouse"], preferred=["desktop"]),
                result_data=dict(spec.parameters) if spec.parameters else {},
            )

            graph.add_subgoal(sg_observe)
            graph.add_subgoal(sg_interact)
            graph.add_relation(sg_observe.id, sg_interact.id, RelationType.REQUIRED)

        goal.graph = graph
        return goal
