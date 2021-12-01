import setuptools

with open("readme.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="Pyttoresque",
    author="Pepijn de Vos",
    author_email="pepijndevos@gmail.com",
    description="Library for working with NyanCAD tools",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/NyanCAD/pyttoresque",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=[
        'ibmcloudant',
        'pycapnp',
        'bokeh',
        'numpy'
    ],
    package_data={
        'pyttoresque': ['simserver/Simulator.capnp'],
    },
    python_requires='>=3.6',
    use_scm_version=True,
    setup_requires=['setuptools_scm'],
)
