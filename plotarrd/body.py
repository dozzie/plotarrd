#!/usr/bin/python

import flask
import plotarrd.settings
import os
import rrd

import base64
import json

#-----------------------------------------------------------------------------

app = flask.Flask(__name__)
app.config.from_object(plotarrd.settings)

#-----------------------------------------------------------------------------

def encode(data):
    return base64.b64encode(json.dumps(data))

def decode(data):
    try:
        return json.loads(base64.b64decode(data))
    except:
        flask.abort(400)

#-----------------------------------------------------------------------------

@app.route("/")
def index():
    rrds = rrd.list_files(app.config['RRD_PATH'])
    return flask.render_template('index.html', rrds = rrds)

#-----------------------------------------------------------------------------

@app.route("/plot", methods = ["GET", "POST"])
def plot():
    if flask.request.method == "POST" and 'graph' in flask.session:
        # 'delete' in flask.request.values
        entry = int(flask.request.values['delete'])
        if entry < len(flask.session['graph']):
            new_list = list(flask.session['graph'])
            del new_list[entry]
            flask.session['graph'] = new_list
        return flask.redirect(flask.url_for('plot'))

    if 'graph' not in flask.session or len(flask.session['graph']) == 0:
        vals = []
        url = ""
    else:
        vals = flask.session['graph']
        params = {
            'values': vals,
        }
        url = flask.url_for('render', params = encode(params))

    return flask.render_template('plot.html', image_url = url, values = vals)

@app.route("/render/<params>")
def render(params):
    params = decode(params)
    # TODO: sanity checks on params
    img = rrd.plot(values = params['values'], rrd_root = app.config['RRD_PATH'])
    return flask.Response(response = img, content_type = 'image/png')

#-----------------------------------------------------------------------------

@app.route("/edit/save", methods = ["POST"])
def plot_save():
    # TODO:
    #   * sanitize the submitted form
    #   * save the submitted form (flask.request.values.getlist() for "rrd"
    #     and "ds")

    if 'discard' in flask.request.values:
        del flask.session['graph']
        return flask.redirect(flask.url_for('plot'))

    # 'save' in flask.request.values
    pass # TODO

#-----------------------------------------------------------------------------

@app.route("/edit/browse")
def browse_files():
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

    return flask.render_template('browse_files.html',
                                 path = dirname,
                                 files = sorted(files),
                                 subdirs = sorted(subdirs))

#-----------------------------------------------------------------------------

@app.route("/edit/datasources", methods = ["POST", "GET"])
def browse_datasources():
    if 'file' not in flask.request.values:
        return flask.redirect(flask.url_for('browse_files'))

    # TODO: sanity check (leading slash, "..")
    filename = flask.request.values['file'].strip('/')

    if flask.request.method == 'POST':
        new_vars = [
            {"rrd": filename, "ds": ds}
            for ds in flask.request.values.getlist('datasource')
        ]
        if 'graph' not in flask.session:
            flask.session['graph'] = new_vars
        else:
            flask.session['graph'] += new_vars
        return flask.redirect(flask.url_for('plot'))

    filename_abs = os.path.join(app.config['RRD_PATH'], filename)
    datasources = rrd.list_variables(filename_abs)

    return flask.render_template('browse_datasources.html',
                                 file = filename, datasources = datasources)

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
