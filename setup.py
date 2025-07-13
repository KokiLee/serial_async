from setuptools import find_packages, setup

setup(
    name="py_serial_app_for_witmotion",
    version="1.0.0",
    description="Serial communication application with GUI",
    author="Koki Lee",
    author_email="riko2501@gmail.com",
    packages=find_packages(),
    install_requires=[
        "matplotlib==3.8.2",
        "numpy==2.3.1",
        "PyQt5==5.15.11",
        "PyQt5_sip==12.13.0",
        "pyserial==3.5",
        "pyserial_asyncio==0.6",
        "pytest==7.4.4",
        "qasync==0.27.1",
        "setuptools==49.2.1",
    ],
    python_requires=">=3.9.2",
)
