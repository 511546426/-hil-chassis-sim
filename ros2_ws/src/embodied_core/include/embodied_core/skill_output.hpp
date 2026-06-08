#pragma once

namespace embodied_core {

/// 技能层一帧的完整控制意图，可映射为 EmbodiedCommand
struct SkillOutput {
  double target_linear_x{0.0};
  double target_steering_angle{0.0};
  double arm_shoulder{0.0};
  double arm_elbow{0.0};
  double arm_wrist{0.0};
  double gripper{0.0};
  bool emergency_brake{false};
};

}  // namespace embodied_core
