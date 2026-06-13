#include <gtest/gtest.h>

#include <embodied_core/task_goal.hpp>
#include <embodied_msgs/msg/embodied_goal.hpp>

#include "chassis_agent_cpp/goal_from_msg.hpp"

using embodied_core::TaskGoal;
using embodied_core::TaskGoalKind;
using embodied_msgs::msg::EmbodiedGoal;

TEST(GoalFromMsgTest, push_red_box_round_trip) {
  const TaskGoal goal = TaskGoal::push_red_box();
  const EmbodiedGoal msg = chassis_agent_cpp::msg_from_task_goal(goal);
  EXPECT_EQ(msg.kind, EmbodiedGoal::PUSH_RED_BOX);
  const TaskGoal back = chassis_agent_cpp::task_goal_from_msg(msg);
  EXPECT_EQ(back.kind, TaskGoalKind::PushRedBox);
}

TEST(GoalFromMsgTest, nav_to_object_round_trip) {
  TaskGoal goal = TaskGoal::nav_to_object("box_red", 0.35);
  const EmbodiedGoal msg = chassis_agent_cpp::msg_from_task_goal(goal);
  EXPECT_EQ(msg.kind, EmbodiedGoal::OBJECT);
  EXPECT_NEAR(msg.standoff, 0.35, 1e-9);
  const TaskGoal back = chassis_agent_cpp::task_goal_from_msg(msg);
  EXPECT_EQ(back.kind, TaskGoalKind::Object);
  EXPECT_EQ(back.object_name, "box_red");
}

TEST(GoalFromMsgTest, point_round_trip) {
  const TaskGoal goal = TaskGoal::point(2.5, 1.0);
  const EmbodiedGoal msg = chassis_agent_cpp::msg_from_task_goal(goal);
  EXPECT_EQ(msg.kind, EmbodiedGoal::POINT);
  EXPECT_NEAR(msg.x, 2.5, 1e-9);
  EXPECT_NEAR(msg.y, 1.0, 1e-9);
  const TaskGoal back = chassis_agent_cpp::task_goal_from_msg(msg);
  EXPECT_EQ(back.kind, TaskGoalKind::Point);
}
