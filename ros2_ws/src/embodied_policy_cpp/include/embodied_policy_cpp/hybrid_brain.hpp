#pragma once

#include <optional>
#include <string>

#include <embodied_core/brain.hpp>
#include <embodied_core/push_red_box_fsm.hpp>
#include <embodied_core/skill_executor.hpp>
#include <embodied_core/task_goal.hpp>

#include "embodied_policy_cpp/rl_brain.hpp"

namespace embodied_policy_cpp {

/// 分层大脑：RL 导航 + PushRedBoxFSM 操作段（ReachArm → 推箱）
class HybridBrain : public embodied_core::Brain {
 public:
  struct Config {
    RLBrain::Config rl;
    embodied_core::PushRedBoxFSM::Config fsm;
  };

  explicit HybridBrain(const Config &config);

  void reset(const embodied_core::TaskGoal &goal) override;

  embodied_core::SkillOutput act(
      const embodied_core::WorldView &world,
      double dt_sec) override;

  [[nodiscard]] std::optional<std::string> take_transition_log() override;

  [[nodiscard]] const char *phase_name() const override;

  [[nodiscard]] bool should_enable_virtual_grasp() const override;

  [[nodiscard]] bool should_disable_virtual_grasp() const override;

  [[nodiscard]] bool in_rl_nav_phase() const { return rl_nav_phase_; }

 private:
  Config config_;
  RLBrain rl_brain_;
  embodied_core::SkillExecutor executor_;
  embodied_core::PushRedBoxFSM fsm_;
  bool rl_nav_phase_{true};
  std::optional<std::string> pending_log_;
};

}  // namespace embodied_policy_cpp
