#include <vector>

class Solution {
public:
  std::vector<int> sortedSquares(std::vector<int> &nums) {
    const int length = static_cast<int>(nums.size());
    std::vector<int> result(length);

    int left_index = 0;
    int right_index = length - 1;
    int write_index = length - 1;

    while (left_index <= right_index) {
      const int left_square = nums[left_index] * nums[left_index];
      const int right_square = nums[right_index] * nums[right_index];

      if (left_square > right_square) {
        result[write_index] = left_square;
        ++left_index;
      } else {
        result[write_index] = right_square;
        --right_index;
      }
      --write_index;
    }

    return result;
  }
};
