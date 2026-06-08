#include "embodied_core/navigation.hpp"

#include <cmath>
#include <gtest/gtest.h>

using namespace embodied_core;

// ═══════════════════════════════════════════════════════
// normalize_angle
// ═══════════════════════════════════════════════════════

TEST(NavigationTest, normalize_angle_zero) {
  EXPECT_NEAR(normalize_angle(0.0), 0.0, 1e-9);
}

TEST(NavigationTest, normalize_angle_wraps_pi) {
  EXPECT_NEAR(normalize_angle(3.0 * M_PI), M_PI, 1e-6);
  EXPECT_NEAR(normalize_angle(-3.0 * M_PI), -M_PI, 1e-6);
}

// ═══════════════════════════════════════════════════════
// approach_point
// ═══════════════════════════════════════════════════════

TEST(NavigationTest, approach_point_on_line) {
  double gx = 0.0;
  double gy = 0.0;
  approach_point(0.0, 0.0, 2.0, 0.0, 0.35, gx, gy);
  EXPECT_NEAR(gx, 1.65, 1e-6);
  EXPECT_NEAR(gy, 0.0, 1e-6);
}

TEST(NavigationTest, approach_point_at_origin_fallback) {
  double gx = 0.0;
  double gy = 0.0;
  approach_point(0.0, 0.0, 0.0, 0.0, 0.35, gx, gy);
  EXPECT_NEAR(gx, -0.35, 1e-6);
  EXPECT_NEAR(gy, 0.0, 1e-6);
}

// ═══════════════════════════════════════════════════════
// pure_pursuit
// ═══════════════════════════════════════════════════════

TEST(NavigationTest, pure_pursuit_arrived_when_close) {
  const auto cmd = pure_pursuit(0.0, 0.0, 0.0, 0.1, 0.0, 0.3);
  EXPECT_TRUE(cmd.arrived);
  EXPECT_NEAR(cmd.target_linear_x, 0.0, 1e-9);
  EXPECT_NEAR(cmd.target_steering_angle, 0.0, 1e-9);
}

TEST(NavigationTest, pure_pursuit_matches_python_heading_forward) {
  // 机器人在原点朝 +X，目标在 (2, 0) — 应前进且 steer≈0
  // 对照：chassis_agent/navigation.py 同参数调用
  const auto cmd = pure_pursuit(0.0, 0.0, 0.0, 2.0, 0.0);
  EXPECT_FALSE(cmd.arrived);
  EXPECT_GT(cmd.target_linear_x, 0.4);
  EXPECT_NEAR(cmd.target_steering_angle, 0.0, 0.05);
}

TEST(NavigationTest, pure_pursuit_turns_toward_lateral_target) {
  const auto cmd = pure_pursuit(0.0, 0.0, 0.0, 0.0, 2.0);
  EXPECT_FALSE(cmd.arrived);
  EXPECT_GT(cmd.target_steering_angle, 0.1);
}

// ═══════════════════════════════════════════════════════
// stuck_at_box
// ═══════════════════════════════════════════════════════

static WorldView world_near_box(double base_x, double base_vx, double box_x = 2.5) {
  WorldView w;
  w.base_x = base_x;
  w.base_vx = base_vx;
  w.objects.push_back(ObjectPose{"box_red", box_x, 0.0, 0.18});
  return w;
}

TEST(NavigationTest, stuck_at_box_close_and_cmd_forward) {
  const auto w = world_near_box(2.0, 0.0);
  EXPECT_TRUE(stuck_at_box(w, 0.2));
}

TEST(NavigationTest, stuck_at_box_not_when_far) {
  const auto w = world_near_box(0.0, 0.5);
  EXPECT_FALSE(stuck_at_box(w, 0.5));
}
