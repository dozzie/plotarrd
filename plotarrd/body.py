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
    filename_abs = os.path.join(app.config['RRD_PATH'], filename)

    if 'finish' in flask.request.values and \
       'datasource' in flask.request.values:
        datasources = flask.request.values.getlist('datasource')
        if 'datasources' in flask.session:
            del flask.session['datasources']
        # TODO: save in some other session variable and redirect
        return flask.render_template('browse_list.html',
                                     file = filename,
                                     datasources = datasources)

    if 'datasources' not in flask.session:
        flask.session['datasources'] = []

    if 'ds' in flask.request.values:
        ds = flask.request.values['ds']
        if ds not in flask.session['datasources']:
            flask.session['datasources'].append(ds)

    if 'remove_ds' in flask.request.values:
        ds = flask.request.values['remove_ds']
        if ds in flask.session['datasources']:
            flask.session['datasources'].remove(ds)

    # force a copy, as Flask might not notice the change
    flask.session['datasources'] = list(flask.session['datasources'])

    datasources = rrd.list_variables(filename_abs)

    return flask.render_template('browse_add_datasource.html',
                                 file = filename, datasources = datasources,
                                 added = flask.session['datasources'])

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
