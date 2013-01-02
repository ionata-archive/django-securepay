#!/usr/bin/env python

try:
    from setuptools import setup, find_packages
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages

setup(
    name='django-securepay',
    version="1.0.3",
    description='Interface with the SecurePay API from Django',
    author='Ionata Web Solutions',
    author_email='webmaster@ionata.com.au',
    url='https://bitbucket.org/ionata/django-securepay',
    packages=find_packages(),
    install_requires=[
        'Django>=1.4.1',
        'requests>=0.13.0',
        'django-admin-extensions>=0.1.1',
        'django-picklefield==0.2.1',
    ],
    package_data={},
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Framework :: Django',
    ],
)
