#!/usr/bin/python
#
# Default settings for plotarrd webapplication.
#
#-----------------------------------------------------------------------------

import os

#-----------------------------------------------------------------------------

APP_ROOT = os.path.dirname(os.path.dirname(__name__))

IMAGE_STORAGE = 'images'

RRD_PATH = '/var/lib/collectd/rrd'

SECRET_KEY_FILE = 'secret.txt'

#-----------------------------------------------------------------------------

IMAGE_STORAGE_ABS = os.path.join(APP_ROOT, IMAGE_STORAGE)

SECRET_KEY_FILE_ABS = os.path.join(APP_ROOT, SECRET_KEY_FILE)
SECRET_KEY = open(SECRET_KEY_FILE_ABS).readline().strip()

#-----------------------------------------------------------------------------
# vim:ft=python
