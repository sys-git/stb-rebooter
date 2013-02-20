#!/usr/bin/env python
# -*- coding: utf-8 -*-

try:
    from setuptools import setup, find_packages
except ImportError:
    import ez_setup
    ez_setup.use_setuptools()
    from setuptools import setup, find_packages
    
setup(
    name="stbrebooter",
    version="0.1",
    url='https://github.com/sys-git/stb-rebooter',
    packages=find_packages(),
    package_dir={'stb-rebooter': 'Rebooter'},
    include_package_data=True,
    author="Francis Horsman",
    author_email="francis.horsman@gmail.com",
    description="Twisted SSH generic stb and pdu rebooter.",
    license="GNU General Public License",
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Communications',
    ]
)
