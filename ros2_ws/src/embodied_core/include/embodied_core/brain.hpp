#pragma once

#include <optional>
#include <string>

#include "embodied_core/skill_output.hpp"
#include "embodied_core/task_goal.hpp"
#include "embodied_core/world_view.hpp"

namespace embodied_core {

/// 可插拔大脑接口（第三期：RuleBrain / RLBrain）
class Brain {
 public:
  virtual ~Brain() = default;

  virtual void reset(const TaskGoal &goal) = 0;

  virtual SkillOutput act(const WorldView &world, double dt_sec) = 0;

  [[nodiscard]] virtual std::optional<std::string> take_transition_log() {
    return std::nullopt;
  }

  [[nodiscard]] virtual const char *phase_name() const { return "Unknown"; }

  [[nodiscard]] virtual bool should_enable_virtual_grasp() const { return false; }

  [[nodiscard]] virtual bool should_disable_virtual_grasp() const { return false; }
};

}  // namespace embodied_core
