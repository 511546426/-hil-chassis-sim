#include <algorithm>

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
  int minDepth(TreeNode* root) {
    if (root == nullptr) {
      return 0;
    }

    const int left_depth = minDepth(root->left);
    const int right_depth = minDepth(root->right);

    if (root->left == nullptr) {
      return right_depth + 1;
    }

    if (root->right == nullptr) {
      return left_depth + 1;
    }

    return std::min(left_depth, right_depth) + 1;
  }
};
