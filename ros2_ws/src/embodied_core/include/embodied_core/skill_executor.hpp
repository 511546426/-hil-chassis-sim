#pragma once

#include "embodied_core/manipulate_skill.hpp"
#include "embodied_core/navigate_skill.hpp"
#include "embodied_core/skill_output.hpp"
#include "embodied_core/world_view.hpp"

namespace embodied_core {

/// 技能组合器：FSM 通过 Executor 调用导航/操作，不直接持有多个 Skill 细节
class SkillExecutor {
 public:
  SkillExecutor() = default;
  explicit SkillExecutor(NavigateSkill navigate, ManipulateSkill manipulate);

  [[nodiscard]] SkillOutput step_navigate(
      const WorldView &world,
      double target_x, double target_y,
      bool reverse = false) const;

  [[nodiscard]] SkillOutput step_navigate_to_box_red(
      const WorldView &world,
      bool reverse = false) const;

  [[nodiscard]] SkillOutput step_manipulate(
      const WorldView &world,
      ManipulateSkill::Preset preset,
      ManipulateSkill::GripperAction action) const;

  [[nodiscard]] const NavigateSkill &navigate() const { return navigate_; }
  [[nodiscard]] const ManipulateSkill &manipulate() const { return manipulate_; }

 private:
  NavigateSkill navigate_{};
  ManipulateSkill manipulate_{};
};

}  // namespace embodied_core
