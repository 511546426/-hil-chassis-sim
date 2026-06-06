cmake_minimum_required(VERSION 3.22)
project(chassis_controller)

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(nav_msgs REQUIRED)
find_package(chassis_msgs REQUIRED)

add_executable(controller_node src/controller_node.cpp)

target_link_libraries(controller_node
  rclcpp::rclcpp
  nav_msgs::nav_msgs__rosidl_typesupport_cpp
  chassis_msgs::chassis_msgs__rosidl_typesupport_cpp
)

target_compile_features(controller_node PUBLIC cxx_std_17)

install(TARGETS controller_node
  DESTINATION lib/${PROJECT_NAME})

ament_package()
