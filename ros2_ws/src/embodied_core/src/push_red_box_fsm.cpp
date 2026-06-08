#include "embodied_core/push_red_box_fsm.hpp"

#include <cmath>
#include <sstream>

#include "embodied_core/arm_preset.hpp"
#include "embodied_core/manipulate_skill.hpp"
#include "embodied_core/navigation.hpp"

namespace embodied_core {

namespace {

const char *phase_to_string(PushRedBoxPhase phase) {
  switch (phase) {
    case PushRedBoxPhase::Idle:
      return "Idle";
    case PushRedBoxPhase::NavToRed:
      return "NavToRed";
    case PushRedBoxPhase::ReachArm:
      return "ReachArm";
    case PushRedBoxPhase::CloseGripper:
      return "CloseGripper";
    case PushRedBoxPhase::BackUp:
      return "BackUp";
    case PushRedBoxPhase::Done:
      return "Done";
    case PushRedBoxPhase::Failed:
      return "Failed";
  }
  return "Unknown";
}

}  // namespace

PushRedBoxFSM::PushRedBoxFSM() : PushRedBoxFSM(Config{}) {}

PushRedBoxFSM::PushRedBoxFSM(const Config &config) : config_(config) {
  last_output_.arm_shoulder = kArmStow.shoulder;
  last_output_.arm_elbow = kArmStow.elbow;
  last_output_.arm_wrist = kArmStow.wrist;
  last_output_.gripper = 0.0;
}

void PushRedBoxFSM::reset() {
  phase_ = PushRedBoxPhase::Idle;
  phase_time_ = 0.0;
  virtual_grasp_request_ = false;
  virtual_grasp_release_ = false;
  pending_log_.reset();
}

const char *PushRedBoxFSM::phase_name() const {
  return phase_to_string(phase_);
}

std::optional<std::string> PushRedBoxFSM::take_transition_log() {
  if (!pending_log_) {
    return std::nullopt;
  }
  auto msg = std::move(*pending_log_);
  pending_log_.reset();
  return msg;
}

bool PushRedBoxFSM::should_enable_virtual_grasp() const {
  return virtual_grasp_request_;
}

bool PushRedBoxFSM::should_disable_virtual_grasp() const {
  return virtual_grasp_release_;
}

void PushRedBoxFSM::transition(PushRedBoxPhase next, const char *reason) {
  if (phase_ == next) {
    return;
  }
  std::ostringstream oss;
  oss << "FSM " << phase_to_string(phase_) << " -> " << phase_to_string(next)
      << ": " << reason;
  pending_log_ = oss.str();
  phase_ = next;
  phase_time_ = 0.0;

  virtual_grasp_request_ = (next == PushRedBoxPhase::BackUp);
  virtual_grasp_release_ =
      (next == PushRedBoxPhase::Done || next == PushRedBoxPhase::Failed);
}

bool PushRedBoxFSM::navigation_complete(
    const WorldView &world,
    const SkillOutput &out) const {
  if (stuck_at_box(world, out.target_linear_x)) {
    return true;
  }
  const auto dist = world.distance_to_box_red();
  if (!dist) {
    return false;
  }
  return *dist <= config_.standoff + config_.arrive_dist;
}

SkillOutput PushRedBoxFSM::idle_output() const {
  SkillOutput out;
  out.arm_shoulder = kArmStow.shoulder;
  out.arm_elbow = kArmStow.elbow;
  out.arm_wrist = kArmStow.wrist;
  out.gripper = 0.0;
  return out;
}

SkillOutput PushRedBoxFSM::hold_output(const SkillOutput &last) const {
  SkillOutput out = last;
  out.target_linear_x = 0.0;
  out.target_steering_angle = 0.0;
  out.emergency_brake = false;
  return out;
}

SkillOutput PushRedBoxFSM::tick(
    const WorldView &world,
    SkillExecutor &executor,
    double dt_sec) {
  phase_time_ += dt_sec;
  virtual_grasp_request_ = false;
  virtual_grasp_release_ = false;

  switch (phase_) {
    case PushRedBoxPhase::Idle:
      transition(PushRedBoxPhase::NavToRed, "world_state ready");
      last_output_ = executor.step_navigate_to_box_red(world, false);
      break;

    case PushRedBoxPhase::NavToRed: {
      last_output_ = executor.step_navigate_to_box_red(world, false);
      if (navigation_complete(world, last_output_)) {
        std::ostringstream reason;
        const auto dist = world.distance_to_box_red();
        reason << "arrived dist=";
        if (dist) {
          reason << *dist;
        } else {
          reason << "n/a";
        }
        transition(PushRedBoxPhase::ReachArm, reason.str().c_str());
        last_output_ = executor.step_manipulate(
            world,
            ManipulateSkill::Preset::Reach,
            ManipulateSkill::GripperAction::Open);
      } else if (phase_time_ > config_.phase_timeout_nav) {
        transition(PushRedBoxPhase::Failed, "nav timeout");
        last_output_ = hold_output(last_output_);
      }
      break;
    }

    case PushRedBoxPhase::ReachArm: {
      last_output_ = executor.step_manipulate(
          world,
          ManipulateSkill::Preset::Reach,
          ManipulateSkill::GripperAction::Open);
      if (ManipulateSkill::arm_at_preset(
              world, ManipulateSkill::Preset::Reach, config_.arm_tol)) {
        transition(PushRedBoxPhase::CloseGripper, "arm at REACH");
        last_output_ = executor.step_manipulate(
            world,
            ManipulateSkill::Preset::Reach,
            ManipulateSkill::GripperAction::Close);
      } else if (phase_time_ > config_.phase_timeout_reach) {
        transition(PushRedBoxPhase::Failed, "reach arm timeout");
        last_output_ = hold_output(last_output_);
      }
      break;
    }

    case PushRedBoxPhase::CloseGripper: {
      last_output_ = executor.step_manipulate(
          world,
          ManipulateSkill::Preset::Reach,
          ManipulateSkill::GripperAction::Close);
      if (ManipulateSkill::gripper_at(world, 1.0, config_.gripper_tol)
          && world.gripper_touching_object) {
        transition(PushRedBoxPhase::BackUp, "gripper closed with contact");
        last_output_ = executor.step_navigate_to_box_red(world, true);
      } else if (phase_time_ > config_.phase_timeout_gripper) {
        transition(PushRedBoxPhase::Failed, "close gripper timeout");
        last_output_ = hold_output(last_output_);
      }
      break;
    }

    case PushRedBoxPhase::BackUp: {
      // M3：倒车占位（M5 attach 后 M6 用位移判据结束）
      last_output_ = executor.step_navigate_to_box_red(world, true);
      if (phase_time_ >= config_.back_up_hold_sec) {
        transition(PushRedBoxPhase::Done, "back up hold complete (M3)");
        last_output_ = hold_output(last_output_);
      }
      break;
    }

    case PushRedBoxPhase::Done:
    case PushRedBoxPhase::Failed:
      last_output_ = hold_output(last_output_);
      break;
  }

  return last_output_;
}

}  // namespace embodied_core
