from setuptools import setup

setup(
    name='snoggle',
    version='0.0.1',
    packates=['snoggle'],
    install_requires=[
        'Flask==0.10.1',
        'Flask-SocketIO==2.8.1',
    ],
    author='Andreas Jansson',
    author_email='andreas@jansson.me.uk',
    description=('boggleship'),
    license='OMEGPL',
    url='https://github.com/andreasjansson/snoggle',
)
