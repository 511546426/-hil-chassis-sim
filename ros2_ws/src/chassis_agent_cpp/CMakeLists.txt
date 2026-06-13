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
find_package(onnxruntime CONFIG REQUIRED)
find_package(embodied_policy_cpp REQUIRED)

add_executable(agent_node
  src/agent_node.cpp
  src/world_from_msg.cpp
  src/goal_from_msg.cpp
)
target_include_directories(agent_node PRIVATE
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
)

target_link_libraries(agent_node
  rclcpp::rclcpp
  embodied_msgs::embodied_msgs__rosidl_typesupport_cpp
  geometry_msgs::geometry_msgs__rosidl_typesupport_cpp
  embodied_core::embodied_core
  embodied_policy_cpp::embodied_policy_cpp
  onnxruntime::onnxruntime
)
target_compile_features(agent_node PUBLIC cxx_std_17)

install(TARGETS agent_node DESTINATION lib/${PROJECT_NAME})

if(BUILD_TESTING)
  find_package(ament_cmake_gtest REQUIRED)
  ament_add_gtest(test_goal_from_msg test/test_goal_from_msg.cpp)
  target_link_libraries(test_goal_from_msg
    embodied_msgs::embodied_msgs__rosidl_typesupport_cpp
    embodied_core::embodied_core
  )
  target_sources(test_goal_from_msg PRIVATE src/goal_from_msg.cpp)
  target_include_directories(test_goal_from_msg PRIVATE
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  )
endif()

ament_package()
