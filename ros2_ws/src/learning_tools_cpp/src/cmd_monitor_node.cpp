#include <functional>
#include <memory>

#include <embodied_msgs/msg/embodied_command.hpp>
#include <rclcpp/rclcpp.hpp>

using EmbodiedCommand = embodied_msgs::msg::EmbodiedCommand;

class CmdMonitorNode : public rclcpp::Node {
public:
  CmdMonitorNode() : Node("cmd_monitor_node") {
    subscription_ = create_subscription<EmbodiedCommand>(
        "/control_cmd", 10,
        std::bind(
            &CmdMonitorNode::cmdCallback, this, std::placeholders::_1));
  }

private:
  void cmdCallback(const EmbodiedCommand::SharedPtr msg) {
    RCLCPP_INFO_THROTTLE(
        get_logger(),
        *get_clock(),
        1000,
        "linear_x=%.3f, steering_angle=%.3f, emergency_brake=%s",
        msg->target_linear_x, msg->target_steering_angle,
        msg->emergency_brake ? "true" : "false");
  }

  rclcpp::Subscription<EmbodiedCommand>::SharedPtr subscription_;
};

int main(int argc, char *argv[]) {
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<CmdMonitorNode>());
  rclcpp::shutdown();
  return 0;
}
