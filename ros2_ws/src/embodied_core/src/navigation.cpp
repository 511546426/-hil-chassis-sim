#include "embodied_core/navigation.hpp"

#include <cmath>

namespace embodied_core {

namespace {

constexpr double kPi = 3.14159265358979323846;
constexpr double kTwoPi = 2.0 * kPi;

}  // namespace

// 见 navigation.hpp：角度归一化到 (-π, π]
double normalize_angle(double angle) {
  while (angle > kPi) {
    angle -= kTwoPi;
  }
  while (angle < -kPi) {
    angle += kTwoPi;
  }
  return angle;
}

// 见 navigation.hpp：在 target 沿 base→target 方向前留出 standoff，结果写入 out_x/out_y
void approach_point(
    double base_x, double base_y,
    double target_x, double target_y,
    double standoff,
    double &out_x, double &out_y) {
  const double dx = target_x - base_x;
  const double dy = target_y - base_y;
  const double dist = std::hypot(dx, dy);
  if (dist < 1e-3) {
    out_x = target_x - standoff;
    out_y = target_y;
    return;
  }
  const double scale = std::max(0.0, dist - standoff) / dist;
  out_x = base_x + dx * scale;
  out_y = base_y + dy * scale;
}

// 见 navigation.hpp：Pure Pursuit 主入口；输入位姿+目标点，输出 NavigationCommand
NavigationCommand pure_pursuit(
    double x, double y, double yaw,
    double target_x, double target_y,
    double arrive_dist,
    double look_ahead,
    double max_vx,
    double max_steer,
    double wheelbase) {
  const double dx = target_x - x;
  const double dy = target_y - y;
  const double dist = std::hypot(dx, dy);

  if (dist < arrive_dist) {
    return NavigationCommand{0.0, 0.0, true};
  }

  const double target_heading = std::atan2(dy, dx);
  const double heading_err = normalize_angle(target_heading - yaw);

  double lx = target_x;
  double ly = target_y;
  if (dist > look_ahead) {
    lx = x + look_ahead * std::cos(target_heading);
    ly = y + look_ahead * std::sin(target_heading);
  }

  const double local_y =
      std::sin(-yaw) * (lx - x) + std::cos(-yaw) * (ly - y);
  const double curvature = 2.0 * local_y / std::max(look_ahead * look_ahead, 1e-6);
  double steer = std::atan(curvature * wheelbase);
  steer = std::max(-max_steer, std::min(max_steer, steer));

  const double speed_factor = std::max(0.5, std::cos(heading_err));
  double vx = max_vx * speed_factor;
  if (std::abs(heading_err) > kPi / 4.0) {
    vx *= 0.5;
  }

  return NavigationCommand{vx, steer, false};
}

// 见 navigation.hpp：顶箱卡住时提前结束导航
bool stuck_at_box(const WorldView &world, double cmd_vx) {
  const auto dist = world.distance_to_box_red();
  if (!dist) {
    return false;
  }
  if (*dist <= 0.52 && cmd_vx > 0.05) {
    return true;
  }
  return cmd_vx > 0.15 && std::abs(world.base_vx) < 0.05 && *dist < 0.75;
}

}  // namespace embodied_core
