#include <chrono>
#include <memory>

#include <embodied_msgs/srv/reset_episode.hpp>
#include <rclcpp/rclcpp.hpp>

using embodied_msgs::srv::ResetEpisode;

class ResetClientNode : public rclcpp::Node {
public:
  ResetClientNode()
      : Node("reset_client_node") {
    client_ = create_client<ResetEpisode>(
        "/sim/reset_episode");
  }

  bool reset() {
    using namespace std::chrono_literals;

    if (!client_->wait_for_service(2s)) {
      RCLCPP_ERROR(
          get_logger(),
          "service /sim/reset_episode is not available");
      return false;
    }

    auto request =
        std::make_shared<ResetEpisode::Request>();
    request->base_x = 0.0;
    request->base_y = 0.0;
    request->base_yaw = 0.0;

    // 回调式异步请求不主动等待 Future，用定时器处理超时。
    timeout_timer_ = create_wall_timer(3s, [this]() {
      if (response_received_) {
        return;
      }

      RCLCPP_ERROR(
          get_logger(),
          "reset service request timed out or failed");
      exit_code_ = 1;
      rclcpp::shutdown();
    });

    client_->async_send_request(
        request,
        [this](rclcpp::Client<ResetEpisode>::SharedFuture future) {
          response_received_ = true;
          timeout_timer_->cancel();

          const auto response = future.get();
          if (!response->success) {
            RCLCPP_ERROR(
                get_logger(),
                "reset failed: %s",
                response->message.c_str());
            exit_code_ = 1;
          } else {
            RCLCPP_INFO(
                get_logger(),
                "reset succeeded: %s",
                response->message.c_str());
            exit_code_ = 0;
          }

          // 处理完一次性请求后退出 spin。
          rclcpp::shutdown();
        });

    return true;
  }

  int exit_code() const {
    return exit_code_;
  }

private:
  rclcpp::Client<ResetEpisode>::SharedPtr client_;
  rclcpp::TimerBase::SharedPtr timeout_timer_;
  bool response_received_{false};
  int exit_code_{1};
};

int main(int argc, char* argv[]) {
  rclcpp::init(argc, argv);

  const auto node = std::make_shared<ResetClientNode>();
  if (!node->reset()) {
    rclcpp::shutdown();
    return 1;
  }

  // Executor 驱动 Response 回调和超时定时器。
  rclcpp::spin(node);
  rclcpp::shutdown();
  return node->exit_code();
}
