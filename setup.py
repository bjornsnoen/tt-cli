from setuptools import find_packages, setup

setup(
    name="tt-cli",
    version="1.0.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "beautifulsoup4==4.9.3",
        "certifi==2020.12.5",
        "chardet==4.0.0; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3, 3.4'",
        "click==7.1.2",
        "click-help-colors==0.9",
        "html5lib==1.1",
        "idna==2.10; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3'",
        "python-dotenv==0.15.0",
        "requests==2.25.1",
        "six==1.15.0; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3'",
        "soupsieve==2.1; python_version >= '3.0'",
        "urllib3==1.26.3; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3, 3.4' and python_version < '4'",
        "webencodings==0.5.1",
    ],
    entry_points="""
        [console_scripts]
        tt-cli=ttcli.main:cli
        tt-a=ttcli.main:write_to_all
    """,
)
