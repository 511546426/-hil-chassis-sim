#include <algorithm>
#include <unordered_map>
#include <utility>
#include <vector>

class Solution {
public:
  std::vector<int> topKFrequent(std::vector<int>& nums, int k) {
    std::unordered_map<int, int> frequencies;

    for (const int num : nums) {
      ++frequencies[num];
    }

    std::vector<std::pair<int, int>> entries(
        frequencies.begin(), frequencies.end());

    std::sort(
        entries.begin(), entries.end(),
        [](const auto& left, const auto& right) {
          return left.second > right.second;
        });

    std::vector<int> result;
    result.reserve(k);

    for (int i = 0; i < k; ++i) {
      result.push_back(entries[i].first);
    }

    return result;
  }
};
