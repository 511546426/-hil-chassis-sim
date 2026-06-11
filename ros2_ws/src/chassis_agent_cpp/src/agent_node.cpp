/**
 * agent_node —— C++ 具身 Agent（P3-M0：Brain 接口 + RuleBrain）
 *
 * 数据流：
 *   sub /world_state  →  WorldView  →  Brain  →  /control_cmd
 */

#include <memory>
#include <optional>
#include <string>

#include <embodied_msgs/msg/embodied_command.hpp>
#include <embodied_msgs/msg/embodied_world_state.hpp>
#include <embodied_msgs/srv/set_virtual_grasp.hpp>
#include <embodied_core/brain.hpp>
#include <embodied_core/arm_preset.hpp>
#include <embodied_core/rule_brain.hpp>
#include <embodied_core/task_goal.hpp>
#include <rclcpp/rclcpp.hpp>

#include "chassis_agent_cpp/world_from_msg.hpp"

using namespace std::chrono_literals;
using EmbodiedCommand = embodied_msgs::msg::EmbodiedCommand;
using EmbodiedWorldState = embodied_msgs::msg::EmbodiedWorldState;
using SetVirtualGrasp = embodied_msgs::srv::SetVirtualGrasp;

namespace {

constexpr double kControlPeriodSec = 0.02;
constexpr double kDefaultStandoff = 0.35;
constexpr double kDefaultArriveDist = 0.3;

embodied_core::RuleBrain::Config rule_brain_config_from_node(rclcpp::Node &node) {
  embodied_core::RuleBrain::Config cfg;
  cfg.standoff = node.get_parameter("standoff").as_double();
  cfg.arrive_dist = node.get_parameter("arrive_dist").as_double();
  cfg.fsm.standoff = cfg.standoff;
  cfg.fsm.arrive_dist = cfg.arrive_dist;
  return cfg;
}

std::unique_ptr<embodied_core::Brain> make_brain(
    rclcpp::Node &node,
    const embodied_core::RuleBrain::Config &rule_cfg) {
  const std::string brain_type = node.get_parameter("brain").as_string();
  if (brain_type == "rule") {
    auto brain = std::make_unique<embodied_core::RuleBrain>(rule_cfg);
    brain->reset(embodied_core::TaskGoal::push_red_box());
    return brain;
  }
  if (brain_type == "rl") {
    RCLCPP_FATAL(
        node.get_logger(),
        "brain=rl 尚未实现（P3-M2 ONNX + RLBrain）；请使用 brain:=rule");
    throw std::runtime_error("brain=rl not implemented");
  }
  RCLCPP_FATAL(
      node.get_logger(),
      "未知 brain 类型: %s（支持: rule, rl）",
      brain_type.c_str());
  throw std::runtime_error("unknown brain type");
}

}  // namespace

class AgentNode : public rclcpp::Node {
 public:
  AgentNode() : Node("agent_node_cpp") {
    declare_parameter("brain", "rule");
    declare_parameter("policy", "");
    declare_parameter("standoff", kDefaultStandoff);
    declare_parameter("arrive_dist", kDefaultArriveDist);

    const auto rule_cfg = rule_brain_config_from_node(*this);
    brain_ = make_brain(*this, rule_cfg);

    const std::string brain_type = get_parameter("brain").as_string();
    RCLCPP_INFO(get_logger(), "C++ agent_node 已启动（brain=%s）", brain_type.c_str());
    if (brain_type == "rule") {
      RCLCPP_INFO(
          get_logger(),
          "  任务: NAV → REACH → 夹爪 → 倒车推箱（≥ 0.2 m）");
    }
    RCLCPP_INFO(
        get_logger(),
        "  standoff=%.2f m  arrive_dist=%.2f m",
        rule_cfg.standoff,
        rule_cfg.arrive_dist);

    sub_world_ = create_subscription<EmbodiedWorldState>(
        "/world_state", 10,
        [this](const EmbodiedWorldState::SharedPtr msg) { on_world_state(*msg); });

    pub_cmd_ = create_publisher<EmbodiedCommand>("/control_cmd", 10);
    grasp_client_ = create_client<SetVirtualGrasp>("/sim/set_virtual_grasp");
    timer_ = create_wall_timer(20ms, [this]() { publish_cmd(); });
  }

