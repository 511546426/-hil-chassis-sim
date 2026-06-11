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

}  // namespace embodied_core
