#pragma once

#include <embodied_msgs/msg/embodied_world_state.hpp>
#include <embodied_core/world_view.hpp>

namespace chassis_agent_cpp {

/// 将 ROS /world_state 转为 embodied_core::WorldView（算法层与 ROS 的唯一转换点）
embodied_core::WorldView world_from_msg(
    const embodied_msgs::msg::EmbodiedWorldState &msg);

}  // namespace chassis_agent_cpp
