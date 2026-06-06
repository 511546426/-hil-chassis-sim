/**
 * controller_node —— 具身智能体遥控（移动底盘 + 机械臂 + 夹爪）
 *
 * 底盘: w/s/a/d/c/空格/b
 * 机械臂: i/k=肩升降  j/l=肘左右  u/o=腕俯仰  g=夹爪  q=退出
 */

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstring>

#include <sys/select.h>
#include <termios.h>
#include <unistd.h>

#include <embodied_msgs/msg/embodied_command.hpp>
#include <nav_msgs/msg/odometry.hpp>
#include <rclcpp/executors.hpp>
#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/joint_state.hpp>

using namespace std::chrono_literals;
using EmbodiedCommand = embodied_msgs::msg::EmbodiedCommand;
using Odometry = nav_msgs::msg::Odometry;
using JointState = sensor_msgs::msg::JointState;

static constexpr double MAX_STEER = 0.52;
static constexpr double STEER_STEP = 0.08;
static constexpr double ARM_STEP = 0.12;

class RawTerminal {
public:
    RawTerminal() {
        if (!isatty(STDIN_FILENO)) return;
        if (tcgetattr(STDIN_FILENO, &original_) == 0) {
            termios raw = original_;
            raw.c_lflag &= ~(ICANON | ECHO);
            raw.c_cc[VMIN] = 0;
            raw.c_cc[VTIME] = 0;
            if (tcsetattr(STDIN_FILENO, TCSANOW, &raw) == 0) active_ = true;
        }
    }
    ~RawTerminal() { restore(); }
    void restore() {
        if (active_) { tcsetattr(STDIN_FILENO, TCSANOW, &original_); active_ = false; }
    }
    bool active() const { return active_; }
private:
    termios original_{};
    bool active_ = false;
};

class ControllerNode : public rclcpp::Node {
public:
    ControllerNode() : Node("controller_node") {
        pub_ = this->create_publisher<EmbodiedCommand>("/control_cmd", 10);
        pub_timer_ = this->create_wall_timer(20ms, [this]() { publish_cmd(); });

        sub_odom_ = this->create_subscription<Odometry>(
            "/chassis_state", 10, [this](const Odometry &m) { on_odom(m); });
        sub_arm_ = this->create_subscription<JointState>(
            "/arm_state", 10, [this](const JointState &m) { on_arm(m); });

        RCLCPP_INFO(get_logger(), "具身智能体遥控已启动");
        RCLCPP_INFO(get_logger(), "  底盘: w/s 前进后退  a/d 转向  c 回正  空格 停  b 急停");
        RCLCPP_INFO(get_logger(), "  机械臂: i/k 肩升降  j/l 肘左右  u/o 腕俯仰  g 夹爪  q 退出");
    }

