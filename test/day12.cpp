#include <stack>
#include <string>
#include <vector>

class Solution {
public:
  int evalRPN(std::vector<std::string>& tokens) {
    std::stack<int> operands;

    for (const std::string& token : tokens) {
      if (token != "+" && token != "-" && token != "*" && token != "/") {
        operands.push(std::stoi(token));
        continue;
      }

      const int right = operands.top();
      operands.pop();
      const int left = operands.top();
      operands.pop();

      if (token == "+") {
        operands.push(left + right);
      } else if (token == "-") {
        operands.push(left - right);
      } else if (token == "*") {
        operands.push(left * right);
      } else {
        operands.push(left / right);
      }
    }

    return operands.top();
  }
};
