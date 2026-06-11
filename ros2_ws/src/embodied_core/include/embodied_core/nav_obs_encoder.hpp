#pragma once

#include <array>

#include "embodied_core/nav_obs_spec.hpp"
#include "embodied_core/task_goal.hpp"
#include "embodied_core/world_view.hpp"

namespace embodied_core {

using NavObservation = std::array<double, kNavObsDim>;

/// 将 WorldView + TaskGoal 编码为归一化导航观测向量
[[nodiscard]] NavObservation encode_nav_obs(
    const WorldView &world,
    const TaskGoal &goal);

/// standoff 后的有效目标距离 [m]（与 encode_nav_obs 中 dist 一致）
[[nodiscard]] double nav_goal_distance(
    const WorldView &world,
    const TaskGoal &goal);

}  // namespace embodied_core
