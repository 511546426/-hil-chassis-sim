#pragma once

#include <cstdint>
#include <optional>
#include <string>

#include "embodied_core/skill_executor.hpp"
#include "embodied_core/skill_output.hpp"
#include "embodied_core/world_view.hpp"

namespace embodied_core {

enum class PushRedBoxPhase : uint8_t {
  Idle,
  NavToRed,
  ReachArm,
  CloseGripper,
  BackUp,
  Done,
  Failed,
};

/// 推红箱任务状态机（M4：CloseGripper 需夹爪闭合且 gripper_touching_object）
class PushRedBoxFSM {
 public:
  struct Config {
    double standoff{0.35};
    double arrive_dist{0.3};
    double push_min_dist{0.20};
    double max_vx_reverse{0.35};
    double phase_timeout_nav{60.0};
    double phase_timeout_reach{15.0};
    double phase_timeout_gripper{15.0};
    double phase_timeout_back_up{15.0};
    double arm_tol{0.08};
    double gripper_tol{0.05};
  };

  PushRedBoxFSM();
  explicit PushRedBoxFSM(const Config &config);

  /// 根据当前阶段调用 SkillExecutor，检查转移，返回本帧控制输出
  [[nodiscard]] SkillOutput tick(
      const WorldView &world,
      SkillExecutor &executor,
      double dt_sec);

  [[nodiscard]] PushRedBoxPhase phase() const { return phase_; }
  [[nodiscard]] const char *phase_name() const;

  /// M5：进入 BackUp 时应请求 virtual attach
  [[nodiscard]] bool should_enable_virtual_grasp() const;

  /// M5：Done / Failed 时应释放 attach
  [[nodiscard]] bool should_disable_virtual_grasp() const;

  /// 取走上次状态转移日志（供 agent_node 打印一次）
  [[nodiscard]] std::optional<std::string> take_transition_log();

  void reset();

  /// P3-M4：RL 导航完成后，从 ReachArm 阶段开始规则操作
  void begin_manipulate_after_nav();

 private:
  [[nodiscard]] bool navigation_complete(
      const WorldView &world,
      const SkillOutput &out) const;

  void transition(PushRedBoxPhase next, const char *reason);
  void capture_box_push_origin(const WorldView &world);
  [[nodiscard]] double box_push_distance(const WorldView &world) const;
  [[nodiscard]] SkillOutput idle_output() const;
  [[nodiscard]] SkillOutput hold_output(const SkillOutput &last) const;

  Config config_;
  PushRedBoxPhase phase_{PushRedBoxPhase::Idle};
  double phase_time_{0.0};
  bool virtual_grasp_request_{false};
  bool virtual_grasp_release_{false};
  bool has_box_push_origin_{false};
  double box_x0_{0.0};
  double box_y0_{0.0};
  SkillOutput last_output_{};
  std::optional<std::string> pending_log_;
};

}  // namespace embodied_core
