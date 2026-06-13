#include <gtest/gtest.h>

#include <embodied_core/task_goal.hpp>
#include <embodied_msgs/msg/embodied_goal.hpp>
#include <embodied_msgs/msg/embodied_task_plan.hpp>

#include "chassis_agent_cpp/goal_from_msg.hpp"

using embodied_core::TaskGoal;
using embodied_core::TaskGoalKind;
using embodied_msgs::msg::EmbodiedGoal;
using embodied_msgs::msg::EmbodiedTaskPlan;

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

TEST(GoalFromMsgTest, infer_recommended_brain_push) {
  EmbodiedGoal msg;
  msg.kind = EmbodiedGoal::PUSH_RED_BOX;
  EXPECT_EQ(chassis_agent_cpp::infer_recommended_brain(msg, "rule"), "rule");
  EXPECT_EQ(chassis_agent_cpp::infer_recommended_brain(msg, "hybrid"), "hybrid");
}

TEST(GoalFromMsgTest, infer_recommended_brain_nav) {
  EmbodiedGoal msg;
  msg.kind = EmbodiedGoal::OBJECT;
  msg.object_name = "box_red";
  EXPECT_EQ(chassis_agent_cpp::infer_recommended_brain(msg, "rule"), "rl");
}

TEST(GoalFromMsgTest, resolve_recommended_brain_from_plan) {
  EmbodiedTaskPlan plan;
  plan.recommended_brain = "rl";
  EmbodiedGoal goal;
  goal.kind = EmbodiedGoal::PUSH_RED_BOX;
  plan.goals.push_back(goal);
  EXPECT_EQ(chassis_agent_cpp::resolve_recommended_brain(plan, "rule"), "rl");
}

TEST(GoalFromMsgTest, resolve_recommended_brain_infers_from_goal) {
  EmbodiedTaskPlan plan;
  EmbodiedGoal goal;
  goal.kind = EmbodiedGoal::OBJECT;
  goal.object_name = "box_red";
  plan.goals.push_back(goal);
  EXPECT_EQ(chassis_agent_cpp::resolve_recommended_brain(plan, "rule"), "rl");
}
