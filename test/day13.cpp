#include <deque>
#include <vector>

class Solution {
public:
  std::vector<int> maxSlidingWindow(std::vector<int>& nums, int k) {
    std::vector<int> result;
    std::deque<int> candidates;

    for (int i = 0; i < static_cast<int>(nums.size()); ++i) {
      const int window_left = i - k + 1;

      if (!candidates.empty() && candidates.front() < window_left) {
        candidates.pop_front();
      }

      while (!candidates.empty() && nums[candidates.back()] <= nums[i]) {
        candidates.pop_back();
      }

      candidates.push_back(i);

      if (i >= k - 1) {
        result.push_back(nums[candidates.front()]);
      }
    }

    return result;
  }
};
