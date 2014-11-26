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

#-----------------------------------------------------------------------------

IMAGE_STORAGE_ABS = os.path.join(APP_ROOT, IMAGE_STORAGE)

#-----------------------------------------------------------------------------
# vim:ft=python