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
  int sumOfLeftLeaves(TreeNode* root) {
    return sumLeftLeaves(root, false);
  }

private:
  int sumLeftLeaves(TreeNode* node, bool is_left) {
    if (node == nullptr) {
      return 0;
    }

    // 当前节点必须同时是左孩子和叶子节点。
    if (is_left && node->left == nullptr && node->right == nullptr) {
      return node->val;
    }

    const int left_sum = sumLeftLeaves(node->left, true);
    const int right_sum = sumLeftLeaves(node->right, false);
    return left_sum + right_sum;
  }
};
