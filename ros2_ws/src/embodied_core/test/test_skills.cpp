#include "embodied_core/arm_preset.hpp"
#include "embodied_core/manipulate_skill.hpp"
#include "embodied_core/navigate_skill.hpp"
#include "embodied_core/skill_executor.hpp"

#include <cmath>
#include <gtest/gtest.h>

using namespace embodied_core;

// ═══════════════════════════════════════════════════════
// 辅助
// ═══════════════════════════════════════════════════════

static WorldView make_world(
    double base_x, double base_y, double base_yaw = 0.0,
    double base_vx = 0.0) {
  WorldView w;
  w.base_x = base_x;
  w.base_y = base_y;
  w.base_yaw = base_yaw;
  w.base_vx = base_vx;
  return w;
}

static WorldView world_with_red_box(
    double base_x, double base_y, double base_yaw = 0.0,
    double box_x = 2.5, double box_y = 0.0) {
  auto w = make_world(base_x, base_y, base_yaw);
  w.objects.push_back(ObjectPose{"box_red", box_x, box_y, 0.18});
  return w;
}

static void expect_arm_stow(const SkillOutput &out) {
  EXPECT_NEAR(out.arm_shoulder, kArmStow.shoulder, 1e-9);
  EXPECT_NEAR(out.arm_elbow, kArmStow.elbow, 1e-9);
  EXPECT_NEAR(out.arm_wrist, kArmStow.wrist, 1e-9);
  EXPECT_NEAR(out.gripper, 0.0, 1e-9);
  EXPECT_FALSE(out.emergency_brake);
}

// ═══════════════════════════════════════════════════════
// NavigateSkill
// ═══════════════════════════════════════════════════════

TEST(NavigateSkillTest, compute_forward_moves_toward_target) {
  NavigateSkill skill;
  const auto w = make_world(0.0, 0.0, 0.0);
  const SkillOutput out = skill.compute(w, 2.0, 0.0);

  EXPECT_GT(out.target_linear_x, 0.4);
  EXPECT_NEAR(out.target_steering_angle, 0.0, 0.05);
  expect_arm_stow(out);
}

TEST(NavigateSkillTest, compute_applies_standoff_before_pursuit) {
  NavigateSkill skill(0.35, 0.3);
  // 已在红箱 standoff 点附近，应视为到达并停车
  const auto w = make_world(2.12, 0.0, 0.0);
  const SkillOutput out = skill.compute(w, 2.5, 0.0);

  EXPECT_NEAR(out.target_linear_x, 0.0, 1e-9);
  EXPECT_NEAR(out.target_steering_angle, 0.0, 1e-9);
  expect_arm_stow(out);
}

TEST(NavigateSkillTest, compute_to_box_red_uses_box_pose) {
  NavigateSkill skill;
  const auto w = world_with_red_box(0.0, 0.0, 0.0, 3.0, 1.0);
  const SkillOutput out = skill.compute_to_box_red(w);

  EXPECT_GT(out.target_linear_x, 0.0);
  expect_arm_stow(out);
}

TEST(NavigateSkillTest, compute_to_box_red_fallback_without_box) {
  NavigateSkill skill;
  const auto w = make_world(0.0, 0.0, 0.0);
  const SkillOutput out = skill.compute_to_box_red(w);

  // fallback 中心 (2.5, 0)，与有 box 时行为一致：应前进
  EXPECT_GT(out.target_linear_x, 0.4);
  expect_arm_stow(out);
}

TEST(NavigateSkillTest, compute_reverse_negative_vx) {
  NavigateSkill skill(0.35, 0.3, 0.35);
  const auto w = world_with_red_box(2.0, 0.0);
  const SkillOutput out = skill.compute(w, 2.5, 0.0, true);

  EXPECT_NEAR(out.target_linear_x, -0.35, 1e-9);
  expect_arm_stow(out);
}

TEST(NavigateSkillTest, config_getters) {
  NavigateSkill skill(0.4, 0.25, 0.2);
  EXPECT_NEAR(skill.standoff(), 0.4, 1e-9);
  EXPECT_NEAR(skill.arrive_dist(), 0.25, 1e-9);
}

// ═══════════════════════════════════════════════════════
// ManipulateSkill
// ═══════════════════════════════════════════════════════

TEST(ManipulateSkillTest, preset_to_arm_values) {
  const ArmPreset stow = ManipulateSkill::preset_to_arm(ManipulateSkill::Preset::Stow);
  const ArmPreset reach = ManipulateSkill::preset_to_arm(ManipulateSkill::Preset::Reach);
  const ArmPreset grasp = ManipulateSkill::preset_to_arm(ManipulateSkill::Preset::GraspReady);

  EXPECT_NEAR(stow.shoulder, kArmStow.shoulder, 1e-9);
  EXPECT_NEAR(reach.elbow, kArmReach.elbow, 1e-9);
  EXPECT_NEAR(grasp.wrist, kArmGraspReady.wrist, 1e-9);
}

