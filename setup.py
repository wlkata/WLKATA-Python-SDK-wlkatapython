from setuptools import setup

setup(
    name='wlkatapython', 
    version='0.0.9', 
    description='WLKATA-Mirobot/E4 Multiple robotic arm control!', 
    long_description='Suitable for controlling single or multiple Mirobot robotic arms, E4 robotic arms, slides, and conveyor belts. Note that a multifunctional controller must be used to use this SDK.',
    author='DS', 
    py_modules=[
        'wlkatapython'
    ] ,
    install_requires=[
        'pyserial'
    ]
)
