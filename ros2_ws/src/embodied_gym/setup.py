from setuptools import find_packages, setup

package_name = 'embodied_gym'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools', 'numpy', 'gymnasium', 'stable-baselines3', 'pyyaml'],
    zip_safe=True,
    maintainer='changwei',
    maintainer_email='changwei@example.com',
    description='Gymnasium environments for embodied RL training',
    license='Apache-2.0',
)
