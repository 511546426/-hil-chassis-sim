#include <stack>
#include <string>

class Solution {
public:
  bool isValid(const std::string &s) {
    std::stack<char> brackets;

    for (const char ch : s) {
      if (ch == '(' || ch == '[' || ch == '{') {
        brackets.push(ch);
        continue;
      }

      if (brackets.empty()) {
        return false;
      }

      const char left = brackets.top();
      const bool matched =
          (left == '(' && ch == ')') ||
          (left == '[' && ch == ']') ||
          (left == '{' && ch == '}');

      if (!matched) {
        return false;
      }

      brackets.pop();
    }

    return brackets.empty();
  }
};
