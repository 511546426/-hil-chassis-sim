cmake_minimum_required(VERSION 3.22)
project(learning_tools_cpp)

if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
  set(CMAKE_CXX_STANDARD_REQUIRED ON)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(nav_msgs REQUIRED)
find_package(embodied_msgs REQUIRED)

add_executable(topic_logger_node src/topic_logger_node.cpp)
target_link_libraries(topic_logger_node
  rclcpp::rclcpp
  nav_msgs::nav_msgs__rosidl_typesupport_cpp
)
target_compile_features(topic_logger_node PUBLIC cxx_std_17)

add_executable(cmd_monitor_node src/cmd_monitor_node.cpp)
target_link_libraries(cmd_monitor_node
  rclcpp::rclcpp
  embodied_msgs::embodied_msgs__rosidl_typesupport_cpp
)
target_compile_features(cmd_monitor_node PUBLIC cxx_std_17)

install(TARGETS
  topic_logger_node
  cmd_monitor_node
  DESTINATION lib/${PROJECT_NAME}
)

install(
  DIRECTORY launch
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
