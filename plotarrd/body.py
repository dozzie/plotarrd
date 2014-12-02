#!/usr/bin/python

import flask
import plotarrd.settings
import os
import rrd
import re

import base64
import json

#-----------------------------------------------------------------------------

app = flask.Flask(__name__)
app.config.from_object(plotarrd.settings)

_PARAM_RE = re.compile(r'\$\{([a-zA-Z0-9_.-]+)\}')

#-----------------------------------------------------------------------------

@app.route("/")
def index():
    saved_graphs = [
        g[:-5]
        for g in os.listdir(app.config['SAVED_GRAPHS_ABS'])
        if g.endswith('.json')
    ]
    saved_graphs.sort()
    return flask.render_template('index.html', graphs = saved_graphs)

#-----------------------------------------------------------------------------
#
# session:
#   * 'graph' :: [ {'name': str(), 'rrd': str(), 'ds': str()} ]
#   * 'params' :: { Name: ExampleValue }
#   * 'plot_params' :: {
#       'title':? str(),
#       'ylabel':? str(),
#       'ymin':? number(),
#       'ymax':? number(),
#       'timespan':? int(),
#       'timespan_unit': "h" | "d" | "w" | "m"
#     }
#
#-----------------------------------------------------------------------------

@app.route("/plot", methods = ["GET"])
def plot():
    if 'graph' not in flask.session or len(flask.session['graph']) == 0:
        vals = []
        plot_params = {}
        params = flask.session.get('params', {})
        url = ""
    else:
        vals = flask.session['graph']
        plot_params = flask.session.get('plot_params', {})
        params = flask.session.get('params', {})
        url_params = {
            'graph': vals,
            'params': params,
            'plot_params': plot_params,
        }
        url = flask.url_for('render', params = encode(url_params))

    return flask.render_template('plot.html',
                                 image_url = url,
                                 values = vals,
                                 plot_params = plot_params,
                                 params = params)

@app.route("/plot", methods = ["POST"])
def plot_rename_or_delete():
    if 'rename' in flask.request.values:
        entry = int(flask.request.values['rename'])
        if entry < len(flask.session['graph']):
            new_list = list(flask.session['graph'])
            # TODO: sanitize name
            new_list[entry]['name'] = flask.request.values['name']
            flask.session['graph'] = new_list
    elif 'delete' in flask.request.values:
        entry = int(flask.request.values['delete'])
        if entry < len(flask.session['graph']):
            new_list = list(flask.session['graph'])
            del new_list[entry]
            flask.session['graph'] = new_list
    # so hitting "refresh" don't complain about resubmitting data
    return flask.redirect(flask.url_for('plot'))

#-----------------------------------------------------------------------------

@app.route("/plot/labels", methods = ["POST"])
def plot_set_labels():
    # form fields:
    #   * title, ylabel, ymin, ymax
    #   * timespan + timespan_unit
    #   * update=update
    new_vars = dict(flask.session.get('plot_params', {}))

    if flask.request.values.get('title', '') != '':
        new_vars['title'] = flask.request.values['title']
    elif 'title' in new_vars:
        del new_vars['title']
    if flask.request.values.get('ylabel', '') != '':
        new_vars['ylabel'] = flask.request.values['ylabel']
    elif 'ylabel' in new_vars:
        del new_vars['ylabel']

    def number(s):
        if '.' in s or 'e' in s or 'E' in s:
            return float(s)
        else:
            return int(s)
    if flask.request.values.get('ymin', '') != '':
        new_vars['ymin'] = number(flask.request.values['ymin'])
    elif 'ymin' in new_vars:
        del new_vars['ymin']
    if flask.request.values.get('ymax', '') != '':
        new_vars['ymax'] = number(flask.request.values['ymax'])
    elif 'ymax' in new_vars:
        del new_vars['ymax']

    if flask.request.values.get('timespan_unit', '') in ['h', 'd', 'w', 'm']:
        new_vars['timespan_unit'] = flask.request.values['timespan_unit']
    if flask.request.values.get('timespan', '') != '':
        new_vars['timespan'] = int(flask.request.values['timespan'])
    else:
        if 'timespan' in new_vars:
            del new_vars['timespan']
        if 'timespan_unit' in new_vars:
            del new_vars['timespan_unit']

    flask.session['plot_params'] = new_vars
    return flask.redirect(flask.url_for('plot'))

