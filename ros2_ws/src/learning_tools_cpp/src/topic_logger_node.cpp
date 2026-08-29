/**
 * topic_logger_node — D3 练习：订阅 /chassis_state，打印底盘线速度。
 */

#include <nav_msgs/msg/odometry.hpp>
#include <rclcpp/rclcpp.hpp>

#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

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

    parameter_callback_handle_ = add_on_set_parameters_callback(
        [this](const std::vector<rclcpp::Parameter>& parameters) {
          return onParametersChanged(parameters);
        });

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
  rcl_interfaces::msg::SetParametersResult onParametersChanged(
      const std::vector<rclcpp::Parameter>& parameters) {
    rcl_interfaces::msg::SetParametersResult result;
    result.successful = true;

    int next_log_every_n = log_every_n_;
    bool update_log_every_n = false;

    for (const auto& parameter : parameters) {
      if (parameter.get_name() == "log_every_n") {
        if (parameter.get_type() !=
            rclcpp::ParameterType::PARAMETER_INTEGER) {
          result.successful = false;
          result.reason = "log_every_n must be an integer";
          return result;
        }

        const auto value = parameter.as_int();
        if (value <= 0 || value > std::numeric_limits<int>::max()) {
          result.successful = false;
          result.reason = "log_every_n must be greater than 0";
          return result;
        }

        next_log_every_n = static_cast<int>(value);
        update_log_every_n = true;
      } else if (parameter.get_name() == "topic_name") {
        result.successful = false;
        result.reason =
            "topic_name cannot be changed while the node is running";
        return result;
      }
    }

    if (update_log_every_n) {
      log_every_n_ = next_log_every_n;
      RCLCPP_INFO(
          get_logger(), "log_every_n updated to %d", log_every_n_);
    }

    return result;
  }

  std::string topic_name_;
  int log_every_n_;
  int message_count_{0};
  rclcpp::Subscription<Odometry>::SharedPtr sub_;
  rclcpp::node_interfaces::OnSetParametersCallbackHandle::SharedPtr
      parameter_callback_handle_;
};

int main(int argc, char * argv[]) {
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<TopicLoggerNode>());
  rclcpp::shutdown();
  return 0;
}
