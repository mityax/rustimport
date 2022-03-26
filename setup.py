from setuptools import setup

version = open("VERSION").read()

description = open("README.md").read()

setup(
    packages=["rustimport"],
    install_requires=["mako", "pybind11"],
    zip_safe=False,
    name="rustimport",
    version=version,
    description="Import C++ files directly from Python!",
    long_description=description,
    long_description_content_type="text/markdown",
    url="https://github.com/tbenthompson/rustimport",
    author="T. Ben Thompson",
    author_email="t.ben.thompson@gmail.com",
    license="MIT",
    platforms=["any"],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Operating System :: POSIX",
        "Topic :: Software Development",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: C++",
    ],
)
