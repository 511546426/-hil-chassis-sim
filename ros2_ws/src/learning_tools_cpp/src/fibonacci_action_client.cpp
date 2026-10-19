#include <chrono>
#include <functional>
#include <memory>

#include <example_interfaces/action/fibonacci.hpp>
#include <rclcpp/rclcpp.hpp>
#include <rclcpp_action/rclcpp_action.hpp>

using Fibonacci = example_interfaces::action::Fibonacci;
using GoalHandleFibonacci = rclcpp_action::ClientGoalHandle<Fibonacci>;

class FibonacciActionClient : public rclcpp::Node {
public:
  FibonacciActionClient()
      : Node("fibonacci_action_client") {
    client_ = rclcpp_action::create_client<Fibonacci>(
        this, "learning/fibonacci");
  }

  void send_goal(int order) {
    if (!client_->wait_for_action_server(std::chrono::seconds(3))) {
      RCLCPP_ERROR(get_logger(), "Action server is not available");
      rclcpp::shutdown();
      return;
    }

    Fibonacci::Goal goal;
    goal.order = order;

    rclcpp_action::Client<Fibonacci>::SendGoalOptions options;
    options.goal_response_callback =
        [this](const GoalHandleFibonacci::SharedPtr& goal_handle) {
          if (!goal_handle) {
            RCLCPP_ERROR(get_logger(), "Goal was rejected");
          } else {
            RCLCPP_INFO(get_logger(), "Goal accepted");
          }
        };
    options.feedback_callback =
        [this](GoalHandleFibonacci::SharedPtr,
               const std::shared_ptr<const Fibonacci::Feedback> feedback) {
          RCLCPP_INFO(get_logger(), "Feedback sequence size: %zu",
                      feedback->sequence.size());
        };
    options.result_callback =
        [this](const GoalHandleFibonacci::WrappedResult& wrapped_result) {
          if (wrapped_result.code == rclcpp_action::ResultCode::SUCCEEDED) {
            RCLCPP_INFO(get_logger(), "Result sequence size: %zu",
                        wrapped_result.result->sequence.size());
          } else {
            RCLCPP_ERROR(get_logger(), "Action failed or was canceled");
          }
          rclcpp::shutdown();
        };

    client_->async_send_goal(goal, options);
  }

private:
  rclcpp_action::Client<Fibonacci>::SharedPtr client_;
};

int main(int argc, char* argv[]) {
  rclcpp::init(argc, argv);
  const auto node = std::make_shared<FibonacciActionClient>();
  node->send_goal(8);
  rclcpp::spin(node);
  rclcpp::shutdown();
  return 0;
}
