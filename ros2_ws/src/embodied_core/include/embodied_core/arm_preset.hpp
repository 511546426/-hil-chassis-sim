#pragma once

namespace embodied_core {

/// 机械臂关节角预设（弧度），与 Python arm_presets.py / BRAIN_ROADMAP 一致
struct ArmPreset {
  double shoulder{};
  double elbow{};
  double wrist{};
};

inline constexpr ArmPreset kArmStow{0.35, 0.0, 0.25};
inline constexpr ArmPreset kArmReach{0.55, 0.4, 0.3};
inline constexpr ArmPreset kArmGraspReady{0.45, 0.6, 0.2};

}  // namespace embodied_core
