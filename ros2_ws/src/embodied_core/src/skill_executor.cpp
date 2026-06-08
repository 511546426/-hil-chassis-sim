#include "embodied_core/skill_executor.hpp"

namespace embodied_core {

SkillExecutor::SkillExecutor(NavigateSkill navigate, ManipulateSkill manipulate)
    : navigate_(std::move(navigate)),
      manipulate_(std::move(manipulate)) {}

SkillOutput SkillExecutor::step_navigate(
    const WorldView &world,
    double target_x, double target_y,
    bool reverse) const {
  return navigate_.compute(world, target_x, target_y, reverse);
}

SkillOutput SkillExecutor::step_navigate_to_box_red(
    const WorldView &world,
    bool reverse) const {
  return navigate_.compute_to_box_red(world, reverse);
}

SkillOutput SkillExecutor::step_manipulate(
    const WorldView &world,
    ManipulateSkill::Preset preset,
    ManipulateSkill::GripperAction action) const {
  return manipulate_.compute(world, preset, action);
}

}  // namespace embodied_core
