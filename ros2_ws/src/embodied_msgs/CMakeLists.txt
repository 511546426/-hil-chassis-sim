cmake_minimum_required(VERSION 3.22)
project(embodied_msgs)

find_package(ament_cmake REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(std_msgs REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/EmbodiedCommand.msg"
  "msg/EmbodiedWorldState.msg"
  "msg/EmbodiedGoal.msg"
  "msg/EmbodiedTaskPlan.msg"
  "srv/SetVirtualGrasp.srv"
  "srv/ResetEpisode.srv"
  DEPENDENCIES std_msgs geometry_msgs
)

ament_export_dependencies(rosidl_default_runtime)
ament_package()
