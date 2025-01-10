from setuptools import setup

setup(
    name='watchdog-server',
    version='1.0',
    long_description=__doc__,
    packages=['app'],
    include_package_data=True,
    zip_safe=False,
    install_requires=['flask', 'sqlalchemy', 'redis']
)