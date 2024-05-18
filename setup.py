import os
from setuptools import setup, find_packages


def read():
    return open(os.path.join(os.path.dirname(__file__), "README.md")).read()


setup(
    name="kubernetes-python-client",
    version="0.0.1",
    keywords=["Kubernetes", "Python Client", "Kserve"],
    packages=find_packages("."),
    long_description=read(),
    install_requires=[
        "kubernetes==29.0.0",
        "kserve==0.12.1",
    ]
)
