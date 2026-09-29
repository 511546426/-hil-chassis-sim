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
  int countNodes(TreeNode* root) {
    if (root == nullptr) {
      return 0;
    }

    int left_height = 0;
    TreeNode* left = root;
    while (left != nullptr) {
      ++left_height;
      left = left->left;
    }

    int right_height = 0;
    TreeNode* right = root;
    while (right != nullptr) {
      ++right_height;
      right = right->right;
    }

    if (left_height == right_height) {
      return (1 << left_height) - 1;
    }

    return countNodes(root->left) +
           countNodes(root->right) +
           1;
  }
};