TEST(ManipulateSkillTest, compute_reach_zeros_base) {
  ManipulateSkill skill;
  WorldView w;
  w.gripper = 0.5;

  const SkillOutput out = skill.compute(
      w, ManipulateSkill::Preset::Reach, ManipulateSkill::GripperAction::Hold);

  EXPECT_NEAR(out.target_linear_x, 0.0, 1e-9);
  EXPECT_NEAR(out.target_steering_angle, 0.0, 1e-9);
  EXPECT_NEAR(out.arm_shoulder, kArmReach.shoulder, 1e-9);
  EXPECT_NEAR(out.arm_elbow, kArmReach.elbow, 1e-9);
  EXPECT_NEAR(out.arm_wrist, kArmReach.wrist, 1e-9);
  EXPECT_NEAR(out.gripper, 0.5, 1e-9);
  EXPECT_FALSE(out.emergency_brake);
}

TEST(ManipulateSkillTest, gripper_open_close_hold) {
  ManipulateSkill skill;
  WorldView w;
  w.gripper = 0.3;

  const auto open_out = skill.compute(
      w, ManipulateSkill::Preset::Stow, ManipulateSkill::GripperAction::Open);
  const auto close_out = skill.compute(
      w, ManipulateSkill::Preset::Stow, ManipulateSkill::GripperAction::Close);
  const auto hold_out = skill.compute(
      w, ManipulateSkill::Preset::Stow, ManipulateSkill::GripperAction::Hold);

  EXPECT_NEAR(open_out.gripper, 0.0, 1e-9);
  EXPECT_NEAR(close_out.gripper, 1.0, 1e-9);
  EXPECT_NEAR(hold_out.gripper, 0.3, 1e-9);
}

TEST(ManipulateSkillTest, arm_at_preset_within_tolerance) {
  WorldView w;
  w.arm_shoulder = kArmReach.shoulder;
  w.arm_elbow = kArmReach.elbow + 0.05;
  w.arm_wrist = kArmReach.wrist;

  EXPECT_TRUE(ManipulateSkill::arm_at_preset(w, ManipulateSkill::Preset::Reach, 0.08));
  EXPECT_FALSE(ManipulateSkill::arm_at_preset(w, ManipulateSkill::Preset::Reach, 0.04));
}

TEST(ManipulateSkillTest, gripper_at_within_tolerance) {
  WorldView w;
  w.gripper = 0.97;

  EXPECT_TRUE(ManipulateSkill::gripper_at(w, 1.0, 0.05));
  EXPECT_FALSE(ManipulateSkill::gripper_at(w, 1.0, 0.02));
}

// ═══════════════════════════════════════════════════════
// SkillExecutor
// ═══════════════════════════════════════════════════════

TEST(SkillExecutorTest, step_navigate_delegates) {
  NavigateSkill nav(0.35, 0.3);
  ManipulateSkill manip;
  SkillExecutor executor(nav, manip);

  const auto w = make_world(0.0, 0.0, 0.0);
  const SkillOutput direct = nav.compute(w, 2.0, 0.0);
  const SkillOutput via_exec = executor.step_navigate(w, 2.0, 0.0);

  EXPECT_NEAR(via_exec.target_linear_x, direct.target_linear_x, 1e-9);
  EXPECT_NEAR(via_exec.target_steering_angle, direct.target_steering_angle, 1e-9);
  EXPECT_NEAR(via_exec.arm_shoulder, direct.arm_shoulder, 1e-9);
}

TEST(SkillExecutorTest, step_navigate_to_box_red_delegates) {
  NavigateSkill nav;
  SkillExecutor executor(nav, ManipulateSkill{});

  const auto w = world_with_red_box(0.0, 0.0);
  const SkillOutput direct = nav.compute_to_box_red(w);
  const SkillOutput via_exec = executor.step_navigate_to_box_red(w);

  EXPECT_NEAR(via_exec.target_linear_x, direct.target_linear_x, 1e-9);
  EXPECT_NEAR(via_exec.target_steering_angle, direct.target_steering_angle, 1e-9);
}

TEST(SkillExecutorTest, step_manipulate_delegates) {
  ManipulateSkill manip;
  SkillExecutor executor(NavigateSkill{}, manip);

  WorldView w;
  w.gripper = 0.0;
  const SkillOutput direct = manip.compute(
      w, ManipulateSkill::Preset::GraspReady, ManipulateSkill::GripperAction::Close);
  const SkillOutput via_exec = executor.step_manipulate(
      w, ManipulateSkill::Preset::GraspReady, ManipulateSkill::GripperAction::Close);

  EXPECT_NEAR(via_exec.arm_shoulder, direct.arm_shoulder, 1e-9);
  EXPECT_NEAR(via_exec.arm_elbow, direct.arm_elbow, 1e-9);
  EXPECT_NEAR(via_exec.arm_wrist, direct.arm_wrist, 1e-9);
  EXPECT_NEAR(via_exec.gripper, direct.gripper, 1e-9);
  EXPECT_NEAR(via_exec.target_linear_x, 0.0, 1e-9);
}

TEST(SkillExecutorTest, default_constructed_executor) {
  SkillExecutor executor;
  const auto w = make_world(0.0, 0.0, 0.0);
  const SkillOutput out = executor.step_navigate_to_box_red(w);
  EXPECT_GT(out.target_linear_x, 0.0);
}
