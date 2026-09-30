#include <algorithm>
#include <cstdlib>

struct TreeNode {
  int val;
  TreeNode* left;
  TreeNode* right;

  TreeNode()
      : val(0), left(nullptr), right(nullptr) {}

  explicit TreeNode(int value)
      : val(value), left(nullptr), right(nullptr) {}

  TreeNode(int value, TreeNode* left_node, TreeNode* right_node)
      : val(value), left(left_node), right(right_node) {}
};

class Solution {
public:
  bool isBalanced(TreeNode* root) {
    return getHeight(root) != -1;
  }

private:
  int getHeight(TreeNode* node) {
    if (node == nullptr) {
      return 0;
    }

    const int left_height = getHeight(node->left);
    if (left_height == -1) {
      return -1;
    }

    const int right_height = getHeight(node->right);
    if (right_height == -1) {
      return -1;
    }

    if (std::abs(left_height - right_height) > 1) {
      return -1;
    }

    return std::max(left_height, right_height) + 1;
  }
};
