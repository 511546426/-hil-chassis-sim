#include "embodied_core/push_red_box_fsm.hpp"

#include <gtest/gtest.h>

using namespace embodied_core;

static WorldView world_at_box(double gripper = 0.0, bool touching = false) {
  WorldView w;
  w.base_x = 2.12;
  w.base_y = 0.0;
  w.base_yaw = 0.0;
  w.arm_shoulder = kArmReach.shoulder;
  w.arm_elbow = kArmReach.elbow;
  w.arm_wrist = kArmReach.wrist;
  w.gripper = gripper;
  w.gripper_touching_object = touching;
  w.touched_object_name = touching ? "box_red" : "";
  w.objects.push_back(ObjectPose{"box_red", 2.5, 0.0, 0.18});
  return w;
}

static SkillExecutor make_executor() {
  return SkillExecutor(NavigateSkill(0.35, 0.3), ManipulateSkill{});
}

TEST(PushRedBoxFSMTest, idle_starts_navigation) {
  PushRedBoxFSM fsm;
  SkillExecutor exec = make_executor();
  WorldView w;
  w.objects.push_back(ObjectPose{"box_red", 2.5, 0.0, 0.18});

  const SkillOutput out = fsm.tick(w, exec, 0.02);
  EXPECT_EQ(fsm.phase(), PushRedBoxPhase::NavToRed);
  EXPECT_GT(out.target_linear_x, 0.0);
  ASSERT_TRUE(fsm.take_transition_log().has_value());
}

TEST(PushRedBoxFSMTest, nav_to_reach_when_near_box) {
  PushRedBoxFSM fsm;
  SkillExecutor exec = make_executor();
  WorldView w = world_at_box();

  fsm.tick(w, exec, 0.02);
  ASSERT_EQ(fsm.phase(), PushRedBoxPhase::NavToRed);

  const SkillOutput out = fsm.tick(w, exec, 0.02);
  EXPECT_EQ(fsm.phase(), PushRedBoxPhase::ReachArm);
  EXPECT_NEAR(out.arm_shoulder, kArmReach.shoulder, 1e-9);
  const auto log = fsm.take_transition_log();
  ASSERT_TRUE(log.has_value());
  EXPECT_NE(log->find("NavToRed -> ReachArm"), std::string::npos);
}

TEST(PushRedBoxFSMTest, reach_to_close_when_arm_ready) {
  PushRedBoxFSM fsm;
  SkillExecutor exec = make_executor();
  WorldView w = world_at_box();

  fsm.tick(w, exec, 0.02);
  fsm.tick(w, exec, 0.02);
  ASSERT_EQ(fsm.phase(), PushRedBoxPhase::ReachArm);

  const SkillOutput out = fsm.tick(w, exec, 0.02);
  EXPECT_EQ(fsm.phase(), PushRedBoxPhase::CloseGripper);
  EXPECT_NEAR(out.gripper, 1.0, 1e-9);
}

TEST(PushRedBoxFSMTest, close_without_contact_stays_in_close_gripper) {
  PushRedBoxFSM fsm;
  SkillExecutor exec = make_executor();
  WorldView w = world_at_box(1.0, false);

  for (int i = 0; i < 4; ++i) {
    fsm.tick(w, exec, 0.02);
  }
  EXPECT_EQ(fsm.phase(), PushRedBoxPhase::CloseGripper);
}

TEST(PushRedBoxFSMTest, close_to_back_up_when_gripper_closed_and_touching) {
  PushRedBoxFSM fsm;
  SkillExecutor exec = make_executor();
  WorldView w = world_at_box(1.0, true);

  fsm.tick(w, exec, 0.02);
  fsm.tick(w, exec, 0.02);
  fsm.tick(w, exec, 0.02);
  ASSERT_EQ(fsm.phase(), PushRedBoxPhase::CloseGripper);

  const SkillOutput out = fsm.tick(w, exec, 0.02);
  EXPECT_EQ(fsm.phase(), PushRedBoxPhase::BackUp);
  EXPECT_LT(out.target_linear_x, 0.0);
  EXPECT_TRUE(fsm.should_enable_virtual_grasp());
}

TEST(PushRedBoxFSMTest, back_up_to_done_when_box_moved_enough) {
  PushRedBoxFSM::Config cfg;
  cfg.push_min_dist = 0.20;
  PushRedBoxFSM fsm(cfg);
  SkillExecutor exec = make_executor();
  WorldView w = world_at_box(1.0, true);

  for (int i = 0; i < 4; ++i) {
    fsm.tick(w, exec, 0.02);
  }
  ASSERT_EQ(fsm.phase(), PushRedBoxPhase::BackUp);

  w.objects[0].x = 2.29;
  fsm.tick(w, exec, 0.02);
  EXPECT_EQ(fsm.phase(), PushRedBoxPhase::Done);
  EXPECT_TRUE(fsm.should_disable_virtual_grasp());
  const auto log = fsm.take_transition_log();
  ASSERT_TRUE(log.has_value());
  EXPECT_NE(log->find("box moved"), std::string::npos);
}

TEST(PushRedBoxFSMTest, back_up_waits_until_push_min_dist) {
  PushRedBoxFSM::Config cfg;
  cfg.push_min_dist = 0.20;
  PushRedBoxFSM fsm(cfg);
  SkillExecutor exec = make_executor();
  WorldView w = world_at_box(1.0, true);

  for (int i = 0; i < 4; ++i) {
    fsm.tick(w, exec, 0.02);
  }
  ASSERT_EQ(fsm.phase(), PushRedBoxPhase::BackUp);

  w.objects[0].x = 2.40;
  fsm.tick(w, exec, 0.02);
  EXPECT_EQ(fsm.phase(), PushRedBoxPhase::BackUp);

  w.objects[0].x = 2.29;
  fsm.tick(w, exec, 0.02);
  EXPECT_EQ(fsm.phase(), PushRedBoxPhase::Done);
}
