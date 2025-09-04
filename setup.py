import pathlib
from setuptools import setup, find_packages
from distutils.spawn import find_executable
import platform


def readme():
    with open('README.md') as f:
        return f.read()


dependencies = ['pyperclip', 'click', 'appdirs', 'daemonize', 'lxml', 'numpy']
if find_executable("fswatch") is None:
    if platform.system() == "Linux":
        dependencies.append("inotify")
    else:
        raise ValueError(
                "inkscape-figures-typst needs fswatch to run on MacOS. You "
                "can install it using `brew install fswatch`"
                )

setup(
    name="inkscape-figures-typst",
    version="1.0.7",
    description="Script for managing inkscape figures with typst",
    long_description=readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/DobbiKov/inkscape-figures-typst",
    author="Yehor Korotenko",
    author_email="yehor.korotenko@outlook.com",
    license="MIT",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
    ],
    packages=['inkscapefigures', 'inkscape_svg_to_typst'],
    scripts=['bin/inkscape-figures-typst'],
    install_requires=dependencies,
    include_package_data=True
)
