from setuptools import find_packages, setup

setup(
    name="py_serial_app_for_witmotion",
    version="1.0.0",
    description="Serial communication application with GUI",
    author="Koki Lee",
    author_email="riko2501@gmail.com",
    packages=find_packages(),
    install_requires=[
        "pyserial",
        "matplotlib",
        "numpy",
        "PyQt5",
        "qasync",
        "pytest-asyncio",
        "pytest",
    ],
    python_requires=">=3.9.2",
)
