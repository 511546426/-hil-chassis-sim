#include "embodied_policy_cpp/rl_brain.hpp"

#include <embodied_core/arm_preset.hpp>
#include <embodied_core/nav_obs_encoder.hpp>
#include <embodied_core/nav_obs_spec.hpp>

namespace embodied_policy_cpp {

RLBrain::RLBrain(const Config &config)
    : config_(config), session_(config.policy_path), goal_(config.goal) {}

void RLBrain::reset(const embodied_core::TaskGoal &goal) { goal_ = goal; }

embodied_core::SkillOutput RLBrain::act(
    const embodied_core::WorldView &world,
    double dt_sec) {
  (void)dt_sec;

  const embodied_core::NavObservation obs =
      embodied_core::encode_nav_obs(world, goal_);

  std::array<float, OnnxSession::kObsDim> obs_f{};
  for (int i = 0; i < embodied_core::kNavObsDim; ++i) {
    obs_f[static_cast<size_t>(i)] = static_cast<float>(obs[static_cast<size_t>(i)]);
  }

  const auto action = session_.run_nav_action(obs_f);

  embodied_core::SkillOutput out;
  out.target_linear_x =
      static_cast<double>(action[0]) * embodied_core::kNavObsMaxVx;
  out.target_steering_angle =
      static_cast<double>(action[1]) * embodied_core::kNavObsMaxSteer;
  out.arm_shoulder = embodied_core::kArmStow.shoulder;
  out.arm_elbow = embodied_core::kArmStow.elbow;
  out.arm_wrist = embodied_core::kArmStow.wrist;
  out.gripper = 0.0;
  out.emergency_brake = false;
  return out;
}

}  // namespace embodied_policy_cpp
