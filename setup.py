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
        'aiohttp',
        'pycapnp',
        'panel',
        'holoviews',
        'datashader',
        'plotly',
        'numpy',
        'jupyterlab',
        'jupyter-server-proxy',
    ],
    package_data={
        'pyttoresque': [
            'api/Simulator.capnp',
            'app/static/*',
            'app/templates/*',
        ],
    },
    include_package_data=True,
    data_files=[
        (
            "etc/jupyter/jupyter_server_config.d",
            ["jupyter-config/jupyter_server_config.d/pyttoresque.json"]
        ),
        (
            "etc/jupyter/jupyter_notebook_config.d",
            ["jupyter-config/jupyter_notebook_config.d/pyttoresque.json"]
        ),
    ],
    entry_points={
        'console_scripts': [
            'jupyter-mosaic = pyttoresque.app:main'
        ],
        'jupyter_serverproxy_servers': [
            # name = packagename:function_name
            # 'pouchdb = pyttoresque.app:setup_pouchdb',
            'panel = pyttoresque.app:setup_panel',
        ]
    },
    python_requires='>=3.6',
    use_scm_version=True,
    setup_requires=['setuptools_scm'],
)
