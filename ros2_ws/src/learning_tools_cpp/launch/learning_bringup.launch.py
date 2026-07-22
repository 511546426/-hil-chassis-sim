from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    enable_topic_logger = LaunchConfiguration("enable_topic_logger")
    enable_cmd_monitor = LaunchConfiguration("enable_cmd_monitor")

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "enable_topic_logger",
                default_value="true",
                description="Enable topic logger",
            ),
            DeclareLaunchArgument(
                "enable_cmd_monitor",
                default_value="true",
                description="Enable command monitor",
            ),
            Node(
                package="learning_tools_cpp",
                executable="topic_logger_node",
                name="topic_logger_node",
                output="screen",
                condition=IfCondition(enable_topic_logger),
            ),
            Node(
                package="learning_tools_cpp",
                executable="cmd_monitor_node",
                name="cmd_monitor_node",
                output="screen",
                condition=IfCondition(enable_cmd_monitor),
            ),
        ]
    )