 private:
  void on_world_state(const EmbodiedWorldState &msg) {
    world_ = chassis_agent_cpp::world_from_msg(msg);
    world_valid_ = true;
  }

  void publish_cmd() {
    EmbodiedCommand cmd;
    cmd.emergency_brake = false;

    embodied_core::SkillOutput out;
    if (!world_valid_ || !world_ || !brain_) {
      out.arm_shoulder = embodied_core::kArmStow.shoulder;
      out.arm_elbow = embodied_core::kArmStow.elbow;
      out.arm_wrist = embodied_core::kArmStow.wrist;
      out.gripper = 0.0;
    } else {
      out = brain_->act(*world_, kControlPeriodSec);

      if (auto log = brain_->take_transition_log()) {
        RCLCPP_INFO(get_logger(), "%s", log->c_str());
      }
      if (brain_->should_enable_virtual_grasp()) {
        call_virtual_grasp(true, "box_red");
      }
      if (brain_->should_disable_virtual_grasp()) {
        call_virtual_grasp(false, "box_red");
      }
    }

    cmd.target_linear_x = out.target_linear_x;
    cmd.target_steering_angle = out.target_steering_angle;
    cmd.arm_shoulder = out.arm_shoulder;
    cmd.arm_elbow = out.arm_elbow;
    cmd.arm_wrist = out.arm_wrist;
    cmd.gripper = out.gripper;
    pub_cmd_->publish(cmd);

    log_cmd_throttled(out);
  }

  void log_cmd_throttled(const embodied_core::SkillOutput &out) {
    const std::string phase = brain_ ? brain_->phase_name() : "N/A";
    const std::string summary =
        std::string("phase=") + phase +
        " base[vx=" + std::to_string(out.target_linear_x) +
        " steer=" + std::to_string(out.target_steering_angle) + "]" +
        " grip=" + std::to_string(out.gripper);
    if (summary != last_cmd_log_) {
      RCLCPP_INFO(get_logger(), "→ cmd %s", summary.c_str());
      last_cmd_log_ = summary;
    }
  }

  void call_virtual_grasp(bool enable, const std::string &object_name) {
    if (!grasp_client_->service_is_ready()) {
      RCLCPP_WARN(
          get_logger(),
          "virtual grasp service 不可用 (enable=%d object=%s)",
          enable ? 1 : 0,
          object_name.c_str());
      return;
    }

    auto request = std::make_shared<SetVirtualGrasp::Request>();
    request->enable = enable;
    request->object_name = object_name;

    grasp_client_->async_send_request(
        request,
        [this, enable](rclcpp::Client<SetVirtualGrasp>::SharedFuture future) {
          const auto response = future.get();
          if (response->success) {
            RCLCPP_INFO(
                get_logger(),
                "virtual grasp %s: %s",
                enable ? "ON" : "OFF",
                response->message.c_str());
          } else {
            RCLCPP_WARN(
                get_logger(),
                "virtual grasp %s 失败: %s",
                enable ? "ON" : "OFF",
                response->message.c_str());
          }
        });
  }

  std::unique_ptr<embodied_core::Brain> brain_;

  rclcpp::Subscription<EmbodiedWorldState>::SharedPtr sub_world_;
  rclcpp::Publisher<EmbodiedCommand>::SharedPtr pub_cmd_;
  rclcpp::Client<SetVirtualGrasp>::SharedPtr grasp_client_;
  rclcpp::TimerBase::SharedPtr timer_;

  std::optional<embodied_core::WorldView> world_;
  bool world_valid_{false};
  std::string last_cmd_log_;
};

int main(int argc, char **argv) {
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<AgentNode>());
  rclcpp::shutdown();
  return 0;
}
