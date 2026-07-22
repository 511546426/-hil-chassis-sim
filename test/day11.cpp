#include <queue>

class MyStack {
public:
  void push(int x) {
    int size = queue_.size();
    queue_.push(x);

    for (int i = 0; i < size; i++) {
      int front = queue_.front();
      queue_.pop();
      queue_.push(front);
    }
  }

  int pop() {
    int result = queue_.front();
    queue_.pop();
    return result;
  }

  int top() {
    return queue_.front();
  }

  bool empty() {
    return queue_.empty();
  }

private:
  std::queue<int> queue_;
};
