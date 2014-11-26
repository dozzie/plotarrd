#!/usr/bin/python

import flask
import plotarrd.settings
import os

#-----------------------------------------------------------------------------

app = flask.Flask(__name__)
app.config.from_object(plotarrd.settings)

#-----------------------------------------------------------------------------

@app.route("/")
def index():
    url = flask.url_for('images', image = 'foo')
    return flask.render_template('index.html', url = url)

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
