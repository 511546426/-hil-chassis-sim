#include "embodied_core/rule_brain.hpp"

namespace embodied_core {

RuleBrain::RuleBrain() : RuleBrain(Config{}) {}

RuleBrain::RuleBrain(const Config &config)
    : config_(config),
      executor_(
          NavigateSkill(config.standoff, config.arrive_dist),
          ManipulateSkill{}),
      fsm_(config.fsm) {}

void RuleBrain::reset(const TaskGoal &goal) {
  (void)goal;
  fsm_.reset();
}

SkillOutput RuleBrain::act(const WorldView &world, double dt_sec) {
  return fsm_.tick(world, executor_, dt_sec);
}

std::optional<std::string> RuleBrain::take_transition_log() {
  return fsm_.take_transition_log();
}

const char *RuleBrain::phase_name() const { return fsm_.phase_name(); }

bool RuleBrain::should_enable_virtual_grasp() const {
  return fsm_.should_enable_virtual_grasp();
}

bool RuleBrain::should_disable_virtual_grasp() const {
  return fsm_.should_disable_virtual_grasp();
}

}  // namespace embodied_core
