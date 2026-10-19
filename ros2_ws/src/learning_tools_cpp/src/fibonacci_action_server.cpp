#include <chrono>
#include <memory>
#include <thread>

#include <example_interfaces/action/fibonacci.hpp>
#include <rclcpp/rclcpp.hpp>
#include <rclcpp_action/rclcpp_action.hpp>

using Fibonacci = example_interfaces::action::Fibonacci;
using GoalHandleFibonacci = rclcpp_action::ServerGoalHandle<Fibonacci>;

class FibonacciActionServer : public rclcpp::Node {
public:
  FibonacciActionServer()
      : Node("fibonacci_action_server") {
    using namespace std::placeholders;

    action_server_ = rclcpp_action::create_server<Fibonacci>(
        this,
        "learning/fibonacci",
        std::bind(&FibonacciActionServer::handle_goal, this, _1, _2),
        std::bind(&FibonacciActionServer::handle_cancel, this, _1),
        std::bind(&FibonacciActionServer::handle_accepted, this, _1));

    RCLCPP_INFO(get_logger(), "Action server ready: /learning/fibonacci");
  }

private:
  rclcpp_action::GoalResponse handle_goal(
      const rclcpp_action::GoalUUID&,
      std::shared_ptr<const Fibonacci::Goal> goal) {
    if (goal->order < 0) {
      RCLCPP_WARN(get_logger(), "Rejecting negative Fibonacci order");
      return rclcpp_action::GoalResponse::REJECT;
    }

    RCLCPP_INFO(get_logger(), "Accepted Fibonacci order: %d", goal->order);
    return rclcpp_action::GoalResponse::ACCEPT_AND_EXECUTE;
  }

  rclcpp_action::CancelResponse handle_cancel(
      const std::shared_ptr<GoalHandleFibonacci>) {
    RCLCPP_INFO(get_logger(), "Cancel request received");
    return rclcpp_action::CancelResponse::ACCEPT;
  }

  void handle_accepted(const std::shared_ptr<GoalHandleFibonacci> goal_handle) {
    std::thread{std::bind(
        &FibonacciActionServer::execute, this, std::placeholders::_1),
        goal_handle}.detach();
  }

  void execute(const std::shared_ptr<GoalHandleFibonacci> goal_handle) {
    const auto goal = goal_handle->get_goal();
    auto feedback = std::make_shared<Fibonacci::Feedback>();
    auto result = std::make_shared<Fibonacci::Result>();

    feedback->sequence = {0, 1};
    const int order = goal->order;

    for (int i = 2; i < order; ++i) {
      if (goal_handle->is_canceling()) {
        result->sequence = feedback->sequence;
        goal_handle->canceled(result);
        RCLCPP_INFO(get_logger(), "Fibonacci goal canceled");
        return;
      }

      feedback->sequence.push_back(
          feedback->sequence[i - 1] + feedback->sequence[i - 2]);
      goal_handle->publish_feedback(feedback);
      std::this_thread::sleep_for(std::chrono::milliseconds(300));
    }

    if (order == 0) {
      feedback->sequence.clear();
    } else if (order == 1) {
      feedback->sequence.resize(1);
    }

    result->sequence = feedback->sequence;
    goal_handle->succeed(result);
    RCLCPP_INFO(get_logger(), "Fibonacci goal completed");
  }

  rclcpp_action::Server<Fibonacci>::SharedPtr action_server_;
};

int main(int argc, char* argv[]) {
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<FibonacciActionServer>());
  rclcpp::shutdown();
  return 0;
}
