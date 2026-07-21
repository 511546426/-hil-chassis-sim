#include <vector>

class Solution {
public:
  std::vector<std::vector<int>> generateMatrix(int n) {
    std::vector<std::vector<int>> matrix(
        n, std::vector<int>(n, 0));

    int top = 0;
    int bottom = n - 1;
    int left = 0;
    int right = n - 1;
    int value = 1;

    while (top <= bottom && left <= right) {
      // 从左到右填写上边。
      for (int i = left; i <= right; ++i) {
        matrix[top][i] = value++;
      }
      ++top;

      // 从上到下填写右边。
      for (int i = top; i <= bottom; ++i) {
        matrix[i][right] = value++;
      }
      --right;

      if (top <= bottom) {
        // 从右到左填写下边。
        for (int i = right; i >= left; --i) {
          matrix[bottom][i] = value++;
        }
        --bottom;
      }

      if (left <= right) {
        // 从下到上填写左边。
        for (int i = bottom; i >= top; --i) {
          matrix[i][left] = value++;
        }
        ++left;
      }
    }

    return matrix;
  }
};
