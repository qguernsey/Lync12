import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="lyncconnector",
    version="0.0.1",
    author="Quentin Guernsey",
    author_email="quentin.guernsey@gmail",
    description="A package for controlling a HTD Lync controller",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/qguernsey/Lync12",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)

