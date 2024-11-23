from distutils.core import setup

with open("requirements.txt") as f:
    requirements = f.read().splitlines()


setup(
    name='semantiq_browse',
    version='0.0.1',
    packages=["sq_browse"],
    url='',
    license='',
    author='Jakob Rößler',
    author_email='',
    description='',
    install_requires=requirements,
    entry_points={
        'console_scripts': [
            "sq_browse = sq_browse.cmd:main",
        ]
    }
)
