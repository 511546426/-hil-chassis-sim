#include "chassis_agent_cpp/goal_from_msg.hpp"

namespace chassis_agent_cpp {

namespace {

using embodied_msgs::msg::EmbodiedGoal;
using embodied_core::TaskGoal;
using embodied_core::TaskGoalKind;

TaskGoalKind kind_from_msg(uint8_t kind) {
  switch (kind) {
    case EmbodiedGoal::POINT:
      return TaskGoalKind::Point;
    case EmbodiedGoal::OBJECT:
      return TaskGoalKind::Object;
    case EmbodiedGoal::PUSH_RED_BOX:
      return TaskGoalKind::PushRedBox;
    default:
      return TaskGoalKind::PushRedBox;
  }
}

uint8_t kind_to_msg(TaskGoalKind kind) {
  switch (kind) {
    case TaskGoalKind::Point:
      return EmbodiedGoal::POINT;
    case TaskGoalKind::Object:
      return EmbodiedGoal::OBJECT;
    case TaskGoalKind::PushRedBox:
      return EmbodiedGoal::PUSH_RED_BOX;
  }
  return EmbodiedGoal::PUSH_RED_BOX;
}

}  // namespace

TaskGoal task_goal_from_msg(const EmbodiedGoal &msg) {
  TaskGoal goal;
  goal.kind = kind_from_msg(msg.kind);
  goal.x = msg.x;
  goal.y = msg.y;
  goal.object_name = msg.object_name.empty() ? "box_red" : msg.object_name;
  goal.standoff = msg.standoff > 0.0 ? msg.standoff : 0.35;
  return goal;
}

EmbodiedGoal msg_from_task_goal(const TaskGoal &goal) {
  EmbodiedGoal msg;
  msg.kind = kind_to_msg(goal.kind);
  msg.x = goal.x;
  msg.y = goal.y;
  msg.object_name = goal.object_name;
  msg.standoff = goal.standoff;
  return msg;
}

}  // namespace chassis_agent_cpp
