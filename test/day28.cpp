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
  bool hasPathSum(TreeNode* root, int targetSum) {
    return hasPath(root, targetSum);
  }

private:
  bool hasPath(TreeNode* node, int remaining) {
    if (node == nullptr) {
      return false;
    }

    remaining -= node->val;

    // 只有根到叶子的完整路径才可以作为答案。
    if (node->left == nullptr && node->right == nullptr) {
      return remaining == 0;
    }

    return hasPath(node->left, remaining) ||
           hasPath(node->right, remaining);
  }
};
