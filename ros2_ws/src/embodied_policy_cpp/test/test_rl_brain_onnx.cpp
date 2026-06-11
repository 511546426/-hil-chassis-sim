#include "embodied_policy_cpp/onnx_session.hpp"
#include "embodied_policy_cpp/rl_brain.hpp"

#include <cmath>
#include <filesystem>
#include <gtest/gtest.h>

#include "onnx_test_vectors.hpp"

namespace {

constexpr const char *kPolicyPath = NAV_POLICY_ONNX_PATH;
constexpr double kMaxActionError = 1e-4;

void require_policy_file() {
  if (!std::filesystem::exists(kPolicyPath)) {
    GTEST_SKIP() << "ONNX policy not found: " << kPolicyPath;
  }
}

}  // namespace

TEST(RLBrainOnnxTest, onnx_session_matches_reference_vectors) {
  require_policy_file();
  embodied_policy_cpp::OnnxSession session(kPolicyPath);

  for (const auto &sample : embodied_policy_cpp::kNavPolicyTestVectors) {
    const auto action = session.run_nav_action(sample.obs);
    for (size_t i = 0; i < action.size(); ++i) {
      EXPECT_NEAR(action[i], sample.action[i], static_cast<float>(kMaxActionError))
          << "obs index mismatch at action dim " << i;
    }
  }
}

TEST(RLBrainOnnxTest, rl_brain_end_to_end_action) {
  require_policy_file();

  embodied_policy_cpp::RLBrain::Config cfg;
  cfg.policy_path = kPolicyPath;
  cfg.goal = embodied_core::TaskGoal::point(2.5, 0.0);
  embodied_policy_cpp::RLBrain brain(cfg);

  embodied_core::WorldView world;
  world.base_x = 0.0;
  world.base_y = 0.0;
  world.base_yaw = 0.0;
  world.base_vx = 0.5;
  world.base_steer = 0.1;

  const auto out = brain.act(world, 0.02);
  EXPECT_GE(out.target_linear_x, -1.0);
  EXPECT_LE(out.target_linear_x, 1.0);
  EXPECT_GE(out.target_steering_angle, -0.52);
  EXPECT_LE(out.target_steering_angle, 0.52);
}
