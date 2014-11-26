#!/usr/bin/python

import rrdtool
import os

#-----------------------------------------------------------------------------

def list_files(path):
    path = path.rstrip('/') + '/'
    rrds = []
    def walk(arg, dirname, fnames):
        d = dirname.replace(path, '')
        rrds.extend([os.path.join(d, f) for f in fnames if f.endswith('.rrd')])
    os.path.walk(path, walk, None)
    return rrds

#-----------------------------------------------------------------------------

def list_variables(filename):
    info = rrdtool.info(str(filename))
    datasources = [
        ds[3:-7]
        for ds in info.keys()
        if ds.startswith("ds[") and ds.endswith("].index")
    ]
    datasources.sort(key = lambda(ds): info["ds[%s].index" % (ds)])
    return datasources

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