    void run(rclcpp::executors::SingleThreadedExecutor &executor) {
        RawTerminal term;
        while (rclcpp::ok()) {
            fd_set fds;
            FD_ZERO(&fds);
            FD_SET(STDIN_FILENO, &fds);
            timeval tv{0, 50000};
            int ready = select(STDIN_FILENO + 1, &fds, nullptr, nullptr, &tv);
            if (ready > 0 && FD_ISSET(STDIN_FILENO, &fds)) {
                char c = 0;
                if (read(STDIN_FILENO, &c, 1) == 1 && !handle_key(c)) break;
            } else if (ready < 0) break;
            executor.spin_some();
        }
        term.restore();
    }

private:
    bool handle_key(char c) {
        switch (c) {
            case 'w': case 'W': vx_cmd_ = 1.0; emergency_brake_ = false; break;
            case 's': case 'S': vx_cmd_ = -1.0; emergency_brake_ = false; break;
            case 'a': case 'A': steer_cmd_ = std::min(steer_cmd_ + STEER_STEP, MAX_STEER); emergency_brake_ = false; break;
            case 'd': case 'D': steer_cmd_ = std::max(steer_cmd_ - STEER_STEP, -MAX_STEER); emergency_brake_ = false; break;
            case 'c': case 'C': steer_cmd_ = 0.0; emergency_brake_ = false; break;
            case 'i': case 'I': shoulder_cmd_ = std::min(shoulder_cmd_ + ARM_STEP, 1.0); break;
            case 'k': case 'K': shoulder_cmd_ = std::max(shoulder_cmd_ - ARM_STEP, -1.0); break;
            case 'j': case 'J': elbow_cmd_ = std::min(elbow_cmd_ + ARM_STEP, 1.2); break;
            case 'l': case 'L': elbow_cmd_ = std::max(elbow_cmd_ - ARM_STEP, -1.2); break;
            case 'u': case 'U': wrist_cmd_ = std::min(wrist_cmd_ + ARM_STEP, 1.2); break;
            case 'o': case 'O': wrist_cmd_ = std::max(wrist_cmd_ - ARM_STEP, -1.2); break;
            case 'g': case 'G': gripper_cmd_ = gripper_cmd_ < 0.5 ? 1.0 : 0.0; break;
            case ' ':
                vx_cmd_ = steer_cmd_ = 0.0; emergency_brake_ = false; break;
            case 'b': case 'B':
                vx_cmd_ = steer_cmd_ = 0.0; emergency_brake_ = true; break;
            case 'q': case 'Q':
                RCLCPP_INFO(get_logger(), "退出");
                rclcpp::shutdown();
                return false;
            default: return true;
        }
        RCLCPP_INFO(get_logger(),
            "→ base[vx=%+.2f steer=%+.0f°]%s  arm[S=%+.2f E=%+.2f W=%+.2f] grip=%.0f%%",
            vx_cmd_, steer_cmd_ * 180.0 / M_PI,
            emergency_brake_ ? " BRAKE" : "",
            shoulder_cmd_, elbow_cmd_, wrist_cmd_, gripper_cmd_ * 100.0);
        return true;
    }

    void publish_cmd() {
        EmbodiedCommand msg;
        msg.target_linear_x = vx_cmd_;
        msg.target_steering_angle = steer_cmd_;
        msg.emergency_brake = emergency_brake_;
        msg.arm_shoulder = shoulder_cmd_;
        msg.arm_elbow = elbow_cmd_;
        msg.arm_wrist = wrist_cmd_;
        msg.gripper = gripper_cmd_;
        pub_->publish(msg);
    }

    static double yaw_from_quat(const Odometry &msg) {
        const auto &q = msg.pose.pose.orientation;
        return std::atan2(2.0 * (q.w * q.z + q.x * q.y), 1.0 - 2.0 * (q.y * q.y + q.z * q.z));
    }

    void on_odom(const Odometry &msg) {
        RCLCPP_INFO_THROTTLE(get_logger(), *get_clock(), 1000,
            "← base x=%+.2f y=%+.2f yaw=%+.0f° vx=%+.2f",
            msg.pose.pose.position.x, msg.pose.pose.position.y,
            yaw_from_quat(msg) * 180.0 / M_PI, msg.twist.twist.linear.x);
    }

    void on_arm(const JointState &msg) {
        if (msg.position.size() < 3) return;
        RCLCPP_INFO_THROTTLE(get_logger(), *get_clock(), 1000,
            "← arm [S=%+.2f E=%+.2f W=%+.2f] grip=%.0f%%",
            msg.position[0], msg.position[1], msg.position[2],
            msg.position.size() > 3 ? msg.position[3] * 100.0 : 0.0);
    }

    rclcpp::Publisher<EmbodiedCommand>::SharedPtr pub_;
    rclcpp::Subscription<Odometry>::SharedPtr sub_odom_;
    rclcpp::Subscription<JointState>::SharedPtr sub_arm_;
    rclcpp::TimerBase::SharedPtr pub_timer_;

    double vx_cmd_ = 0.0, steer_cmd_ = 0.0;
    double shoulder_cmd_ = 0.35, elbow_cmd_ = 0.0, wrist_cmd_ = 0.25, gripper_cmd_ = 0.0;
    bool emergency_brake_ = false;
};

int main(int argc, char **argv) {
    rclcpp::init(argc, argv);
    auto node = std::make_shared<ControllerNode>();
    rclcpp::executors::SingleThreadedExecutor executor;
    executor.add_node(node);
    node->run(executor);
    rclcpp::shutdown();
    return 0;
}
