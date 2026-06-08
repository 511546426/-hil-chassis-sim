#pragma once

#include "embodied_core/navigation.hpp"
#include "embodied_core/skill_output.hpp"
#include "embodied_core/world_view.hpp"

namespace embodied_core {

/// 导航技能：把「去哪」变成底盘 vx/steer，不负责机械臂与 FSM
class NavigateSkill {
 public:
  explicit NavigateSkill(
      double standoff = 0.35,
      double arrive_dist = 0.3,
      double max_vx_reverse = 0.35);

  [[nodiscard]] SkillOutput compute(
      const WorldView &world,
      double target_x, double target_y,
      bool reverse = false) const;

  [[nodiscard]] SkillOutput compute_to_box_red(
      const WorldView &world,
      bool reverse = false) const;

  [[nodiscard]] double standoff() const { return standoff_; }
  [[nodiscard]] double arrive_dist() const { return arrive_dist_; }

 private:
  [[nodiscard]] SkillOutput make_output(const NavigationCommand &nav) const;

  double standoff_;
  double arrive_dist_;
  double max_vx_reverse_;
};

}  // namespace embodied_core
