"""Build EmbodiedTaskPlan messages from templates."""

from __future__ import annotations

from embodied_msgs.msg import EmbodiedGoal, EmbodiedTaskPlan
from std_msgs.msg import Header

from embodied_planner.templates import GoalTemplate, TaskTemplate


def goal_from_template(goal: GoalTemplate) -> EmbodiedGoal:
    msg = EmbodiedGoal()
    fields = goal.to_msg_fields()
    msg.kind = int(fields['kind'])
    msg.x = float(fields['x'])
    msg.y = float(fields['y'])
    msg.object_name = str(fields['object_name'])
    msg.standoff = float(fields['standoff'])
    return msg


def plan_from_template(
    template: TaskTemplate,
    *,
    source: str = 'template',
    raw_text: str = '',
    frame_id: str = 'map',
) -> EmbodiedTaskPlan:
    plan = EmbodiedTaskPlan()
    plan.header = Header()
    plan.header.frame_id = frame_id
    plan.source = source
    plan.raw_text = raw_text or template.id
    plan.goals = [goal_from_template(g) for g in template.goals]
    return plan
