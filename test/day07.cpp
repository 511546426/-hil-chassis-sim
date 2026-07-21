#include <string>

class Solution {
public:
  bool isAnagram(const std::string &s, const std::string &t) {
    if (s.size() != t.size()) {
      return false;
    }

    int counts[26] = {};
    for (const char ch : s) {
      ++counts[ch - 'a'];
    }

    for (const char ch : t) {
      --counts[ch - 'a'];
    }

    for (const int count : counts) {
      if (count != 0) {
        return false;
      }
    }

    return true;
  }
};
