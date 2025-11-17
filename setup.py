from setuptools import setup, find_packages

setup(
    name="fxmacrodata",  # pip install fxmacrodata
    version="0.1.0",
    description="Python SDK for FXMacroData API (forex macroeconomic data)",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="FXMacroData",
    author_email="info@fxmacrodata.com",
    url="https://github.com/fxmacrodata/fxmacrodata",
    packages=find_packages(),
    install_requires=[
        "requests>=2.28.0",
        "aiohttp>=3.8.0",
    ],
    python_requires=">=3.9",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
