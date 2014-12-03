#!/usr/bin/python
#
# Default settings for plotarrd webapplication.
#
#-----------------------------------------------------------------------------

import os

#-----------------------------------------------------------------------------

APP_ROOT = os.path.dirname(os.path.dirname(__file__))

RRD_PATH = '/var/lib/collectd/rrd'
SAVED_GRAPHS = 'graphs'

SECRET_KEY_FILE = 'secret.txt'

DEBUG = True

#-----------------------------------------------------------------------------

SECRET_KEY_FILE_ABS = os.path.join(APP_ROOT, SECRET_KEY_FILE)
SECRET_KEY = open(SECRET_KEY_FILE_ABS).readline().strip()

SAVED_GRAPHS_ABS = os.path.join(APP_ROOT, SAVED_GRAPHS)

#-----------------------------------------------------------------------------
# vim:ft=python
