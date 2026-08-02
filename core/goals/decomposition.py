"""
Goal Decomposer.
Decomposes high-level GoalSpecifications into a SubGoal DAG with multi-relation edges.
"""

from core.goals.enums import GoalType, RelationType
from core.goals.models import Goal, GoalDependencyGraph, GoalSpecification, SubGoal


class GoalDecomposer:
    """
    Decomposes High-Level GoalSpecifications into SubGoals and DAG relations.
    """

    def decompose(self, spec: GoalSpecification) -> Goal:
        goal = Goal(spec=spec)
        graph = GoalDependencyGraph()

        desc_lower = spec.description.lower()

        # Dynamic rule-based decomposition pattern
        if "report" in desc_lower or "download" in desc_lower or "browser" in desc_lower:
            sg_open = SubGoal(
                id="sg_open_browser",
                title="Open Browser",
                description="Launch browser and navigate to target URL",
                required_capability="navigation",
            )
            sg_login = SubGoal(
                id="sg_login",
                title="Login to Service",
                description="Authenticate with credentials",
                required_capability="dom_interaction",
            )
            sg_export = SubGoal(
                id="sg_export",
                title="Export Data",
                description="Trigger export / download action",
                required_capability="download",
            )
            sg_save = SubGoal(
                id="sg_save",
                title="Save File to Disk",
                description="Save downloaded file into local filesystem",
                required_capability="mouse",
            )
            sg_verify_vision = SubGoal(
                id="sg_verify_vision",
                title="Verify Visual Confirmation",
                description="Use vision runtime to verify success text on screen",
                required_capability="ocr",
            )

            graph.add_subgoal(sg_open)
            graph.add_subgoal(sg_login)
            graph.add_subgoal(sg_export)
            graph.add_subgoal(sg_save)
            graph.add_subgoal(sg_verify_vision)

            # Build multi-relation DAG
            graph.add_relation(sg_open.id, sg_login.id, RelationType.REQUIRED)
            graph.add_relation(sg_login.id, sg_export.id, RelationType.REQUIRED)
            graph.add_relation(sg_export.id, sg_save.id, RelationType.REQUIRED)
            # Verify Vision is OPTIONAL (failure won't break the goal)
            graph.add_relation(sg_save.id, sg_verify_vision.id, RelationType.OPTIONAL)

        else:
            # Default Desktop / Mixed Goal pattern
            sg_observe = SubGoal(
                id="sg_observe",
                title="Observe Environment",
                description="Capture screen and active windows",
                required_capability="screenshot",
            )
            sg_interact = SubGoal(
                id="sg_interact",
                title="Execute Desktop Action",
                description="Perform mouse/keyboard action on active window",
                required_capability="mouse",
            )

            graph.add_subgoal(sg_observe)
            graph.add_subgoal(sg_interact)
            graph.add_relation(sg_observe.id, sg_interact.id, RelationType.REQUIRED)

        goal.graph = graph
        return goal
