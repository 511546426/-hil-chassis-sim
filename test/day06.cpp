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
      for (int column = left; column <= right; ++column) {
        matrix[top][column] = value++;
      }
      ++top;

      for (int row = top; row <= bottom; ++row) {
        matrix[row][right] = value++;
      }
      --right;

      if (top <= bottom) {
        for (int column = right; column >= left; --column) {
          matrix[bottom][column] = value++;
        }
        --bottom;
      }

      if (left <= right) {
        for (int row = bottom; row >= top; --row) {
          matrix[row][left] = value++;
        }
        ++left;
      }
    }

    return matrix;
  }
};
