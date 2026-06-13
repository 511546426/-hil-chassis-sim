/**
 * agent_node —— C++ 具身 Agent（P3-M0：Brain 接口 + RuleBrain）
 *
 * 数据流：
 *   sub /world_state  →  WorldView  →  Brain  →  /control_cmd
 *   sub /task_plan    →  brain=auto 时按 recommended_brain 切换
 */

#include <memory>
#include <optional>
#include <string>

#include <embodied_msgs/msg/embodied_command.hpp>
#include <embodied_msgs/msg/embodied_goal.hpp>
#include <embodied_msgs/msg/embodied_world_state.hpp>
#include <embodied_msgs/msg/embodied_task_plan.hpp>
#include <embodied_msgs/srv/reset_episode.hpp>
#include <embodied_msgs/srv/set_virtual_grasp.hpp>
#include <embodied_core/brain.hpp>
#include <embodied_core/arm_preset.hpp>
#include <embodied_core/rule_brain.hpp>
#include <embodied_core/task_goal.hpp>
#include <embodied_policy_cpp/hybrid_brain.hpp>
#include <embodied_policy_cpp/rl_brain.hpp>
#include <rclcpp/qos.hpp>
#include <rclcpp/rclcpp.hpp>

#include "chassis_agent_cpp/goal_from_msg.hpp"
#include "chassis_agent_cpp/world_from_msg.hpp"

using namespace std::chrono_literals;
using EmbodiedCommand = embodied_msgs::msg::EmbodiedCommand;
using EmbodiedWorldState = embodied_msgs::msg::EmbodiedWorldState;
using EmbodiedTaskPlan = embodied_msgs::msg::EmbodiedTaskPlan;
using SetVirtualGrasp = embodied_msgs::srv::SetVirtualGrasp;
using ResetEpisode = embodied_msgs::srv::ResetEpisode;

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

embodied_core::TaskGoal rl_task_goal_from_node(rclcpp::Node &node) {
  const double standoff = node.get_parameter("standoff").as_double();
  const std::string task = node.get_parameter("task").as_string();
  if (task == "nav_to_box_red" || task == "box_red") {
    return embodied_core::TaskGoal::nav_to_object("box_red", standoff);
  }
  if (task == "push_red_box") {
    return embodied_core::TaskGoal::push_red_box();
  }
  return embodied_core::TaskGoal::nav_to_object("box_red", standoff);
}

embodied_core::TaskGoal agent_task_goal_from_node(
    rclcpp::Node &node,
    const std::string &brain_type) {
  if (brain_type == "rule" || brain_type == "hybrid") {
    return embodied_core::TaskGoal::push_red_box();
  }
  return rl_task_goal_from_node(node);
}

std::unique_ptr<embodied_core::Brain> make_brain(
    rclcpp::Node &node,
    const embodied_core::RuleBrain::Config &rule_cfg,
    const std::string &brain_type) {
  if (brain_type == "rule") {
    return std::make_unique<embodied_core::RuleBrain>(rule_cfg);
  }
  if (brain_type == "rl") {
    const std::string policy_path = node.get_parameter("policy").as_string();
    if (policy_path.empty()) {
      RCLCPP_FATAL(node.get_logger(), "brain=rl 需要 -p policy:=/path/to/nav_policy.onnx");
      throw std::runtime_error("policy path required for brain=rl");
    }
    embodied_policy_cpp::RLBrain::Config rl_cfg;
    rl_cfg.policy_path = policy_path;
    rl_cfg.goal = rl_task_goal_from_node(node);
    rl_cfg.arrive_dist = node.get_parameter("arrive_dist").as_double();
    return std::make_unique<embodied_policy_cpp::RLBrain>(rl_cfg);
  }
  if (brain_type == "hybrid") {
    const std::string policy_path = node.get_parameter("policy").as_string();
    if (policy_path.empty()) {
      RCLCPP_FATAL(
          node.get_logger(),
          "brain=hybrid 需要 -p policy:=/path/to/nav_policy.onnx");
      throw std::runtime_error("policy path required for brain=hybrid");
    }
    embodied_policy_cpp::HybridBrain::Config hybrid_cfg;
    hybrid_cfg.rl.policy_path = policy_path;
    hybrid_cfg.rl.goal = embodied_core::TaskGoal::nav_to_object(
        "box_red", node.get_parameter("standoff").as_double());
    hybrid_cfg.rl.arrive_dist = node.get_parameter("arrive_dist").as_double();
    hybrid_cfg.fsm = rule_cfg.fsm;
    return std::make_unique<embodied_policy_cpp::HybridBrain>(hybrid_cfg);
  }
  RCLCPP_FATAL(
      node.get_logger(),
      "未知 brain 类型: %s（支持: rule, rl, hybrid, auto）",
      brain_type.c_str());
  throw std::runtime_error("unknown brain type");
}

}  // namespace

