/**
 * agent_node —— C++ 具身 Agent（第二期 M3：PushRedBoxFSM）
 *
 * 数据流：
 *   sub /world_state  →  WorldView  →  PushRedBoxFSM  →  /control_cmd
 */

#include <optional>
#include <string>

#include <embodied_msgs/msg/embodied_command.hpp>
#include <embodied_msgs/msg/embodied_world_state.hpp>
#include <embodied_core/arm_preset.hpp>
#include <embodied_core/push_red_box_fsm.hpp>
#include <embodied_core/skill_executor.hpp>
#include <rclcpp/rclcpp.hpp>

#include "chassis_agent_cpp/world_from_msg.hpp"

using namespace std::chrono_literals;
using EmbodiedCommand = embodied_msgs::msg::EmbodiedCommand;
using EmbodiedWorldState = embodied_msgs::msg::EmbodiedWorldState;

namespace {

constexpr double kControlPeriodSec = 0.02;
constexpr double kDefaultStandoff = 0.35;
constexpr double kDefaultArriveDist = 0.3;

embodied_core::PushRedBoxFSM::Config fsm_config_from_node(rclcpp::Node &node) {
  embodied_core::PushRedBoxFSM::Config cfg;
  cfg.standoff = node.get_parameter("standoff").as_double();
  cfg.arrive_dist = node.get_parameter("arrive_dist").as_double();
  return cfg;
}

}  // namespace

class AgentNode : public rclcpp::Node {
 public:
  AgentNode() : Node("agent_node_cpp") {
    declare_parameter("standoff", kDefaultStandoff);
    declare_parameter("arrive_dist", kDefaultArriveDist);

    const double standoff = get_parameter("standoff").as_double();
    const double arrive_dist = get_parameter("arrive_dist").as_double();

    executor_ = embodied_core::SkillExecutor(
        embodied_core::NavigateSkill(standoff, arrive_dist),
        embodied_core::ManipulateSkill{});
    fsm_ = embodied_core::PushRedBoxFSM(fsm_config_from_node(*this));

    sub_world_ = create_subscription<EmbodiedWorldState>(
        "/world_state", 10,
        [this](const EmbodiedWorldState::SharedPtr msg) { on_world_state(*msg); });

    pub_cmd_ = create_publisher<EmbodiedCommand>("/control_cmd", 10);
    timer_ = create_wall_timer(20ms, [this]() { publish_cmd(); });

    RCLCPP_INFO(get_logger(), "C++ agent_node 已启动（M3 PushRedBoxFSM）");
    RCLCPP_INFO(
        get_logger(),
        "  任务: NAV → REACH → CLOSE_GRIPPER → BACK_UP → DONE");
    RCLCPP_INFO(
        get_logger(),
        "  standoff=%.2f m  arrive_dist=%.2f m",
        standoff, arrive_dist);
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
    if (!world_valid_ || !world_) {
      out.arm_shoulder = embodied_core::kArmStow.shoulder;
      out.arm_elbow = embodied_core::kArmStow.elbow;
      out.arm_wrist = embodied_core::kArmStow.wrist;
      out.gripper = 0.0;
    } else {
      out = fsm_.tick(*world_, executor_, kControlPeriodSec);

      if (auto log = fsm_.take_transition_log()) {
        RCLCPP_INFO(get_logger(), "%s", log->c_str());
      }
      if (fsm_.should_enable_virtual_grasp()) {
        RCLCPP_INFO_ONCE(get_logger(), "FSM 请求 virtual grasp（M5 实现 service）");
      }
      if (fsm_.should_disable_virtual_grasp()) {
        RCLCPP_INFO_ONCE(get_logger(), "FSM 请求释放 virtual grasp（M5 实现 service）");
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
    const std::string summary =
        std::string("phase=") + fsm_.phase_name() +
        " base[vx=" + std::to_string(out.target_linear_x) +
        " steer=" + std::to_string(out.target_steering_angle) + "]" +
        " grip=" + std::to_string(out.gripper);
    if (summary != last_cmd_log_) {
      RCLCPP_INFO(get_logger(), "→ cmd %s", summary.c_str());
      last_cmd_log_ = summary;
    }
  }

  embodied_core::SkillExecutor executor_;
  embodied_core::PushRedBoxFSM fsm_;

  rclcpp::Subscription<EmbodiedWorldState>::SharedPtr sub_world_;
  rclcpp::Publisher<EmbodiedCommand>::SharedPtr pub_cmd_;
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
