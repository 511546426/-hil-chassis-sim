from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription(
        [
            Node(
                package="learning_tools_cpp",
                executable="topic_logger_node",
                name="topic_logger_node",
                output="screen",
            ),
            Node(
                package="learning_tools_cpp",
                executable="cmd_monitor_node",
                name="cmd_monitor_node",
                output="screen",
            ),
        ]
    )
