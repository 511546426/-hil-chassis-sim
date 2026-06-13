#pragma once

#include <embodied_core/task_goal.hpp>
#include <embodied_msgs/msg/embodied_goal.hpp>
#include <embodied_msgs/msg/embodied_task_plan.hpp>

namespace chassis_agent_cpp {

embodied_core::TaskGoal task_goal_from_msg(
    const embodied_msgs::msg::EmbodiedGoal &msg);

embodied_msgs::msg::EmbodiedGoal msg_from_task_goal(
    const embodied_core::TaskGoal &goal);

}  // namespace chassis_agent_cpp
