#include "embodied_core/navigate_skill.hpp"

#include "embodied_core/arm_preset.hpp"

namespace embodied_core {

namespace {

constexpr double kFallbackBoxCenterX = 2.5;
constexpr double kFallbackBoxCenterY = 0.0;

}  // namespace

NavigateSkill::NavigateSkill(double standoff, double arrive_dist, double max_vx_reverse)
    : standoff_(standoff),
      arrive_dist_(arrive_dist),
      max_vx_reverse_(max_vx_reverse) {}

SkillOutput NavigateSkill::make_output(const NavigationCommand &nav) const {
  SkillOutput out;
  out.target_linear_x = nav.target_linear_x;
  out.target_steering_angle = nav.target_steering_angle;
  out.arm_shoulder = kArmStow.shoulder;
  out.arm_elbow = kArmStow.elbow;
  out.arm_wrist = kArmStow.wrist;
  out.gripper = 0.0;
  out.emergency_brake = false;
  return out;
}

SkillOutput NavigateSkill::compute(
    const WorldView &world,
    double target_x, double target_y,
    bool reverse) const {
  if (reverse) {
    // TODO(changwei): M6 倒车推箱 — 参考 PHASE2_CPP_IMPLEMENTATION_GUIDE §9
    // 建议：target_linear_x = -max_vx_reverse_，steer 按目标朝向微调
    SkillOutput out = make_output(NavigationCommand{0.0, 0.0, false});
    out.target_linear_x = -max_vx_reverse_;
    return out;
  }

  double goal_x = target_x;
  double goal_y = target_y;
  approach_point(
      world.base_x, world.base_y,
      target_x, target_y,
      standoff_,
      goal_x, goal_y);

  const NavigationCommand nav = pure_pursuit(
      world.base_x, world.base_y, world.base_yaw,
      goal_x, goal_y,
      arrive_dist_);

  return make_output(nav);
}

SkillOutput NavigateSkill::compute_to_box_red(
    const WorldView &world,
    bool reverse) const {
  const auto box = world.box_red_xy();
  // 传箱子中心，compute() 内 approach_point 统一做 standoff
  const double target_x = box ? box->first : kFallbackBoxCenterX;
  const double target_y = box ? box->second : kFallbackBoxCenterY;
  return compute(world, target_x, target_y, reverse);
}

}  // namespace embodied_core
