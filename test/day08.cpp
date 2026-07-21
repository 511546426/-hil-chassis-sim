#include <string>

class Solution {
public:
  std::string removeDuplicates(const std::string &s) {
    std::string stack_str;
    for (const char ch : s) {
      if (!stack_str.empty() && stack_str.back() == ch) {
        stack_str.pop_back();
      } else {
        stack_str.push_back(ch);
      }
    }
    return stack_str;
  }
};
