#pragma once

#include "embodied_core/world_view.hpp"

namespace embodied_core {

/// @brief 底盘导航一帧的控制输出（仅 vx / steer，不含机械臂）
///
/// 由 pure_pursuit() 生成，供 NavigateSkill 填入 SkillOutput。
/// 坐标系与 simulation_node 一致：世界系 x/y，yaw 绕 z 轴逆时针为正 [rad]。
struct NavigationCommand {
  /// 目标线速度 [m/s]。前进为正，后退为负；到达时恒为 0
  double target_linear_x{0.0};

  /// 目标前轮转向角 [rad]。与 EmbodiedCommand.target_steering_angle 同义；
  /// 正值/负值对应 controller 中 a/d 转向方向，幅度受 max_steer 限制
  double target_steering_angle{0.0};

  /// 是否已视为到达目标：平面距离 < arrive_dist 时为 true；
  /// 为 true 时 vx、steer 均为 0，调用方应停车并切换下一阶段（如伸臂）
  bool arrived{false};
};

/// @brief 将任意弧度角归一化到 (-π, π]
///
/// @param angle  输入角 [rad]，可为任意实数
/// @return       等价角，范围 (-π, π]；用于计算航向误差，避免 ±2π 跳变
///
/// @note 边界：+π 与 -π 不等价处理时，+π 会保留为 π（与 Python 版一致）
double normalize_angle(double angle);

/// @brief 在目标点沿「机器人→目标」方向前，留出 standoff 停靠点
///
/// 用于导航到物体（如红箱）时，不把车开到物体几何中心，而在外侧 stop。
///
/// @param[in]  base_x, base_y     机器人当前平面位置 [m]
/// @param[in]  target_x, target_y  目标点（通常为物体中心或路点）[m]
/// @param[in]  standoff           在目标前保留的距离 [m]，典型 0.35
/// @param[out] out_x, out_y       计算得到的导航子目标 [m]
///
/// 几何含义：
///   - 若 base 与 target 距离 > standoff：out 在连线 segment 上，
///     距 target 恰好 standoff（即「靠近目标但还差 standoff 停住」）
///   - 若距离 < 1e-3（几乎重合）：退化为 (target_x - standoff, target_y)
///
/// @note 仅修改 out_x/out_y，无返回值；由 NavigateSkill::compute() 在
///       调用 pure_pursuit 前使用，避免重复 standoff 时请传物体中心而非已偏移点
void approach_point(
    double base_x, double base_y,
    double target_x, double target_y,
    double standoff,
    double &out_x, double &out_y);

/// @brief Pure Pursuit 几何跟踪：根据当前位姿与目标点，输出本帧底盘指令
///
/// 算法概要（与 chassis_agent/navigation.py::pure_pursuit 一致）：
///   1. 若到目标平面距离 < arrive_dist → 停车并 arrived=true
///   2. 计算目标方位 target_heading = atan2(dy, dx)
///   3. 航向误差 heading_err = normalize_angle(target_heading - yaw)
///   4. 选取前视点：距目标较远时沿目标方向前探 look_ahead，否则用目标点
///   5. 将前视点变换到车体坐标系，用横向偏差 local_y 估计曲率
///   6. steer = atan(curvature * wheelbase)，并限幅到 ±max_steer
///   7. vx = max_vx * max(0.5, cos(heading_err))；大航向误差时再减半速
///
/// @param[in] x, y           机器人当前世界坐标 [m]
/// @param[in] yaw            当前航向角 [rad]，0 为 +x 方向
/// @param[in] target_x, target_y  跟踪目标点 [m]（常由 approach_point 预处理）
/// @param[in] arrive_dist    到达半径 [m]，默认 0.3；进入则 arrived=true
/// @param[in] look_ahead     前视距离 [m]，默认 0.8；影响转弯平滑度
/// @param[in] max_vx         最大前进线速度 [m/s]，默认 1.0
/// @param[in] max_steer      最大转向角 [rad]，默认 0.52（与模型 MAX_STEER_ANGLE 一致）
/// @param[in] wheelbase      轴距 [m]，默认 0.32；曲率转 steer 用
///
/// @return NavigationCommand
///   - arrived=false：target_linear_x ∈ (0, max_vx]，target_steering_angle ∈ [-max_steer, max_steer]
///   - arrived=true ：vx=0, steer=0，调用方应停止导航阶段
///
/// @note 本函数只管几何跟踪，不处理碰撞、倒车、机械臂；倒车由 NavigateSkill(reverse=true) 另行处理
/// @note 仅被 NavigateSkill 调用，FSM 不应直接调用
NavigationCommand pure_pursuit(
    double x, double y, double yaw,
    double target_x, double target_y,
    double arrive_dist = 0.3,
    double look_ahead = 0.8,
    double max_vx = 1.0,
    double max_steer = 0.52,
    double wheelbase = 0.32);

/// @brief 判断导航到红箱时是否「顶死」——命令在前进但实际几乎不动
///
/// 当 pure_pursuit 仍输出前进速度，但仿真中底盘被箱子挡住时，用本函数
/// 代替 arrived，提前结束 NAV 阶段（与 Python agent_node._stuck_at_box 一致）。
///
/// @param[in] world   当前观测；使用 base_x/base_y/base_vx 与 box_red 距离
/// @param[in] cmd_vx  本帧 pure_pursuit 输出的 target_linear_x [m/s]
///
/// @return true 表示应视为到达红箱前，条件之一：
///   - 距 box_red ≤ 0.52 m 且 cmd_vx > 0.05
///   - cmd_vx > 0.15 且 |base_vx| < 0.05 且距 box_red < 0.75 m（命令在走、实际不动）
///   false：无 box_red、或仍在正常接近过程中
///
/// @note 由 FSM / agent_node 在 NavToRed 阶段与 nav.arrived 一起做 OR 判断
bool stuck_at_box(const WorldView &world, double cmd_vx);

}  // namespace embodied_core
