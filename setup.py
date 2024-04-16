from setuptools import setup

setup(
    name='wlkatapython', # 自定义包名
    version='0.0.8', # 包的版本号
    description='WLKATA-Mirobot/E4 Multiple robotic arm control!', # 描述信息
    long_description='Suitable for controlling single or multiple Mirobot robotic arms, E4 robotic arms, slides, and conveyor belts. Note that a multifunctional controller must be used to use this SDK.',
    author='DS', # 作者
    py_modules=[
        'wlkatapython'
    ] ,# 包中包含的模块
    install_requires=[
        'pyserial'
    ]
)