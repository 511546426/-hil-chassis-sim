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

    auto future = client_->async_send_request(request);
    const auto result = rclcpp::spin_until_future_complete(
        get_node_base_interface(), future, 3s);

    if (result != rclcpp::FutureReturnCode::SUCCESS) {
      RCLCPP_ERROR(
          get_logger(),
          "reset service request timed out or failed");
      return false;
    }

    const auto response = future.get();
    if (!response->success) {
      RCLCPP_ERROR(
          get_logger(),
          "reset failed: %s",
          response->message.c_str());
      return false;
    }

    RCLCPP_INFO(
        get_logger(),
        "reset succeeded: %s",
        response->message.c_str());
    return true;
  }

private:
  rclcpp::Client<ResetEpisode>::SharedPtr client_;
};

int main(int argc, char* argv[]) {
  rclcpp::init(argc, argv);

  const auto node = std::make_shared<ResetClientNode>();
  const bool success = node->reset();

  rclcpp::shutdown();
  return success ? 0 : 1;
}
