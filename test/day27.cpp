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
  int findBottomLeftValue(TreeNode* root) {
    max_depth_ = -1;
    result_ = 0;
    dfs(root, 0);
    return result_;
  }

private:
  void dfs(TreeNode* node, int depth) {
    if (node == nullptr) {
      return;
    }

    // 先访问左子树，同一层第一次到达的节点就是最左节点。
    if (depth > max_depth_) {
      max_depth_ = depth;
      result_ = node->val;
    }

    dfs(node->left, depth + 1);
    dfs(node->right, depth + 1);
  }

  int max_depth_{-1};
  int result_{0};
};
