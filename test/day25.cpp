#include <string>
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
  std::vector<std::string> binaryTreePaths(TreeNode* root) {
    std::vector<std::string> result;
    collectPaths(root, "", result);
    return result;
  }

private:
  void collectPaths(TreeNode* node,
                    const std::string& path,
                    std::vector<std::string>& result) {
    if (node == nullptr) {
      return;
    }

    std::string current_path = path;
    if (!current_path.empty()) {
      current_path += "->";
    }
    current_path += std::to_string(node->val);

    if (node->left == nullptr && node->right == nullptr) {
      result.push_back(current_path);
      return;
    }

    collectPaths(node->left, current_path, result);
    collectPaths(node->right, current_path, result);
  }
};
