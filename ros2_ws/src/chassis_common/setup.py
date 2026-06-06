from setuptools import find_packages, setup

package_name = 'chassis_common'

setup(
    name=package_name,
    version='0.2.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='changwei',
    maintainer_email='changwei@example.com',
    description='共享底盘 MuJoCo 模型与运动学工具',
    license='Apache-2.0',
)
