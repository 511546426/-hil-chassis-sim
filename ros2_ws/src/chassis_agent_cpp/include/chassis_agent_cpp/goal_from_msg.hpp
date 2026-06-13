#pragma once

#include <embodied_core/task_goal.hpp>
#include <embodied_msgs/msg/embodied_goal.hpp>
#include <embodied_msgs/msg/embodied_task_plan.hpp>

namespace chassis_agent_cpp {

embodied_core::TaskGoal task_goal_from_msg(
    const embodied_msgs::msg::EmbodiedGoal &msg);

embodied_msgs::msg::EmbodiedGoal msg_from_task_goal(
    const embodied_core::TaskGoal &goal);

/// Infer brain type from goal when TaskPlan.recommended_brain is empty.
std::string infer_recommended_brain(
    const embodied_msgs::msg::EmbodiedGoal &goal,
    const std::string &auto_push_brain = "rule");

/// Resolve brain type from TaskPlan (recommended_brain or infer from goal).
std::string resolve_recommended_brain(
    const embodied_msgs::msg::EmbodiedTaskPlan &plan,
    const std::string &auto_push_brain = "rule");

}  // namespace chassis_agent_cpp
