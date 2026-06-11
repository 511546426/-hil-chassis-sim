#include "embodied_policy_cpp/onnx_session.hpp"

#include <stdexcept>
#include <utility>

namespace embodied_policy_cpp {

namespace {

std::string fetch_node_name(Ort::Session &session, size_t index, bool input) {
  Ort::AllocatorWithDefaultOptions allocator;
  if (input) {
    return session.GetInputNameAllocated(index, allocator).get();
  }
  return session.GetOutputNameAllocated(index, allocator).get();
}

}  // namespace

OnnxSession::OnnxSession(const std::string &model_path)
    : env_(ORT_LOGGING_LEVEL_WARNING, "embodied_policy_cpp"),
      session_(env_, model_path.c_str(), Ort::SessionOptions{}) {
  if (session_.GetInputCount() != 1 || session_.GetOutputCount() != 1) {
    throw std::runtime_error("nav policy ONNX must have exactly one input and one output");
  }
  input_name_ = fetch_node_name(session_, 0, true);
  output_name_ = fetch_node_name(session_, 0, false);
}

std::array<float, OnnxSession::kActionDim> OnnxSession::run_nav_action(
    const std::array<float, kObsDim> &obs) {
  std::array<float, kObsDim> obs_copy = obs;
  const std::array<int64_t, 2> input_shape{1, static_cast<int64_t>(kObsDim)};

  Ort::MemoryInfo memory_info =
      Ort::MemoryInfo::CreateCpu(OrtArenaAllocator, OrtMemTypeDefault);
  Ort::Value input_tensor = Ort::Value::CreateTensor<float>(
      memory_info,
      obs_copy.data(),
      obs_copy.size(),
      input_shape.data(),
      input_shape.size());

  const char *input_names[] = {input_name_.c_str()};
  const char *output_names[] = {output_name_.c_str()};

  auto outputs = session_.Run(
      Ort::RunOptions{nullptr},
      input_names,
      &input_tensor,
      1,
      output_names,
      1);

  float *output_data = outputs[0].GetTensorMutableData<float>();
  const auto output_info = outputs[0].GetTensorTypeAndShapeInfo();
  if (output_info.GetElementCount() < static_cast<size_t>(kActionDim)) {
    throw std::runtime_error("ONNX output dim mismatch");
  }

  return {output_data[0], output_data[1]};
}

}  // namespace embodied_policy_cpp
