#!/usr/bin/env python3
# coding=utf-8

from setuptools import setup, find_packages

def requirements_file_to_list(fn='requirements.txt'):
    with open(fn, 'r') as f:
        return [x.rstrip() for x in list(f) if x and not x.startswith('#')]


setup(
    name='TorrentSearcher',
    version='1.0.0',
    install_requires=requirements_file_to_list(),
    py_modules=['TorrentSearch', 'MagnetParser'],
    entry_points={'console_scripts': ['torrent_searcher = TorrentSearch:main',]},
    author='Carlos Miguel Ferreira',
    author_email='carlosmf.pt@gmail.com',
    maintainer='Carlos Miguel Ferreira',
    maintainer_email='carlosmf.pt@gmail.com',
    description='Torrent search engine supporting several torrent tracking platforms.',
    long_description=open('README.md').read(),
    keywords='Torrents, Search',
    license='GPLv3',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ]
)
