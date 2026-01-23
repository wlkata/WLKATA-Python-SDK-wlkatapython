from setuptools import setup, find_packages


setup(
    name='wlkatapython', # 自定义包名 #Custom package name
    version='0.1.0', # 包的版本号 #Package version number
    description='WLKATA-Mirobot/E4/MT4/MS4220 Multiple robotic arm control!', # 描述信息 #Description information
    long_description=open('README.md').read(),  # 长描述，通常是README #Long description, usually README
    long_description_content_type='text/markdown',  # 长描述的格式 #Long description format
    author='DS', # 作者 #Author
    packages=find_packages(include=['*', 'tests*']),  # 自动找到项目中的所有包 #Automatically find all packages in the project
    py_modules=[
        'wlkatapython'
    ] ,# 包中包含的模块 #Modules included in the package
    install_requires=[
        'pyserial'
    ],
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ]
)