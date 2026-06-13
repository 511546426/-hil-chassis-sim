from setuptools import find_packages, setup

package_name = 'embodied_planner'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools', 'pyyaml', 'pydantic'],
    zip_safe=True,
    maintainer='changwei',
    maintainer_email='changwei@example.com',
    description='P3-C2 task planner for embodied agent',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'task_planner_node = embodied_planner.task_planner_node:main',
        ],
    },
)
