from __future__ import with_statement
from setuptools import setup, find_packages

import webarchiver


setup(
    name='webarchiver',

    version=webarchiver.__version__,

    url='https://github.com/chwnam/webarchiver.git',

    author='changwoo',

    author_email='ep6tri@hotmail.com',

    description='A small tool for archiving web resources',

    long_description='',

    license='MIT',

    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        'Topic :: Internet :: WWW/HTTP',
    ],

    keywords='archiving crawling html scraping web',

    packages=find_packages(exclude=()),

    install_requires=[
        'requests',
        'selenium',
        'six',
    ],

    package_data={},

    data_files=[],

    entry_points={},
)
