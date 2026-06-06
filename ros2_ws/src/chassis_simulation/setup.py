import os
from glob import glob

from setuptools import find_packages, setup

package_name = 'chassis_simulation'

setup(
    name=package_name,
    version='0.2.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
    ],
    install_requires=['setuptools'],
    # chassis_msgs 由 colcon 工作区提供
    zip_safe=True,
    maintainer='changwei',
    maintainer_email='changwei@example.com',
    description='MuJoCo 模拟底盘节点',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'simulation_node = chassis_simulation.simulation_node:main',
        ],
    },
)
