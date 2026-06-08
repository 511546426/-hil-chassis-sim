#pragma once

#include <cstdint>

#include "embodied_core/arm_preset.hpp"
#include "embodied_core/skill_output.hpp"
#include "embodied_core/world_view.hpp"

namespace embodied_core {

/// 操作技能：臂姿预设 + 夹爪，底盘速度置零
class ManipulateSkill {
 public:
  enum class Preset : uint8_t { Stow, Reach, GraspReady };
  enum class GripperAction : uint8_t { Hold, Open, Close };

  [[nodiscard]] SkillOutput compute(
      const WorldView &world,
      Preset preset,
      GripperAction action) const;

  [[nodiscard]] static bool arm_at_preset(
      const WorldView &world,
      Preset preset,
      double tol = 0.08);

  [[nodiscard]] static bool gripper_at(
      const WorldView &world,
      double target,
      double tol = 0.05);

  [[nodiscard]] static ArmPreset preset_to_arm(Preset preset);
  [[nodiscard]] static double gripper_target(GripperAction action, const WorldView &world);
};

}  // namespace embodied_core
