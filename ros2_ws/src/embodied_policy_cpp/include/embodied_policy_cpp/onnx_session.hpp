#pragma once

#include <array>
#include <cstddef>
#include <memory>
#include <string>
#include <vector>

#include <onnxruntime/onnxruntime_cxx_api.h>

namespace embodied_policy_cpp {

/// 轻量 ONNX Runtime 封装（导航策略：obs[8] → action[2]）
class OnnxSession {
 public:
  static constexpr std::size_t kObsDim = 8;
  static constexpr std::size_t kActionDim = 2;

  explicit OnnxSession(const std::string &model_path);

  [[nodiscard]] std::array<float, kActionDim> run_nav_action(
      const std::array<float, kObsDim> &obs);

 private:
  Ort::Env env_;
  Ort::Session session_;
  Ort::AllocatorWithDefaultOptions allocator_;
  std::string input_name_;
  std::string output_name_;
};

}  // namespace embodied_policy_cpp
