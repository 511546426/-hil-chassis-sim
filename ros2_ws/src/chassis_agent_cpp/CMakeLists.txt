cmake_minimum_required(VERSION 3.22)
project(chassis_agent_cpp)

if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
  set(CMAKE_CXX_STANDARD_REQUIRED ON)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(embodied_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(embodied_core REQUIRED)

add_executable(agent_node
  src/agent_node.cpp
  src/world_from_msg.cpp
)
target_include_directories(agent_node PRIVATE
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
)

target_link_libraries(agent_node
  rclcpp::rclcpp
  embodied_msgs::embodied_msgs__rosidl_typesupport_cpp
  geometry_msgs::geometry_msgs__rosidl_typesupport_cpp
  embodied_core::embodied_core
)
target_compile_features(agent_node PUBLIC cxx_std_17)

install(TARGETS agent_node DESTINATION lib/${PROJECT_NAME})

ament_package()
