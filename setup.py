

import io
import ast
import re
from os import path
from setuptools import setup, find_packages

base_dir = path.abspath(path.dirname(__file__))

with io.open(path.join(base_dir, "README.md")) as f:
    long_description = f.read()


with io.open(path.join(base_dir, "djingles/_version.py")) as f:
    ctx = {}
    exec(f.read(), None, ctx)
    version = ctx['__version__']


setup(
    name="djingles",
    description="Set of django utilities",
    long_description=long_description,
    version=version,
    url="https://github.com/vivsh/djingles",
    license="BSD",
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Text Processing :: Markup :: HTML'
    ],
    keywords="django utilities",
    install_requires=[
        "python-dateutil",
        "jinja2>=2.8",
        "django>=2",
        "click",
        "djangorestframework",
        "cookiecutter",
    ],
    python_requires='>=3',
    include_package_data=True,
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "djingles = djingles.commands.main:cli"
        ]
    }
)
