#include "embodied_core/world_view.hpp"

#include <cmath>

namespace embodied_core {

const ObjectPose *WorldView::find_object(const std::string &name) const {
  for (const auto &obj : objects) {
    if (obj.name == name) {
      return &obj;
    }
  }
  return nullptr;
}

std::optional<std::pair<double, double>> WorldView::box_red_xy() const {
  // TODO: 你实现
  // 提示: const ObjectPose *box = find_object("box_red");
  //       if (!box) return std::nullopt;
  //       return std::pair{box->x, box->y};
  const ObjectPose *box = find_object("box_red");
  if (!box) return std::nullopt;
  return std::pair(box->x, box->y);
}

std::optional<double> WorldView::distance_to_box_red() const {
  // TODO: 你实现
  // 提示: auto xy = box_red_xy();
  //       if (!xy) return std::nullopt;
  //       return std::hypot(xy->first - base_x, xy->second - base_y);
  auto xy = box_red_xy();
  if (!xy) return std::nullopt;
  return std::hypot(xy->first - base_x, xy->second - base_y);
}

}  // namespace embodied_core


