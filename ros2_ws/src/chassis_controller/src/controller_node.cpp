/**
 * controller_node —— 域控节点 (C++)
 *
 * 角色: HIL 里的「域控制器」
 *   pub  /control_cmd   ← 键盘 → ChassisCommand (CAN 下行)
 *   sub  /chassis_state ← 位姿/速度 → 打印 (CAN 上行)
 *
 * 按键（输入后回车）:
 *   w/s     前进/后退
 *   a/d     左转/右转
 *   空格    正常停车（按减速度平滑减速）
 *   b       急停
 *   q       退出
 *   组合键  例: w a = 同时前进+左转
 */

#include <cmath>
#include <iostream>
#include <string>

#include <chassis_msgs/msg/chassis_command.hpp>
#include <nav_msgs/msg/odometry.hpp>
#include <rclcpp/rclcpp.hpp>

using namespace std::chrono_literals;
using ChassisCommand = chassis_msgs::msg::ChassisCommand;
using Odometry = nav_msgs::msg::Odometry;

class ControllerNode : public rclcpp::Node {
public:
    ControllerNode()
        : Node("controller_node"),
          vx_cmd_(0.0),
          omega_cmd_(0.0),
          emergency_brake_(false) {

        pub_ = this->create_publisher<ChassisCommand>("/control_cmd", 10);
        pub_timer_ = this->create_wall_timer(20ms, [this]() { this->publish_cmd(); });

        sub_ = this->create_subscription<Odometry>(
            "/chassis_state", 10,
            [this](const Odometry &msg) { this->on_state(msg); }
        );

        RCLCPP_INFO(this->get_logger(), "controller_node 已启动");
        RCLCPP_INFO(this->get_logger(), "  w/s/a/d + 回车: 设置目标速度");
        RCLCPP_INFO(this->get_logger(), "  空格 + 回车: 正常停车  |  b + 回车: 急停  |  q + 回车: 退出");
    }

    void run() {
        std::string line;
        while (rclcpp::ok() && std::getline(std::cin, line)) {
            bool has_motion_key = false;
            bool stop_normal = false;
            bool stop_emergency = false;

            for (char c : line) {
                switch (c) {
                    case 'w': case 'W': vx_cmd_ =  1.0; has_motion_key = true; break;
                    case 's': case 'S': vx_cmd_ = -1.0; has_motion_key = true; break;
                    case 'a': case 'A': omega_cmd_ =  2.0; has_motion_key = true; break;
                    case 'd': case 'D': omega_cmd_ = -2.0; has_motion_key = true; break;
                    case 'b': case 'B': stop_emergency = true; break;
                    case ' ': stop_normal = true; break;
                    case 'q': case 'Q': rclcpp::shutdown(); return;
                }
            }

            if (stop_emergency) {
                vx_cmd_ = 0.0;
                omega_cmd_ = 0.0;
                emergency_brake_ = true;
            } else if (stop_normal && !has_motion_key) {
                vx_cmd_ = 0.0;
                omega_cmd_ = 0.0;
                emergency_brake_ = false;
            } else if (has_motion_key) {
                emergency_brake_ = false;
            }

            RCLCPP_INFO(this->get_logger(),
                "→ tgt[vx=%+.2f  w=%+.2f]%s",
                vx_cmd_, omega_cmd_,
                emergency_brake_ ? "  BRAKE" : "");

            rclcpp::spin_some(this->get_node_base_interface());
        }
    }

private:
    void publish_cmd() {
        ChassisCommand msg;
        msg.target_linear_x = vx_cmd_;
        msg.target_angular_z = omega_cmd_;
        msg.emergency_brake = emergency_brake_;
        pub_->publish(msg);
    }

    static double yaw_from_quaternion(const Odometry &msg) {
        const auto &q = msg.pose.pose.orientation;
        const double siny_cosp = 2.0 * (q.w * q.z + q.x * q.y);
        const double cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z);
        return std::atan2(siny_cosp, cosy_cosp);
    }

    void on_state(const Odometry &msg) {
        const double yaw_deg = yaw_from_quaternion(msg) * 180.0 / M_PI;
        RCLCPP_INFO_THROTTLE(
            this->get_logger(), *this->get_clock(), 1000,
            "← x=%+.3f  y=%+.3f  yaw=%+.1f°  act_vx=%+.2f  act_w=%+.2f",
            msg.pose.pose.position.x,
            msg.pose.pose.position.y,
            yaw_deg,
            msg.twist.twist.linear.x,
            msg.twist.twist.angular.z
        );
    }

    rclcpp::Publisher<ChassisCommand>::SharedPtr pub_;
    rclcpp::Subscription<Odometry>::SharedPtr sub_;
    rclcpp::TimerBase::SharedPtr pub_timer_;
    double vx_cmd_;
    double omega_cmd_;
    bool emergency_brake_;
};

int main(int argc, char **argv) {
    rclcpp::init(argc, argv);
    auto node = std::make_shared<ControllerNode>();
    node->run();
    rclcpp::shutdown();
    return 0;
}
