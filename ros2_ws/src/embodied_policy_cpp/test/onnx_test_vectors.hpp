#pragma once

#include <array>
#include <cstddef>

namespace embodied_policy_cpp {

struct OnnxTestVector {
  std::array<float, 8> obs{};
  std::array<float, 2> action{};
};

inline constexpr std::array<OnnxTestVector, 4> kNavPolicyTestVectors = {
  OnnxTestVector{
    {0.00000000f, 0.00000000f, 0.00000000f, 0.00000000f, 0.00000000f, 0.00000000f, 0.00000000f, 0.00000000f},
    {0.92703450f, 0.15904878f},
  },
  OnnxTestVector{
    {0.10000000f, 0.20000000f, 0.05000000f, 0.30000001f, -0.10000000f, 0.40000001f, 0.50000000f, 0.20000000f},
    {1.00000000f, -0.45772988f},
  },
  OnnxTestVector{
    {0.30471709f, -1.03998411f, 0.75045121f, 0.94056469f, -1.95103514f, -1.30217946f, 0.12784040f, -0.31624261f},
    {-0.03570588f, -1.00000000f},
  },
  OnnxTestVector{
    {0.50000000f, -0.30000001f, 0.25000000f, -0.80000001f, 0.60000002f, 0.15000001f, -0.40000001f, 0.10000000f},
    {-0.94302762f, 1.00000000f},
  },
};

}  // namespace embodied_policy_cpp
