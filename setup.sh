#!/usr/bin/env python

#############################################################################

VERSION = '1.0'

#############################################################################

try:
	from setuptools import setup

except ImportError:
	from distutils.core import setup

#############################################################################

setup(
	name = 'jsonv',
	version = VERSION,
	author = 'Jerome Odier',
	author_email = 'jerome.odier@lpsc.in2p3.fr',
	description = 'Json validator with EBNF grammar',
	url = 'http://www.odier.eu/jsonv/',
	license = 'CeCILL-C',
	packages = ['jsonv'],
	package_data = {'jsonv': ['*.txt']}
)

#############################################################################
