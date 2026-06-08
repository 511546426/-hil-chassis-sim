#include "embodied_core/manipulate_skill.hpp"

#include <cmath>

namespace embodied_core {

ArmPreset ManipulateSkill::preset_to_arm(Preset preset) {
  switch (preset) {
    case Preset::Stow:
      return kArmStow;
    case Preset::Reach:
      return kArmReach;
    case Preset::GraspReady:
      return kArmGraspReady;
  }
  return kArmStow;
}

double ManipulateSkill::gripper_target(GripperAction action, const WorldView &world) {
  switch (action) {
    case GripperAction::Open:
      return 0.0;
    case GripperAction::Close:
      return 1.0;
    case GripperAction::Hold:
      return world.gripper;
  }
  return world.gripper;
}

SkillOutput ManipulateSkill::compute(
    const WorldView &world,
    Preset preset,
    GripperAction action) const {
  (void)world;

  const ArmPreset arm = preset_to_arm(preset);
  SkillOutput out;
  out.target_linear_x = 0.0;
  out.target_steering_angle = 0.0;
  out.arm_shoulder = arm.shoulder;
  out.arm_elbow = arm.elbow;
  out.arm_wrist = arm.wrist;
  out.gripper = gripper_target(action, world);
  out.emergency_brake = false;
  return out;
}

bool ManipulateSkill::arm_at_preset(
    const WorldView &world,
    Preset preset,
    double tol) {
  const ArmPreset target = preset_to_arm(preset);
  return std::abs(world.arm_shoulder - target.shoulder) <= tol
      && std::abs(world.arm_elbow - target.elbow) <= tol
      && std::abs(world.arm_wrist - target.wrist) <= tol;
}

bool ManipulateSkill::gripper_at(
    const WorldView &world,
    double target,
    double tol) {
  return std::abs(world.gripper - target) <= tol;
}

}  // namespace embodied_core
