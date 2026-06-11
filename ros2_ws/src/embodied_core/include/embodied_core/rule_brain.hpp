#pragma once

#include <optional>
#include <string>

#include "embodied_core/brain.hpp"
#include "embodied_core/push_red_box_fsm.hpp"
#include "embodied_core/skill_executor.hpp"

namespace embodied_core {

/// 规则大脑：包装 PushRedBoxFSM + SkillExecutor（第二期 Teacher / Baseline）
class RuleBrain : public Brain {
 public:
  struct Config {
    PushRedBoxFSM::Config fsm;
    double standoff{0.35};
    double arrive_dist{0.3};
  };

  RuleBrain();
  explicit RuleBrain(const Config &config);

  void reset(const TaskGoal &goal) override;

  SkillOutput act(const WorldView &world, double dt_sec) override;

  [[nodiscard]] std::optional<std::string> take_transition_log() override;

  [[nodiscard]] const char *phase_name() const override;

  [[nodiscard]] bool should_enable_virtual_grasp() const override;

  [[nodiscard]] bool should_disable_virtual_grasp() const override;

 private:
  Config config_;
  SkillExecutor executor_;
  PushRedBoxFSM fsm_;
};

}  // namespace embodied_core