@app.route("/plot/variables", methods = ["POST"])
def plot_set_variables():
    # form fields:
    #   * name, rrd, ds -- getlist()
    #   * delete (int)
    #   * newvarname, newvarexpr, newvards, update=add
    #   * update=update

    if 'delete' in flask.request.values:
        new_vars = list(flask.session.get('graph', []))
        entry = int(flask.request.values['delete'])
        if entry < len(new_vars):
            del new_vars[entry]
    elif flask.request.values['update'] == 'add':
        new_vars = list(flask.session.get('graph', []))
        # TODO: expressions
        new_vars.append({
            'name': flask.request.values['newvarname'],
            'rrd':  flask.request.values['newvarexpr'],
            'ds':   flask.request.values['newvards'],
        })
    else:
        names = flask.request.values.getlist('name')
        rrds = flask.request.values.getlist('rrd')
        dses = flask.request.values.getlist('ds')
        new_vars = [
            {"rrd": rrds[i], "ds": dses[i], "name": names[i]}
            for i in range(len(rrds))
        ]

    flask.session['graph'] = new_vars

    return flask.redirect(flask.url_for('plot'))

@app.route("/plot/params", methods = ["POST"])
def plot_set_params():
    # form fields:
    #   * param, value -- getlist()
    #   * delete (str)
    #   * newparamname, newparamdefault, update=add
    #   * update=update

    if 'delete' in flask.request.values:
        new_vars = dict(flask.session.get('params', {}))
        entry = flask.request.values['delete']
        if entry in new_vars:
            del new_vars[entry]
    elif flask.request.values['update'] == 'add':
        new_vars = dict(flask.session.get('params', {}))
        new_vars[flask.request.values['newparamname']] = \
            flask.request.values['newparamdefault']
    else:
        names = flask.request.values.getlist('param')
        values = flask.request.values.getlist('value')
        new_vars = dict(zip(names, values))

    flask.session['params'] = new_vars

    return flask.redirect(flask.url_for('plot'))

#-----------------------------------------------------------------------------

@app.route("/render/<params>")
def render(params):
    params = decode(params)
    # TODO: sanity checks on params
    values, graph_params = combine_params(params['graph'],
                                          params.get('plot_params', {}),
                                          params.get('params', {}))
    if 'timespan' in graph_params and 'timespan_unit' in graph_params:
        timespan = "%d%s" % (graph_params['timespan'],
                             graph_params['timespan_unit'])
    else:
        timespan = None
    img = rrd.plot(values = values,
                   rrd_root = app.config['RRD_PATH'],
                   title = graph_params.get('title'),
                   ylabel = graph_params.get('ylabel'),
                   ymin = graph_params.get('ymin'),
                   ymax = graph_params.get('ymax'),
                   timespan = timespan)
    return flask.Response(response = img, content_type = 'image/png')

@app.route("/graph/<name>", methods = ["GET"])
def graph(name):
    try:
        # TODO: sanity checks on name
        params_path = os.path.join(app.config['SAVED_GRAPHS_ABS'],
                                   name + '.json')
        params = json.load(open(params_path))
        url = flask.url_for('render_saved', name = name)
        return flask.render_template('plot.html',
                                     graph_name = name,
                                     image_url = url,
                                     values = params['graph'],
                                     plot_params = params['plot_params'],
                                     params = params['params'])
    except IOError:
        flask.abort(404)

@app.route("/graph/<name>", methods = ["POST"])
def graph_rename_or_delete(name):
    # either "rename" or "delete" button for a variable

    # TODO: sanity checks on name
    params_path = os.path.join(app.config['SAVED_GRAPHS_ABS'], name + '.json')
    try:
        params = json.load(open(params_path))
    except IOError:
        flask.abort(404)

    # load the session
    flask.session['graph'] = params['graph']

    # do the POST thing
    if 'rename' in flask.request.values:
        entry = int(flask.request.values['rename'])
        if entry < len(flask.session['graph']):
            # TODO: sanitize name
            flask.session['graph'][entry]['name'] = flask.request.values['name']
    elif 'delete' in flask.request.values:
        entry = int(flask.request.values['delete'])
        if entry < len(flask.session['graph']):
            del flask.session['graph'][entry]

    return flask.redirect(flask.url_for('plot'))

# ?size={Width}x{Height}&timespan={Time}
# {Time} can be "15min", "8h", "1d", "4w", "1month", "1y" and so on
@app.route("/graph/<name>.png")
def render_saved(name):
    if 'size' in flask.request.args:
        width, height = flask.request.args['size'].split('x')
        width = int(width)
        height = int(height)
    else:
        width = None
        height = None
    timespan = flask.request.args.get('timespan')

    try:
        # TODO: sanity checks on name
        params_path = os.path.join(app.config['SAVED_GRAPHS_ABS'],
                                   name + '.json')
        params = json.load(open(params_path))
        params_updated = params.get('params', {})
        params_updated.update(flask.request.args.items())
        values, graph_params = combine_params(params['graph'],
                                              params.get('plot_params', {}),
                                              params_updated)
        if timespan is None and \
           'timespan' in graph_params and 'timespan_unit' in graph_params:
            timespan = "%d%s" % (graph_params['timespan'],
                                 graph_params['timespan_unit'])

        img = rrd.plot(values = values,
                       rrd_root = app.config['RRD_PATH'],
                       title = graph_params.get('title'),
                       ylabel = graph_params.get('ylabel'),
                       ymin = graph_params.get('ymin'),
                       ymax = graph_params.get('ymax'),
                       width = width, height = height,
                       timespan = timespan)
        return flask.Response(response = img, content_type = 'image/png')
    except IOError:
        flask.abort(404)
    except KeyError:
        flask.abort(500)

