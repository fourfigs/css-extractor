from setuptools import setup, find_packages

setup(
    name="java-css-optimizer",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        'csscompressor',
        'psutil',
        'aiofiles',
        'orjson',
        'typing-extensions'
    ],
    python_requires='>=3.7',
    author="Kenneth Hanks",
    author_email="fourfigs@gmail.com",
    description="A tool for optimizing Java Swing applications by converting style methods to CSS",
    long_description=open('README.md').read(),
    long_description_content_type="text/markdown",
    url="https://github.com/fourfigs/java-css-optimizer",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
) 