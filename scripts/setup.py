from setuptools import setup
from pybind11.setup_helpers import Pybind11Extension, build_ext
from pybind11 import get_cmake_dir
import pybind11

setup(
    name="vpype-cfill",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="A vpype extension for generating concentric fill patterns",
    long_description="",
    packages=["vpype_cfill"],
    python_requires=">=3.7",
    install_requires=[
        "vpype>=1.9",
        "click",
        "numpy",
    ],
    entry_points={
        "vpype.plugins": [
            "cfill = vpype_cfill.vpype_cfill:cfill",
        ]
    },
)