#include <stack>

class MyQueue {
public:
  void push(int x) {
    input_.push(x);
  }

  int pop() {
    moveToOutputIfNeeded();
    const int value = output_.top();
    output_.pop();
    return value;
  }

  int peek() {
    moveToOutputIfNeeded();
    return output_.top();
  }

  bool empty() const {
    return input_.empty() && output_.empty();
  }

private:
  void moveToOutputIfNeeded() {
    if (!output_.empty()) {
      return;
    }

    while (!input_.empty()) {
      output_.push(input_.top());
      input_.pop();
    }
  }

  std::stack<int> input_;
  std::stack<int> output_;
};
