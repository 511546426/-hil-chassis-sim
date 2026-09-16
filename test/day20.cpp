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
  bool isSymmetric(TreeNode* root) {
    if (root == nullptr) {
      return true;
    }

    return isMirror(root->left, root->right);
  }

private:
  bool isMirror(TreeNode* left, TreeNode* right) {
    if (left == nullptr && right == nullptr) {
      return true;
    }

    if (left == nullptr || right == nullptr) {
      return false;
    }

    if (left->val != right->val) {
      return false;
    }

    return isMirror(left->left, right->right) &&
           isMirror(left->right, right->left);
  }
};
