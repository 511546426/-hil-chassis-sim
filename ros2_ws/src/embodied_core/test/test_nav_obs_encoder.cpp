#include "embodied_core/nav_obs_encoder.hpp"

#include <cmath>

#include <gtest/gtest.h>

using namespace embodied_core;

static WorldView world_at_origin_with_box() {
  WorldView world;
  world.base_x = 0.0;
  world.base_y = 0.0;
  world.base_yaw = 0.0;
  world.base_vx = 0.5;
  world.base_steer = 0.1;
  world.objects.push_back(ObjectPose{"box_red", 2.5, 0.0, 0.18});
  return world;
}

TEST(NavObsEncoderTest, dimension_matches_spec) {
  const auto world = world_at_origin_with_box();
  const auto obs = encode_nav_obs(world, TaskGoal::point(2.5, 0.0));
  EXPECT_EQ(obs.size(), static_cast<size_t>(kNavObsDim));
}

TEST(NavObsEncoderTest, forward_goal_in_body_frame) {
  const auto world = world_at_origin_with_box();
  TaskGoal goal = TaskGoal::point(2.5, 0.0);
  goal.standoff = 0.0;
  const auto obs_no_standoff = encode_nav_obs(world, goal);

  EXPECT_NEAR(obs_no_standoff[kObsBaseX], 0.0, 1e-9);
  EXPECT_NEAR(obs_no_standoff[kObsBaseY], 0.0, 1e-9);
  EXPECT_NEAR(obs_no_standoff[kObsBaseYaw], 0.0, 1e-9);
  EXPECT_NEAR(obs_no_standoff[kObsGoalDx], 2.5 / kNavObsGoalScale, 1e-9);
  EXPECT_NEAR(obs_no_standoff[kObsGoalDy], 0.0, 1e-9);
  EXPECT_NEAR(obs_no_standoff[kObsDistGoal], 2.5 / kNavObsGoalScale, 1e-9);
  EXPECT_NEAR(obs_no_standoff[kObsBaseVx], 0.5 / kNavObsMaxVx, 1e-9);
  EXPECT_NEAR(obs_no_standoff[kObsBaseSteerAbs], 0.1 / kNavObsMaxSteer, 1e-9);
}

TEST(NavObsEncoderTest, object_goal_resolves_box_red) {
  WorldView world;
  world.base_x = 1.0;
  world.base_y = 0.0;
  world.base_yaw = 0.0;
  world.objects.push_back(ObjectPose{"box_red", 2.5, 0.0, 0.18});

  TaskGoal goal;
  goal.kind = TaskGoalKind::Object;
  goal.object_name = "box_red";
  goal.standoff = 0.0;

  const auto obs = encode_nav_obs(world, goal);
  EXPECT_NEAR(obs[kObsGoalDx], 1.5 / kNavObsGoalScale, 1e-9);
  EXPECT_NEAR(obs[kObsDistGoal], 1.5 / kNavObsGoalScale, 1e-9);
}

TEST(NavObsEncoderTest, snapshot_values_fixed) {
  const auto world = world_at_origin_with_box();
  TaskGoal goal = TaskGoal::point(2.0, 1.0);
  goal.standoff = 0.0;
  const auto obs = encode_nav_obs(world, goal);

  EXPECT_NEAR(obs[kObsGoalDx], 2.0 / kNavObsGoalScale, 1e-9);
  EXPECT_NEAR(obs[kObsGoalDy], 1.0 / kNavObsGoalScale, 1e-9);
  EXPECT_NEAR(obs[kObsDistGoal], std::hypot(2.0, 1.0) / kNavObsGoalScale, 1e-9);
}
