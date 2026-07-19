#include <algorithm>
#include <climits>
#include <vector>

class Solution {
public:
  int minSubArrayLen(int target, std::vector<int> &nums) {
    int left = 0;
    int right = 0;
    int window_sum = 0;
    int min_length = INT_MAX;
    const int size = static_cast<int>(nums.size());

    while (right < size) {
      window_sum += nums[right];

      while (window_sum >= target) {
        min_length = std::min(min_length, right - left + 1);
        window_sum -= nums[left];
        ++left;
      }

      ++right;
    }

    return min_length == INT_MAX ? 0 : min_length;
  }
};
