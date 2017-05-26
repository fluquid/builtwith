import os
from distutils.core import setup

def read(filename):
    return open(os.path.join(os.path.dirname(__file__), filename)).read()

setup(
    name='builtwith',
    version='1.4',
    packages=['builtwith'],
    author='Johannes Ahlmann, original: Richard Penman',
    author_email='johannes@fluquid.com',
    description='Detect the technology used by a website, such as Apache, JQuery, and Wordpress.',
    install_requires=[
        'six',
        'regex'
    ],
    package_data = {
        'builtwith': ['data/*'],
    },

    long_description=read('Readme.md'),
    url='https://github.com/fluquid/builtwith',
    license='lgpl'
)
