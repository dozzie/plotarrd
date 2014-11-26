#!/usr/bin/python

import flask
import plotarrd.settings
import os
import rrd

#-----------------------------------------------------------------------------

app = flask.Flask(__name__)
app.config.from_object(plotarrd.settings)

#-----------------------------------------------------------------------------

@app.route("/")
def index():
    rrds = rrd.list_files(app.config['RRD_PATH'])
    return flask.render_template('index.html', rrds = rrds)

@app.route("/plot/<path:db>")
def plot(db):
    db_abs = os.path.join(app.config['RRD_PATH'], db)
    # TODO: error handling
    variables = rrd.list_variables(db_abs)
    return flask.render_template('plot.html', rrd = db, variables = variables)

#-----------------------------------------------------------------------------

@app.route("/images/<image>.png")
def images(image):
    # TODO: sanity check on `image'
    img_path = os.path.join(app.config['IMAGE_STORAGE_ABS'], image + '.png')
    try:
        img = open(img_path).read()
        return flask.Response(response = img, content_type = 'image/png')
    except IOError:
        return flask.Response(status = 404)

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
