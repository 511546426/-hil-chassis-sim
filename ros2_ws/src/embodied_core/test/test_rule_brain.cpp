#include "embodied_core/rule_brain.hpp"

#include <gtest/gtest.h>

#include "embodied_core/arm_preset.hpp"

using namespace embodied_core;

static WorldView world_at_box(double gripper = 0.0, bool touching = false) {
  WorldView world;
  world.base_x = 2.12;
  world.base_y = 0.0;
  world.base_yaw = 0.0;
  world.arm_shoulder = kArmReach.shoulder;
  world.arm_elbow = kArmReach.elbow;
  world.arm_wrist = kArmReach.wrist;
  world.gripper = gripper;
  world.gripper_touching_object = touching;
  world.touched_object_name = touching ? "box_red" : "";
  world.objects.push_back(ObjectPose{"box_red", 2.5, 0.0, 0.18});
  return world;
}

TEST(RuleBrainTest, reset_starts_idle_then_navigates) {
  RuleBrain brain;
  brain.reset(TaskGoal::push_red_box());

  WorldView world;
  world.objects.push_back(ObjectPose{"box_red", 2.5, 0.0, 0.18});

  const SkillOutput out = brain.act(world, 0.02);
  EXPECT_GT(out.target_linear_x, 0.0);
  EXPECT_STREQ(brain.phase_name(), "NavToRed");
}

TEST(RuleBrainTest, matches_fsm_tick_output) {
  RuleBrain::Config cfg;
  RuleBrain brain(cfg);

  PushRedBoxFSM fsm(cfg.fsm);
  SkillExecutor exec(
      NavigateSkill(cfg.standoff, cfg.arrive_dist),
      ManipulateSkill{});

  WorldView world = world_at_box(1.0, true);
  brain.reset(TaskGoal::push_red_box());
  fsm.reset();

  for (int i = 0; i < 6; ++i) {
    const SkillOutput from_brain = brain.act(world, 0.02);
    const SkillOutput from_fsm = fsm.tick(world, exec, 0.02);
    EXPECT_NEAR(from_brain.target_linear_x, from_fsm.target_linear_x, 1e-9);
    EXPECT_NEAR(
        from_brain.target_steering_angle,
        from_fsm.target_steering_angle,
        1e-9);
    EXPECT_NEAR(from_brain.gripper, from_fsm.gripper, 1e-9);
    (void)brain.take_transition_log();
    (void)fsm.take_transition_log();
  }
}

TEST(RuleBrainTest, virtual_grasp_flags_follow_fsm) {
  RuleBrain brain;
  brain.reset(TaskGoal::push_red_box());
  WorldView world = world_at_box(1.0, true);

  for (int i = 0; i < 3; ++i) {
    (void)brain.act(world, 0.02);
    (void)brain.take_transition_log();
  }

  const SkillOutput out = brain.act(world, 0.02);
  EXPECT_LT(out.target_linear_x, 0.0);
  EXPECT_STREQ(brain.phase_name(), "BackUp");
  EXPECT_TRUE(brain.should_enable_virtual_grasp());
}
