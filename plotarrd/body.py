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

@app.route("/browse/add_file")
def browse_add_file():
    if 'dir' in flask.request.values:
        # TODO: sanity check (leading slash, "..")
        dirname = flask.request.values['dir'].strip('/')
        dirname_abs = os.path.join(app.config['RRD_PATH'], dirname)
    else:
        dirname = ''
        dirname_abs = app.config['RRD_PATH']

    files = []
    subdirs = []
    for e in os.listdir(dirname_abs):
        if e == '.' or e == '..':
            continue

        ee = os.path.join(dirname_abs, e)
        if os.path.isdir(ee):
            subdirs.append(e)
        elif e.endswith('.rrd') and os.path.isfile(ee):
            files.append(e)

    return flask.render_template('browse_add_file.html',
                                 path = dirname,
                                 files = sorted(files),
                                 subdirs = sorted(subdirs))

@app.route("/browse/add_datasource", methods = ["POST", "GET"])
def browse_add_datasource():
    if 'file' not in flask.request.values:
        return flask.redirect(flask.url_for('browse_add_file'))

    # TODO: sanity check (leading slash, "..")
    filename = flask.request.values['file'].strip('/')

    if flask.request.method == 'POST':
        datasources = flask.request.values.getlist('datasource')
        # TODO: save in some session variable and redirect
        return flask.render_template('browse_list.html',
                                     file = filename,
                                     datasources = datasources)

    filename_abs = os.path.join(app.config['RRD_PATH'], filename)
    datasources = rrd.list_variables(filename_abs)

    return flask.render_template('browse_add_datasource.html',
                                 file = filename, datasources = datasources)

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
