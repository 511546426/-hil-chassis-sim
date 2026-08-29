/**
 * topic_logger_node — D3 练习：订阅 /chassis_state，打印底盘线速度。
 */

#include <nav_msgs/msg/odometry.hpp>
#include <rclcpp/rclcpp.hpp>

#include <stdexcept>
#include <string>

using nav_msgs::msg::Odometry;

class TopicLoggerNode : public rclcpp::Node {
public:
  TopicLoggerNode() : Node("topic_logger_node") {
    topic_name_ = declare_parameter<std::string>(
        "topic_name", "/chassis_state");
    log_every_n_ = declare_parameter<int>("log_every_n", 50);

    if (topic_name_.empty()) {
      throw std::invalid_argument("topic_name must not be empty");
    }
    if (log_every_n_ <= 0) {
      throw std::invalid_argument("log_every_n must be greater than 0");
    }

    sub_ = create_subscription<Odometry>(
        topic_name_, 10,
        [this](const Odometry::SharedPtr msg) {
          ++message_count_;
          if (message_count_ % log_every_n_ != 0) {
            return;
          }

          RCLCPP_INFO(
              get_logger(), "chassis linear.x = %.3f",
              msg->twist.twist.linear.x);
        });

    RCLCPP_INFO(
        get_logger(), "listening on %s, logging every %d messages",
        topic_name_.c_str(), log_every_n_);
  }

private:
  std::string topic_name_;
  int log_every_n_;
  int message_count_{0};
  rclcpp::Subscription<Odometry>::SharedPtr sub_;
};

int main(int argc, char * argv[]) {
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<TopicLoggerNode>());
  rclcpp::shutdown();
  return 0;
}
