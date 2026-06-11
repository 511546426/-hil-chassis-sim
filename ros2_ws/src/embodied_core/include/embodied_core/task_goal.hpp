#pragma once

#include <cstdint>
#include <string>

namespace embodied_core {

/// 任务目标（第三期 TaskSpec / Brain 共用；先于 EmbodiedGoal.msg）
enum class TaskGoalKind : uint8_t {
  Point,
  Object,
  PushRedBox,
};

struct TaskGoal {
  TaskGoalKind kind{TaskGoalKind::PushRedBox};
  double x{0.0};
  double y{0.0};
  std::string object_name{"box_red"};
  double standoff{0.35};

  [[nodiscard]] static TaskGoal push_red_box() {
    TaskGoal goal;
    goal.kind = TaskGoalKind::PushRedBox;
    goal.object_name = "box_red";
    return goal;
  }

  [[nodiscard]] static TaskGoal point(double px, double py) {
    TaskGoal goal;
    goal.kind = TaskGoalKind::Point;
    goal.x = px;
    goal.y = py;
    return goal;
  }

  [[nodiscard]] static TaskGoal nav_to_object(
      const std::string &object_name,
      double standoff = 0.35) {
    TaskGoal goal;
    goal.kind = TaskGoalKind::Object;
    goal.object_name = object_name;
    goal.standoff = standoff;
    return goal;
  }
};

}  // namespace embodied_core
