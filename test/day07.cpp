#include <string>

class Solution {
public:
  bool isAnagram(const std::string &s, const std::string &t) {
    if (s.size() != t.size()) {
      return false;
    }

    int counts[26] = {};

    for (char character : s) {
      ++counts[character - 'a'];
    }

    for (char character : t) {
      --counts[character - 'a'];
    }

    for (int count : counts) {
      if (count != 0) {
        return false;
      }
    }

    return true;
  }
};
