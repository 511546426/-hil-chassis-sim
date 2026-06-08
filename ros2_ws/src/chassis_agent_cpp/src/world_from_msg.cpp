#include "chassis_agent_cpp/world_from_msg.hpp"

#include <cstddef>

namespace chassis_agent_cpp {

embodied_core::WorldView world_from_msg(
    const embodied_msgs::msg::EmbodiedWorldState &msg) {
  embodied_core::WorldView w;

  w.base_x = msg.base_x;
  w.base_y = msg.base_y;
  w.base_yaw = msg.base_yaw;
  w.base_vx = msg.base_vx;
  w.base_steer = msg.base_steer;

  w.arm_shoulder = msg.arm_shoulder;
  w.arm_elbow = msg.arm_elbow;
  w.arm_wrist = msg.arm_wrist;
  w.gripper = msg.gripper;

  const std::size_t n = msg.object_names.size();
  w.objects.reserve(n);
  for (std::size_t i = 0; i < n; ++i) {
    embodied_core::ObjectPose obj;
    obj.name = msg.object_names[i];
    if (i < msg.object_poses.size()) {
      obj.x = msg.object_poses[i].position.x;
      obj.y = msg.object_poses[i].position.y;
      obj.z = msg.object_poses[i].position.z;
    }
    w.objects.push_back(std::move(obj));
  }

  w.gripper_touching_object = msg.gripper_touching_object;
  w.touched_object_name = msg.touched_object_name;

  return w;
}

}  // namespace chassis_agent_cpp
