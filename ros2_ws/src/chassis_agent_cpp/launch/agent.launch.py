from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    push_min_dist = LaunchConfiguration("push_min_dist")

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "push_min_dist",
                default_value="0.20",
                description=(
                    "Minimum box displacement required for the push task "
                    "to succeed, in meters"
                ),
            ),
            Node(
                package="chassis_agent_cpp",
                executable="agent_node",
                name="agent_node_cpp",
                output="screen",
                parameters=[
                    {
                        "brain": "rule",
                        "push_min_dist": ParameterValue(
                            push_min_dist,
                            value_type=float,
                        ),
                    }
                ],
            ),
        ]
    )
