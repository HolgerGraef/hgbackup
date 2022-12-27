import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="HGBackup",
    version="0.1.0",
    author="Holger Graef",
    author_email="holger.graef@gmail.com",
    description="rsync-based backup tool",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/HolgerGraef/hgbackup",
    packages=setuptools.find_packages(),
    package_data={"": ["pie/*.png"]},
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    entry_points={"console_scripts": ["hgbackup = hgbackup.hgbackup:main"]},
)
