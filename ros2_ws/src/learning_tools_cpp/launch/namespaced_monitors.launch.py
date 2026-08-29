from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription(
        [
            Node(
                package="learning_tools_cpp",
                executable="topic_logger_node",
                namespace="robot1",
                name="state_monitor",
                parameters=[
                    {
                        "topic_name": "chassis_state",
                        "log_every_n": 2,
                    }
                ],
                output="screen",
            ),
            Node(
                package="learning_tools_cpp",
                executable="topic_logger_node",
                namespace="robot2",
                name="state_monitor",
                parameters=[
                    {
                        "topic_name": "chassis_state",
                        "log_every_n": 3,
                    }
                ],
                output="screen",
            ),
        ]
    )
