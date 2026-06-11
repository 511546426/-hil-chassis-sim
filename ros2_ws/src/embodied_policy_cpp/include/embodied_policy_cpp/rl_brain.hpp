#pragma once

#include <optional>
#include <string>

#include <embodied_core/brain.hpp>
#include <embodied_core/task_goal.hpp>

#include "embodied_policy_cpp/onnx_session.hpp"

namespace embodied_policy_cpp {

/// RL 导航大脑：WorldView → NavObs → ONNX → vx/steer
class RLBrain : public embodied_core::Brain {
 public:
  struct Config {
    std::string policy_path;
    embodied_core::TaskGoal goal{
        embodied_core::TaskGoal::nav_to_object("box_red", 0.35)};
    double arrive_dist{0.30};
  };

  explicit RLBrain(const Config &config);

  void reset(const embodied_core::TaskGoal &goal) override;

  embodied_core::SkillOutput act(
      const embodied_core::WorldView &world,
      double dt_sec) override;

  [[nodiscard]] const char *phase_name() const override;

  [[nodiscard]] std::optional<std::string> take_transition_log() override;

  [[nodiscard]] bool has_arrived() const { return arrived_; }

 private:
  Config config_;
  OnnxSession session_;
  embodied_core::TaskGoal goal_;
  bool arrived_{false};
  bool arrival_logged_{false};
};

}  // namespace embodied_policy_cpp