class AgentNode : public rclcpp::Node {
 public:
  AgentNode() : Node("agent_node_cpp") {
    declare_parameter("brain", "rule");
    declare_parameter("policy", "");
    declare_parameter("task", "nav_to_box_red");
    declare_parameter("standoff", kDefaultStandoff);
    declare_parameter("arrive_dist", kDefaultArriveDist);
    declare_parameter("listen_task_plan", true);
    declare_parameter("auto_push_brain", "rule");

    rule_cfg_ = rule_brain_config_from_node(*this);
    brain_mode_ = get_parameter("brain").as_string();
    auto_push_brain_ = get_parameter("auto_push_brain").as_string();

    if (brain_mode_ == "auto") {
      RCLCPP_INFO(
          get_logger(),
          "C++ agent_node 已启动（brain=auto，等待 /task_plan）");
      RCLCPP_INFO(
          get_logger(),
          "  auto_push_brain=%s  policy=%s",
          auto_push_brain_.c_str(),
          get_parameter("policy").as_string().c_str());
    } else {
      task_goal_ = agent_task_goal_from_node(*this, brain_mode_);
      activate_brain(brain_mode_, task_goal_);
      log_brain_startup(brain_mode_);
    }

    sub_world_ = create_subscription<EmbodiedWorldState>(
        "/world_state", 10,
        [this](const EmbodiedWorldState::SharedPtr msg) { on_world_state(*msg); });

    if (get_parameter("listen_task_plan").as_bool()) {
      rclcpp::QoS plan_qos(1);
      plan_qos.transient_local();
      sub_task_plan_ = create_subscription<EmbodiedTaskPlan>(
          "/task_plan",
          plan_qos,
          [this](const EmbodiedTaskPlan::SharedPtr msg) { on_task_plan(*msg); });
      RCLCPP_INFO(get_logger(), "  订阅 /task_plan（P3-C2 planner）");
    }

    pub_cmd_ = create_publisher<EmbodiedCommand>("/control_cmd", 10);
    grasp_client_ = create_client<SetVirtualGrasp>("/sim/set_virtual_grasp");
    srv_reset_ = create_service<ResetEpisode>(
        "/agent/reset_episode",
        [this](
            const ResetEpisode::Request::SharedPtr request,
            ResetEpisode::Response::SharedPtr response) {
          (void)request;
          reset_brain_episode(response);
        });
    timer_ = create_wall_timer(20ms, [this]() { publish_cmd(); });
  }

 private:
  void log_brain_startup(const std::string &brain_type) {
    RCLCPP_INFO(get_logger(), "C++ agent_node 已激活（brain=%s）", brain_type.c_str());
    if (brain_type == "rule") {
      RCLCPP_INFO(
          get_logger(),
          "  任务: NAV → REACH → 夹爪 → 倒车推箱（≥ 0.2 m）");
      RCLCPP_INFO(
          get_logger(),
          "  standoff=%.2f m  arrive_dist=%.2f m",
          rule_cfg_.standoff,
          rule_cfg_.arrive_dist);
    } else if (brain_type == "rl") {
      RCLCPP_INFO(
          get_logger(),
          "  任务: RL 导航（policy=%s）",
          get_parameter("policy").as_string().c_str());
    } else if (brain_type == "hybrid") {
      RCLCPP_INFO(
          get_logger(),
          "  任务: Hybrid 推红箱（policy=%s）",
          get_parameter("policy").as_string().c_str());
    }
  }

  void activate_brain(
      const std::string &brain_type,
      const embodied_core::TaskGoal &goal) {
    if (brain_type != active_brain_type_ || !brain_) {
      brain_ = make_brain(*this, rule_cfg_, brain_type);
      active_brain_type_ = brain_type;
      log_brain_startup(brain_type);
    }
    task_goal_ = goal;
    brain_->reset(task_goal_);
    last_cmd_log_.clear();
  }

  void reset_brain_episode(const ResetEpisode::Response::SharedPtr &response) {
    if (!brain_) {
      response->success = false;
      response->message = "brain not initialized (waiting for /task_plan?)";
      return;
    }
    brain_->reset(task_goal_);
    last_cmd_log_.clear();
    response->success = true;
    response->message = "agent brain reset";
    RCLCPP_INFO(get_logger(), "%s", response->message.c_str());
  }

  void on_task_plan(const EmbodiedTaskPlan &plan) {
    if (plan.goals.empty()) {
      RCLCPP_WARN(get_logger(), "忽略空 TaskPlan source=%s", plan.source.c_str());
      return;
    }
    const embodied_core::TaskGoal goal =
        chassis_agent_cpp::task_goal_from_msg(plan.goals.front());

    std::string brain_type = brain_mode_;
    if (brain_mode_ == "auto") {
      brain_type = chassis_agent_cpp::resolve_recommended_brain(
          plan, auto_push_brain_);
    }

    activate_brain(brain_type, goal);
    RCLCPP_INFO(
        get_logger(),
        "TaskPlan 已应用 source=%s raw=%s brain=%s goals=%zu",
        plan.source.c_str(),
        plan.raw_text.c_str(),
        brain_type.c_str(),
        plan.goals.size());
  }

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
    const std::string phase = brain_ ? brain_->phase_name() : "Idle";
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

  embodied_core::RuleBrain::Config rule_cfg_{};
  std::string brain_mode_;
  std::string auto_push_brain_;
  std::string active_brain_type_;

  std::unique_ptr<embodied_core::Brain> brain_;
  embodied_core::TaskGoal task_goal_{embodied_core::TaskGoal::push_red_box()};

  rclcpp::Subscription<EmbodiedWorldState>::SharedPtr sub_world_;
  rclcpp::Subscription<EmbodiedTaskPlan>::SharedPtr sub_task_plan_;
  rclcpp::Publisher<EmbodiedCommand>::SharedPtr pub_cmd_;
  rclcpp::Client<SetVirtualGrasp>::SharedPtr grasp_client_;
  rclcpp::Service<ResetEpisode>::SharedPtr srv_reset_;
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
