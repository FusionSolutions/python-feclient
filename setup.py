#!/usr/bin/env python3
import os, shutil
import feClient
try:
	from setuptools import setup
except ImportError:
	from distutils.core import setup

pwd = os.path.abspath(os.path.dirname(__file__))

setup(
	name = "python-feclient",
	version = feClient.__version__,
	description = "Client for Fusion Explorer API",
	keywords = "explorer client fusion solutions fusionsolutions fusionexplorer",
	author = "Andor `iFA88` Rajci - Fusions Solutions KFT",
	author_email = "ifa@fusionsolutions.io",
	url = "https://github.com/FusionSolutions/python-feclient",
	license = "GPL-3",
	# setup_requires=["setuptools>=25"],
	# install_requires=["setuptools>=25"],
	package_dir={"feClient": "feClient"},
	packages=["feClient"],
	long_description=open(os.path.join(pwd, "README.md")).read(),
	long_description_content_type="text/markdown",
	zip_safe=False,
	scripts=["feClient/fexplorer-cli"],
	python_requires=">=3.8.*",
	classifiers=[ # https://pypi.org/pypi?%3Aaction=list_classifiers
		"Development Status :: 4 - Beta",
		"Topic :: Utilities",
		"Programming Language :: Python :: 3 :: Only",
		"Programming Language :: Python :: 3.8",
		"Programming Language :: Python :: 3.9",
		"License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)",
	],
)