#include <queue>
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
  std::vector<std::vector<int>> levelOrder(TreeNode* root) {
    std::vector<std::vector<int>> result;

    if (root == nullptr) {
      return result;
    }

    std::queue<TreeNode*> nodes;
    nodes.push(root);

    while (!nodes.empty()) {
      const int level_size = static_cast<int>(nodes.size());
      std::vector<int> level;
      level.reserve(level_size);

      for (int i = 0; i < level_size; ++i) {
        TreeNode* node = nodes.front();
        nodes.pop();

        level.push_back(node->val);

        if (node->left != nullptr) {
          nodes.push(node->left);
        }

        if (node->right != nullptr) {
          nodes.push(node->right);
        }
      }

      result.push_back(level);
    }

    return result;
  }
};
