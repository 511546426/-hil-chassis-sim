#pragma once

namespace embodied_core {

/// 导航 RL 观测/动作契约（C++ 单一真相；Python Gym 读 configs/rl/nav_obs_spec.json）
inline constexpr double kNavObsArenaHalf = 15.0;
inline constexpr double kNavObsGoalScale = 5.0;
inline constexpr double kNavObsMaxVx = 1.0;
inline constexpr double kNavObsMaxSteer = 0.52;
inline constexpr int kNavObsDim = 8;
inline constexpr int kNavActionDim = 2;

enum NavObsIndex : int {
  kObsBaseX = 0,
  kObsBaseY = 1,
  kObsBaseYaw = 2,
  kObsGoalDx = 3,
  kObsGoalDy = 4,
  kObsDistGoal = 5,
  kObsBaseVx = 6,
  kObsBaseSteerAbs = 7,
};

}  // namespace embodied_core