#-----------------------------------------------------------------------------

@app.route("/edit/new")
def start_anew():
    for s in ['graph', 'params', 'plot_params']:
        if s in flask.session:
            del flask.session[s]
    return flask.redirect(flask.url_for('plot'))

#-----------------------------------------------------------------------------

@app.route("/edit/save", methods = ["POST"])
def plot_save():
    # TODO:
    #   * sanitize the submitted form
    #   * save the submitted form (flask.request.values.getlist() for "rrd"
    #     and "ds")

    if 'discard' in flask.request.values:
        for s in ['graph', 'params', 'plot_params']:
            if s in flask.session:
                del flask.session[s]
        return flask.redirect(flask.url_for('plot'))
    elif 'delete' in flask.request.values:
        # TODO: sanitize the graph name
        graph_name = flask.request.values['delete']
        params_path = os.path.join(app.config['SAVED_GRAPHS_ABS'],
                                   graph_name + ".json")
        os.unlink(params_path)
        return flask.redirect(flask.url_for('plot'))

    # 'save' in flask.request.values
    graph_name = flask.request.values['graph_name']
    rrds = flask.request.values.getlist('rrd')
    dses = flask.request.values.getlist('ds')
    names = flask.request.values.getlist('name')
    # TODO: sanity checks (graph_name =~ /^[a-zA-Z0-9_]+$/, list lengths equal
    # and >0, paths in rrds, names distinct and appropriate, ...)
    values = [
        {"rrd": rrds[i], "ds": dses[i], "name": names[i]}
        for i in range(len(rrds))
    ]

    params = {
        'graph': values,
        'params': flask.session.get('params', {}),
        'plot_params': flask.session.get('plot_params', {}),
    }
    params_path = os.path.join(app.config['SAVED_GRAPHS_ABS'],
                               graph_name + ".json")
    with open(params_path, 'w') as f:
        json.dump(params, f)
        f.write('\n')
    return flask.redirect(flask.url_for('graph', name = graph_name))

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

@app.route("/edit/datasources", methods = ["GET"])
def browse_datasources():
    if 'file' not in flask.request.values:
        return flask.redirect(flask.url_for('browse_files'))

    # TODO: sanity check (leading slash, "..")
    filename = flask.request.values['file'].strip('/')
    filename_abs = os.path.join(app.config['RRD_PATH'], filename)
    datasources = rrd.list_variables(filename_abs)

    return flask.render_template('browse_datasources.html',
                                 file = filename, datasources = datasources)

@app.route("/edit/datasources", methods = ["POST"])
def browse_datasources_finish():
    prev_dses = flask.session.get('graph', [])
    # TODO: sanity check (leading slash, "..")
    filename = flask.request.values['file'].strip('/')
    new_dses = flask.request.values.getlist('datasource')

    flask.session['graph'] = graph_datasources(prev_dses, filename, new_dses)
    return flask.redirect(flask.url_for('plot'))

#-----------------------------------------------------------------------------

def encode(data):
    return base64.b64encode(json.dumps(data))

def decode(data):
    try:
        return json.loads(base64.b64decode(data))
    except:
        flask.abort(400)

#-----------------------------------------------------------------------------

def combine_params(graph_def, graph_params, params):
    def fill(s):
        if not isinstance(s, (str, unicode)):
            return s
        fields = _PARAM_RE.split(s)
        for i in range(1, len(fields), 2):
            fields[i] = params.get(fields[i], '')
        return ''.join(fields)

    graph_def = [
        {n: fill(d[n]) for n in ['name', 'rrd', 'ds']}
        for d in graph_def
    ]
    graph_params = {
        k: fill(graph_params[k])
        for k in graph_params
    }

    # TODO: fill me
    return (graph_def, graph_params)

#-----------------------------------------------------------------------------

def graph_datasources(prevlist, filename, dslist):
    used_names = {e["name"]: 0 for e in prevlist}

    def name_for(e):
        if e not in used_names:
            used_names[e] = 0
            return e
        else:
            used_names[e] += 1
            return "%s%d" % (e, used_names[e])

    new_dses = [
        {"rrd": filename, "ds": e, "name": name_for(e)}
        for e in dslist
    ]
    return prevlist + new_dses

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
