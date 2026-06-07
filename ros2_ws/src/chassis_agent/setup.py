from setuptools import find_packages, setup

package_name = 'chassis_agent'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='changwei',
    maintainer_email='changwei@example.com',
    description='具身智能体脚本 Agent',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'agent_node = chassis_agent.agent_node:main',
        ],
    },
)
