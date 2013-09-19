from distutils.core import setup

setup(
    name='RPi-MCP23017',
    version='0.1.0',
    author='Christian Fischer',
    author_email='pypi@computerlyrik.de',
    packages=['MCP23017'],
    scripts=[],
    url='https://github.com/computerlyrik/MCP23017-RPi-python',
    license='LICENSE',
    description='Interfacing MCP23017 with Raspberry Pi',
    long_description=open('README.md').read(),
    install_requires=[
        "RPi.GPIO >= 0.5.3a",
    ],
)
