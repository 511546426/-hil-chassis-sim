#include "embodied_core/world_view.hpp"

#include <cmath>
#include <gtest/gtest.h>

using namespace embodied_core;

// ═══════════════════════════════════════════════════════
// 辅助函数：快速构造含有指定物体的 WorldView
// ═══════════════════════════════════════════════════════

static WorldView make_world_with(double base_x = 0.0, double base_y = 0.0,
                                 std::vector<ObjectPose> objs = {}) {
  WorldView w;
  w.base_x = base_x;
  w.base_y = base_y;
  w.objects = std::move(objs);
  return w;
}

static ObjectPose box(const std::string &name, double x, double y, double z = 0.0) {
  return ObjectPose{name, x, y, z};
}

// ═══════════════════════════════════════════════════════
// find_object
// ═══════════════════════════════════════════════════════

TEST(WorldViewTest, find_object_empty) {
  auto w = make_world_with();
  EXPECT_EQ(w.find_object("anything"), nullptr);
}

TEST(WorldViewTest, find_object_exists) {
  auto w = make_world_with(0, 0, {box("box_red", 2.5, 0.0)});
  const auto *obj = w.find_object("box_red");
  ASSERT_NE(obj, nullptr);
  EXPECT_DOUBLE_EQ(obj->x, 2.5);
  EXPECT_DOUBLE_EQ(obj->y, 0.0);
}

TEST(WorldViewTest, find_object_not_found) {
  auto w = make_world_with(0, 0, {box("box_red", 2.5, 0.0)});
  EXPECT_EQ(w.find_object("box_blue"), nullptr);
}

// ═══════════════════════════════════════════════════════
// box_red_xy
// ═══════════════════════════════════════════════════════

TEST(WorldViewTest, box_red_xy_not_found) {
  auto w = make_world_with();          // 空世界
  EXPECT_EQ(w.box_red_xy(), std::nullopt);
}

TEST(WorldViewTest, box_red_xy_found) {
  auto w = make_world_with(0, 0, {box("box_red", 2.5, 0.0)});
  auto xy = w.box_red_xy();
  ASSERT_TRUE(xy.has_value());
  EXPECT_DOUBLE_EQ(xy->first, 2.5);
  EXPECT_DOUBLE_EQ(xy->second, 0.0);
}

TEST(WorldViewTest, box_red_xy_among_multiple) {
  // 场景里有多个物体，验证能挑出 box_red 而不是别的
  auto w = make_world_with(0, 0, {
      box("box_blue", -2.0, 1.5),
      box("box_red", 3.0, 4.0),
      box("pillar", 5.0, 3.0),
  });
  auto xy = w.box_red_xy();
  ASSERT_TRUE(xy.has_value());
  EXPECT_DOUBLE_EQ(xy->first, 3.0);
  EXPECT_DOUBLE_EQ(xy->second, 4.0);
}

TEST(WorldViewTest, box_red_xy_only_other_objects) {
  // 仅有 box_blue，无 box_red → nullopt（错误路径）
  auto w = make_world_with(0, 0, {box("box_blue", -2.0, 1.5)});
  EXPECT_EQ(w.box_red_xy(), std::nullopt);
}

TEST(WorldViewTest, find_object_empty_name) {
  auto w = make_world_with(0, 0, {box("", 1.0, 2.0)});
  const auto *obj = w.find_object("");
  ASSERT_NE(obj, nullptr);
  EXPECT_DOUBLE_EQ(obj->x, 1.0);
}

// ═══════════════════════════════════════════════════════
// distance_to_box_red
// ═══════════════════════════════════════════════════════

TEST(WorldViewTest, distance_no_box) {
  auto w = make_world_with();
  EXPECT_EQ(w.distance_to_box_red(), std::nullopt);
}

TEST(WorldViewTest, distance_pythagorean) {
  // 机器人 (0,0), 红箱 (3,4) → 距离 = 5.0
  auto w = make_world_with(0, 0, {box("box_red", 3.0, 4.0)});
  auto d = w.distance_to_box_red();
  ASSERT_TRUE(d.has_value());
  EXPECT_DOUBLE_EQ(d.value(), 5.0);
}

TEST(WorldViewTest, distance_zero) {
  // 机器人和箱子在同一位置
  auto w = make_world_with(2.0, 3.0, {box("box_red", 2.0, 3.0)});
  auto d = w.distance_to_box_red();
  ASSERT_TRUE(d.has_value());
  EXPECT_DOUBLE_EQ(d.value(), 0.0);
}

TEST(WorldViewTest, distance_negative_coords) {
  // 机器人 (-1, -1), 红箱 (1, 1) → 距离 = sqrt(8) ≈ 2.828
  auto w = make_world_with(-1.0, -1.0, {box("box_red", 1.0, 1.0)});
  auto d = w.distance_to_box_red();
  ASSERT_TRUE(d.has_value());
  EXPECT_DOUBLE_EQ(d.value(), std::sqrt(8.0));
}

TEST(WorldViewTest, distance_default_scene_red_box) {
  // 与第一期场景一致：机器人在原点，红箱在 (2.5, 0)
  auto w = make_world_with(0.0, 0.0, {box("box_red", 2.5, 0.0)});
  auto d = w.distance_to_box_red();
  ASSERT_TRUE(d.has_value());
  EXPECT_DOUBLE_EQ(d.value(), 2.5);
}

TEST(WorldViewTest, distance_independent_of_base_yaw) {
  // 距离只用 base_x/base_y，与 base_yaw 无关
  auto w = make_world_with(0.0, 0.0, {box("box_red", 0.0, 3.0)});
  w.base_yaw = 1.57;
  auto d = w.distance_to_box_red();
  ASSERT_TRUE(d.has_value());
  EXPECT_DOUBLE_EQ(d.value(), 3.0);
}
