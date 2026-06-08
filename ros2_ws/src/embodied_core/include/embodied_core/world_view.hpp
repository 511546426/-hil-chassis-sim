#pragma once

#include <optional>
#include <string>
#include <utility>
#include <vector>

namespace embodied_core {

/// 单个可观测物体（通常来自 /world_state 的 object_names + object_poses）
struct ObjectPose {
  std::string name;
  double x{0.0};
  double y{0.0};
  double z{0.0};
};

/// 大脑使用的观测快照（与 ROS 消息解耦）
///
/// 由 chassis_agent_cpp::AgentNode 从 EmbodiedWorldState 填充；
/// FSM / Skill 只读 WorldView，不包含 rclcpp 头文件。
struct WorldView {
  // --- 底盘 ---
  double base_x{0.0}; // 底盘x坐标
  double base_y{0.0}; // 底盘y坐标
  double base_yaw{0.0}; // 底盘yaw
  double base_vx{0.0}; // 底盘vx
  double base_steer{0.0}; // 底盘steer

  // --- 机械臂（实际值，来自 tracker / world_state）---
  double arm_shoulder{0.0};
  double arm_elbow{0.0};
  double arm_wrist{0.0};
  double gripper{0.0};  // 0=张开, 1=闭合

  // --- 场景物体 ---
  std::vector<ObjectPose> objects;

  // --- 接触（M4 后由 simulation_node 填入）---
  bool gripper_touching_object{false}; // 机械臂是否接触物体
  std::string touched_object_name; // 接触物体的名字

  /// 查找 box_red 的 (x, y)；不存在返回 nullopt
  /// 参考：chassis_agent/agent_node.py::_box_red_xy
  [[nodiscard]] std::optional<std::pair<double, double>> box_red_xy() const;

  /// 底盘到 box_red 中心的平面距离 [m]；无 box 返回 nullopt
  /// 参考：chassis_agent/agent_node.py::_distance_to_box
  [[nodiscard]] std::optional<double> distance_to_box_red() const;

  /// 按名字查找物体
  [[nodiscard]] const ObjectPose *find_object(const std::string &name) const;
};

}  // namespace embodied_core
