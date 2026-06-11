#include "embodied_core/nav_obs_encoder.hpp"

#include <cmath>

#include "embodied_core/navigation.hpp"
#include "embodied_core/nav_obs_spec.hpp"

namespace embodied_core {

namespace {

bool resolve_goal_xy(
    const WorldView &world,
    const TaskGoal &goal,
    double &out_x,
    double &out_y) {
  switch (goal.kind) {
    case TaskGoalKind::Point:
      out_x = goal.x;
      out_y = goal.y;
      return true;
    case TaskGoalKind::Object:
    case TaskGoalKind::PushRedBox: {
      const std::string &name =
          goal.kind == TaskGoalKind::PushRedBox ? "box_red" : goal.object_name;
      const ObjectPose *obj = world.find_object(name);
      if (obj == nullptr) {
        out_x = goal.x;
        out_y = goal.y;
        return goal.x != 0.0 || goal.y != 0.0;
      }
      out_x = obj->x;
      out_y = obj->y;
      return true;
    }
  }
  return false;
}

void apply_standoff(
    const WorldView &world,
    double standoff,
    double &target_x,
    double &target_y) {
  if (standoff <= 0.0) {
    return;
  }
  const double dx = target_x - world.base_x;
  const double dy = target_y - world.base_y;
  const double dist = std::hypot(dx, dy);
  if (dist <= standoff) {
    return;
  }
  const double scale = (dist - standoff) / dist;
  target_x = world.base_x + dx * scale;
  target_y = world.base_y + dy * scale;
}

}  // namespace

NavObservation encode_nav_obs(const WorldView &world, const TaskGoal &goal) {
  NavObservation obs{};

  double target_x = 0.0;
  double target_y = 0.0;
  if (!resolve_goal_xy(world, goal, target_x, target_y)) {
    target_x = goal.x;
    target_y = goal.y;
  }
  apply_standoff(world, goal.standoff, target_x, target_y);

  const double wx = target_x - world.base_x;
  const double wy = target_y - world.base_y;
  const double cos_yaw = std::cos(world.base_yaw);
  const double sin_yaw = std::sin(world.base_yaw);
  const double goal_dx = cos_yaw * wx + sin_yaw * wy;
  const double goal_dy = -sin_yaw * wx + cos_yaw * wy;
  const double dist = std::hypot(wx, wy);

  obs[kObsBaseX] = world.base_x / kNavObsArenaHalf;
  obs[kObsBaseY] = world.base_y / kNavObsArenaHalf;
  obs[kObsBaseYaw] = normalize_angle(world.base_yaw) / M_PI;
  obs[kObsGoalDx] = goal_dx / kNavObsGoalScale;
  obs[kObsGoalDy] = goal_dy / kNavObsGoalScale;
  obs[kObsDistGoal] = dist / kNavObsGoalScale;
  obs[kObsBaseVx] = world.base_vx / kNavObsMaxVx;
  obs[kObsBaseSteerAbs] = std::abs(world.base_steer) / kNavObsMaxSteer;

  return obs;
}

double nav_goal_distance(const WorldView &world, const TaskGoal &goal) {
  double target_x = 0.0;
  double target_y = 0.0;
  if (!resolve_goal_xy(world, goal, target_x, target_y)) {
    target_x = goal.x;
    target_y = goal.y;
  }
  apply_standoff(world, goal.standoff, target_x, target_y);
  const double wx = target_x - world.base_x;
  const double wy = target_y - world.base_y;
  return std::hypot(wx, wy);
}

}  // namespace embodied_core
