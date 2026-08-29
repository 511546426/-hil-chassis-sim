#include <vector>

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
  std::vector<int> preorderTraversal(TreeNode* root) {
    std::vector<int> result;
    preorder(root, result);
    return result;
  }

private:
  void preorder(TreeNode* node, std::vector<int>& result) {
    if (node == nullptr) {
      return;
    }

    result.push_back(node->val);
    preorder(node->left, result);
    preorder(node->right, result);
  }
};
