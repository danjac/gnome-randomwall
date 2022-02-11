#!/usr/bin/env python
from setuptools import find_packages, setup

VERSION = "0.0.1"

setup(
    name="gnome-randomwall",
    version=VERSION,
    author="Dan Jacob",
    author_email="danjac2018@gmail.com",
    entry_points={
        "console_scripts": ["randomwall=randomwall.randomwall:main"]
    },
    # url="https://github.com/randomwall",
    description="Random wallpaper selector for GNOME desktop",
    license="MIT",
    python_requires=">=3.9",
    packages=find_packages("src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.9",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
