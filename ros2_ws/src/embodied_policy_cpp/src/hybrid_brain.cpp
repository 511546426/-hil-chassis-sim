#include "embodied_policy_cpp/hybrid_brain.hpp"

#include <embodied_core/navigation.hpp>

namespace embodied_policy_cpp {

namespace {

bool hybrid_nav_complete(
    const embodied_core::WorldView &world,
    const embodied_core::SkillOutput &out,
    const embodied_core::PushRedBoxFSM::Config &fsm_cfg) {
  if (embodied_core::stuck_at_box(world, out.target_linear_x)) {
    return true;
  }
  const auto dist = world.distance_to_box_red();
  return dist.has_value() && *dist <= fsm_cfg.standoff + fsm_cfg.arrive_dist;
}

}  // namespace

HybridBrain::HybridBrain(const Config &config)
    : config_(config),
      rl_brain_(config.rl),
      executor_(
          embodied_core::NavigateSkill(
              config.fsm.standoff,
              config.fsm.arrive_dist),
          embodied_core::ManipulateSkill{}),
      fsm_(config.fsm) {}

void HybridBrain::reset(const embodied_core::TaskGoal &goal) {
  rl_brain_.reset(goal);
  fsm_.reset();
  rl_nav_phase_ = true;
  pending_log_.reset();
}

const char *HybridBrain::phase_name() const {
  if (rl_nav_phase_) {
    return "Hybrid/RLNav";
  }
  return fsm_.phase_name();
}

std::optional<std::string> HybridBrain::take_transition_log() {
  if (pending_log_) {
    auto msg = std::move(*pending_log_);
    pending_log_.reset();
    return msg;
  }
  return fsm_.take_transition_log();
}

bool HybridBrain::should_enable_virtual_grasp() const {
  if (rl_nav_phase_) {
    return false;
  }
  return fsm_.should_enable_virtual_grasp();
}

bool HybridBrain::should_disable_virtual_grasp() const {
  if (rl_nav_phase_) {
    return false;
  }
  return fsm_.should_disable_virtual_grasp();
}

embodied_core::SkillOutput HybridBrain::act(
    const embodied_core::WorldView &world,
    double dt_sec) {
  if (rl_nav_phase_) {
    auto out = rl_brain_.act(world, dt_sec);
    if (hybrid_nav_complete(world, out, config_.fsm)) {
      rl_nav_phase_ = false;
      fsm_.begin_manipulate_after_nav();
      pending_log_ = "Hybrid RLNav -> Manipulate: navigation complete";
    }
    return out;
  }
  return fsm_.tick(world, executor_, dt_sec);
}

}  // namespace embodied_policy_cpp
