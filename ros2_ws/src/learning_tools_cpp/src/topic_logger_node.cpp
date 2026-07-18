/**
 * topic_logger_node — D3 练习：订阅 /chassis_state，打印底盘线速度。
 */

#include <nav_msgs/msg/odometry.hpp>
#include <rclcpp/rclcpp.hpp>

using nav_msgs::msg::Odometry;

class TopicLoggerNode : public rclcpp::Node {
public:
  TopicLoggerNode() : Node("topic_logger_node") {
    sub_ = create_subscription<Odometry>(
        "/chassis_state", 10,
        [this](const Odometry::SharedPtr msg) {
          const double linear_x = msg->twist.twist.linear.x;
          RCLCPP_INFO(get_logger(), "chassis linear.x = %.3f", linear_x);
        });
    RCLCPP_INFO(get_logger(), "listening on /chassis_state");
  }

private:
  rclcpp::Subscription<Odometry>::SharedPtr sub_;
};

int main(int argc, char * argv[]) {
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<TopicLoggerNode>());
  rclcpp::shutdown();
  return 0;
}
