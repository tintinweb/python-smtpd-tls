#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
from setuptools import setup

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name="smtpd-tls",
    version="0.1",
    author="tintinweb",
    author_email="tintinweb@oststrom.com",
    description=("An extension to the standard python 2.x smtpd library implementing implicit/explicit SSL/TLS/STARTTLS"),
    license="",
    keywords=["smtpd", "starttls", "tls", "ssl"],
    url="https://github.com/tintinweb/python-smtpd-tls",
    download_url="https://github.com/tintinweb/python-smtpd-tls/tarball/v0.1",
    long_description=read("README.rst") if os.path.isfile("README.rst") else read("README.md"),
    install_requires=[],
    py_modules=['smtpd_tls'],
)
