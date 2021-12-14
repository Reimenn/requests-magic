from setuptools import setup
import os

setup(
    name='requests_magic',
    version='v1.6-beta',
    author='Rika',
    author_email='2293840045@qq.com',
    packages=['requests_magic'],
    package_dir={'requests_magic': 'requests_magic'},
    include_package_data=True,
    data_files=[
        os.path.join('./requests_magic/web_view/', i)
        for i in os.listdir('./requests_magic/web_view/')
    ],
    install_requires=['requests']
)
