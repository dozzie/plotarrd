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

@app.route("/plot")
def plot():
    plot_def = PlotParams(session = flask.session)
    if len(plot_def) == 0:
        url = None
    else:
        url = flask.url_for('render', params = plot_def.get_render_arg())

    return flask.render_template('plot.html',
                                 image_url = url,
                                 values      = plot_def.get_defs(),
                                 plot_params = plot_def.get_plot_opts(),
                                 params      = plot_def.get_params())

#-----------------------------------------------------------------------------

@app.route("/plot/labels", methods = ["POST"])
def plot_set_labels():
    # form fields:
    #   * title, ylabel, ymin, ymax
    #   * timespan + timespan_unit
    #   * update=update

    plot_def = PlotParams(session = flask.session)
    for name in ['title', 'ylabel', 'timespan_unit']:
        value = flask.request.values.get(name, '').strip()
        plot_def.set_plot_opt(name, value) # "" == undef

    for name in ['ymin', 'ymax']:
        value = flask.request.values.get(name)
        if value is None or value == '':
            value = None
        elif '.' in value or 'e' in value or 'E' in value:
            value = float(value)
        else:
            value = int(value)
        plot_def.set_plot_opt(name, value)

    value = flask.request.values.get('timespan')
    if value is None or value == '':
        plot_def.set_plot_opt('timespan', None)
        plot_def.set_plot_opt('timespan_unit', None)
    else:
        unit = flask.request.values.get('timespan_unit', 'd')
        plot_def.set_plot_opt('timespan', int(value))
        plot_def.set_plot_opt('timespan_unit', unit)

    plot_def.session_save()

    return flask.redirect(flask.url_for('plot'))

@app.route("/plot/variables", methods = ["POST"])
def plot_set_variables():
    # form fields:
    #   * name, rrd, ds -- getlist()
    #   * delete (int)
    #   * newvarname, newvarexpr, newvards, update=add
    #   * update=update

    plot_def = PlotParams(session = flask.session)

    if 'delete' in flask.request.values:
        entry = int(flask.request.values['delete'])
        plot_def.del_def(entry)
    elif flask.request.values['update'] == 'add':
        # TODO: expressions
        if not path_ok(flask.request.values['newvarexpr']):
            flask.abort(403)
        plot_def.add_def(
            name = flask.request.values['newvarname'],
            rrd  = flask.request.values['newvarexpr'],
            ds   = flask.request.values['newvards'],
        )
    else:
        # TODO: expressions
        names = flask.request.values.getlist('name')
        rrds = flask.request.values.getlist('rrd')
        dses = flask.request.values.getlist('ds')
        def path_filter(path):
            if not path_ok(path): flask.abort(403)
            return path
        plot_def.set_defs([
            {"rrd": path_filter(rrds[i]), "ds": dses[i], "name": names[i]}
            for i in range(len(rrds))
        ])

    plot_def.session_save()

    return flask.redirect(flask.url_for('plot'))

@app.route("/plot/params", methods = ["POST"])
def plot_set_params():
    # form fields:
    #   * param, value -- getlist()
    #   * delete (str)
    #   * newparamname, newparamdefault, update=add
    #   * update=update

    plot_def = PlotParams(session = flask.session)

    if 'delete' in flask.request.values:
        entry = flask.request.values['delete']
        plot_def.del_param(entry)
    elif flask.request.values['update'] == 'add':
        plot_def.add_param(
            flask.request.values['newparamname'],
            flask.request.values['newparamdefault'],
        )
    else:
        names = flask.request.values.getlist('param')
        values = flask.request.values.getlist('value')
        plot_def.set_params(dict(zip(names, values)))

    plot_def.session_save()

    return flask.redirect(flask.url_for('plot'))

#-----------------------------------------------------------------------------

@app.route("/render/<params>")
def render(params):
    plot_def = PlotParams(b64 = params)
    values, opts = plot_def.get_rrdplot_args()
    # sanity check on RRD paths
    if not defs_ok(values):
        flask.abort(403)

    img = rrd.plot(values = values, rrd_root = app.config['RRD_PATH'],
                   **opts)
    return flask.Response(response = img, content_type = 'image/png')

@app.route("/graph/<name>", methods = ["GET"])
def graph(name):
    if not path_ok(name): # `name' is still a path (though it can't have "/")
        flask.abort(403)

    try:
        params_path = os.path.join(app.config['SAVED_GRAPHS_ABS'],
                                   name + '.json')
        plot_def = PlotParams(filename = params_path)
        url = flask.url_for('render_saved', name = name)

        return flask.render_template('plot.html',
                                     graph_name = name,
                                     image_url = url,
                                     values      = plot_def.get_defs(),
                                     plot_params = plot_def.get_plot_opts(),
                                     params      = plot_def.get_params())
    except IOError:
        flask.abort(404)

# ?size={Width}x{Height}&timespan={Time}
# {Time} can be "15min", "8h", "1d", "4w", "1month", "1y" and so on
@app.route("/graph/<name>.png")
def render_saved(name):
    if not path_ok(name): # `name' is still a path (though it can't have "/")
        flask.abort(403)

    if 'size' in flask.request.args:
        width, height = flask.request.args['size'].split('x')
        width = int(width)
        height = int(height)
    else:
        width = None
        height = None
    timespan = flask.request.args.get('timespan')

    try:
        params_path = os.path.join(app.config['SAVED_GRAPHS_ABS'],
                                   name + '.json')
        plot_def = PlotParams(filename = params_path)

        for (name,value) in flask.request.args.items():
            if name == 'timespan' or name == 'size':
                continue
            plot_def.add_param(name, value)

        values, opts = plot_def.get_rrdplot_args(timespan = timespan)
        # sanity check on RRD paths
        # XXX: after propagating all the parameters, defaults and from GET
        if not defs_ok(values):
            flask.abort(403)

        img = rrd.plot(values = values, rrd_root = app.config['RRD_PATH'],
                       width = width, height = height, **opts)
        return flask.Response(response = img, content_type = 'image/png')
    except IOError:
        flask.abort(404)
    except KeyError:
        flask.abort(400)

#-----------------------------------------------------------------------------

@app.route("/edit/new")
def start_anew():
    plot_def = PlotParams(session = flask.session)
    plot_def.session_unset()
    return flask.redirect(flask.url_for('plot'))

#-----------------------------------------------------------------------------

@app.route("/edit/save", methods = ["POST"])
def plot_save():
    # TODO:
    #   * sanitize the submitted form
    #   * save the submitted form (flask.request.values.getlist() for "rrd"
    #     and "ds")

    plot_def = PlotParams(session = flask.session)

    if 'discard' in flask.request.values:
        plot_def.session_unset()
        return flask.redirect(flask.url_for('plot'))
    elif 'delete' in flask.request.values:
        graph_name = flask.request.values['delete']
        if not path_ok(graph_name):
            flask.abort(403)
        params_path = os.path.join(app.config['SAVED_GRAPHS_ABS'],
                                   graph_name + ".json")
        try:
            os.unlink(params_path)
        except OSError:
            flask.abort(404)
        return flask.redirect(flask.url_for('plot'))

    # 'save' in flask.request.values
    graph_name = flask.request.values['graph_name']
    rrds = flask.request.values.getlist('rrd')
    dses = flask.request.values.getlist('ds')
    names = flask.request.values.getlist('name')

    # TODO: sanity checks (graph_name =~ /^[a-zA-Z0-9_]+$/, list lengths equal
    # and >0, paths in rrds, names distinct and appropriate, ...)
    if not re.match(r'^[a-zA-Z0-9_]+$', graph_name):
        flask.abort(403) # invalid graph name

    # NOTE: checking DEFs now is not that necessary, since plotting saved
    # graph still needs to check paths
    def path_filter(path):
        if not path_ok(path): flask.abort(403)
        return path
    plot_def.set_defs([
        {"rrd": path_filter(rrds[i]), "ds": dses[i], "name": names[i]}
        for i in range(len(rrds))
    ])

    params_path = os.path.join(app.config['SAVED_GRAPHS_ABS'],
                               graph_name + ".json")
    with open(params_path, 'w') as f:
        json.dump(plot_def.to_dict(), f)
        f.write('\n')
    return flask.redirect(flask.url_for('graph', name = graph_name))

#-----------------------------------------------------------------------------

@app.route("/edit/browse")
def browse_files():
    if 'dir' in flask.request.values:
        dirname = flask.request.values['dir'].strip('/')
        if not path_ok(dirname):
            flask.abort(403)
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

    filename = flask.request.values['file'].strip('/')
    if not path_ok(filename):
        flask.abort(403)
    filename_abs = os.path.join(app.config['RRD_PATH'], filename)
    datasources = rrd.list_variables(filename_abs)

    return flask.render_template('browse_datasources.html',
                                 file = filename, datasources = datasources)

@app.route("/edit/datasources", methods = ["POST"])
def browse_datasources_finish():
    plot_def = PlotParams(session = flask.session)

    rrd = flask.request.values['file'].strip('/')
    if not path_ok(rrd):
        flask.abort(403)
    for ds in flask.request.values.getlist('datasource'):
        plot_def.add_def(name = ds, rrd = rrd, ds = ds)

    plot_def.session_save()

    return flask.redirect(flask.url_for('plot'))

#-----------------------------------------------------------------------------
# utilities
#-----------------------------------------------------------------------------

def defs_ok(rrd_defs):
    for e in rrd_defs:
        if not path_ok(e['rrd']):
            return False
    return True

def path_ok(path):
    return not(path.startswith("/") or '..' in path.split('/'))

#-----------------------------------------------------------------------------

class PlotParams:
    _PARAM_RE = re.compile(r'\$\{([a-zA-Z0-9_.-]+)\}')

    def __init__(self, session = None, filename = None, b64 = None):
        # DEF statements
        self._graph_def = []
        self._used_names = None # names in _graph_def (lazily computed)

        # parameters to fill ${...} placeholders in labels and DEFs
        self._params = {}

        # remember the passed session dict (for unset() method)
        # NOTE: remember even if overriden with filename or b64
        if session is None:
            session = {}
        self._session = session

        # plot parameters
        self._title = None
        self._ylabel = None
        self._ymin = None
        self._ymax = None
        self._timespan = None
        self._timespan_unit = None

        if filename is not None:
            try:
                session = json.load(open(filename))
            except Exception, e:
                raise IOError(e)
        elif b64 is not None:
            # assume it's a hash and everything is generally correct
            # see also get_render_arg() method
            session = json.loads(base64.b64decode(b64))

        if session.get('graph') is not None:
            self._graph_def = session['graph']
        if session.get('params') is not None:
            self._params = session['params']
        if session.get('plot_params') is not None:
            self._title         = session['plot_params'].get('title')
            self._ylabel        = session['plot_params'].get('ylabel')
            self._ymin          = session['plot_params'].get('ymin')
            self._ymax          = session['plot_params'].get('ymax')
            self._timespan      = session['plot_params'].get('timespan')
            self._timespan_unit = session['plot_params'].get('timespan_unit')

    def __len__(self):
        return len(self._graph_def)

    def to_dict(self):
        return {
            'graph': self._graph_def,
            'params': self._params,
            'plot_params': self.get_plot_opts(),
        }

    # return JSON/Base64 serialized parameters (for /render/<stuff> URL)
    def get_render_arg(self):
        return base64.b64encode(json.dumps(self.to_dict()))

    # unset the variables carried in the session
    def session_unset(self):
        if 'graph' in self._session:
            del self._session['graph']
        if 'params' in self._session:
            del self._session['params']
        if 'plot_params' in self._session:
            del self._session['plot_params']

    def session_save(self):
        self._session['graph'] = self.get_defs()
        self._session['params'] = self.get_params()
        self._session['plot_params'] = self.get_plot_opts()

    def get_rrdplot_args(self, timespan = None):
        def fill(s):
            if not isinstance(s, (str, unicode)): # this includes `None'
                return s
            fields = PlotParams._PARAM_RE.split(s)
            for i in range(1, len(fields), 2):
                fields[i] = self._params.get(fields[i], '')
            return ''.join(fields)

        if timespan is None and \
           self._timespan is not None and self._timespan_unit is not None:
            timespan = "%d%s" % (self._timespan, self._timespan_unit)

        values = [
            {n: fill(d[n]) for n in ['name', 'rrd', 'ds']}
            for d in self._graph_def
        ]
        opts = {
            'title': fill(self._title),
            'ylabel': fill(self._ylabel),
            'ymin': self._ymin,
            'ymax': self._ymax,
            'timespan': timespan,
        }
        return (values, opts)


    # [ {'name': str(), 'rrd': str(), 'ds': str()} ]
    def get_defs(self):
        return list(self._graph_def) # shallow copy

    # { Name: DefaultValue, ... }
    def get_params(self):
        return dict(self._params) # shallow copy

    # {
    #   'title':? str(),
    #   'ylabel':? str(),
    #   'ymin':? number(),
    #   'ymax':? number(),
    #   'timespan':? int(),
    #   'timespan_unit': "h" | "d" | "w" | "m"
    # }
    def get_plot_opts(self):
        result = {}
        if self._title is not None:
            result['title'] = self._title
        if self._ylabel is not None:
            result['ylabel'] = self._ylabel
        if self._ymin is not None:
            result['ymin'] = self._ymin
        if self._ymax is not None:
            result['ymax'] = self._ymax
        if self._timespan is not None and self._timespan_unit is not None:
            result['timespan']      = self._timespan
            result['timespan_unit'] = self._timespan_unit
        return result

    def add_def(self, name, rrd, ds):
        if self._used_names is None:
            self._used_names = set()
            for e in self._graph_def:
                self._used_names.add(e['name'])

        if name in self._used_names:
            cnt = 1
            while "%s%d" % (name, cnt) in self._used_names:
                cnt += 1
            name = "%s%d" % (name, cnt)

        self._graph_def.append({'name': name, 'rrd': rrd, 'ds': ds})

    def add_param(self, name, default_value):
        self._params[name] = default_value

    def set_plot_opt(self, name, value):
        if value == '':
            value = None

        if name == 'title':
            self._title = value
        if name == 'ylabel':
            self._ylabel = value
        if name == 'ymin':
            self._ymin = value
        if name == 'ymax':
            self._ymax = value
        if name == 'timespan':
            self._timespan = value
        if name == 'timespan_unit':
            self._timespan_unit = value

    def del_def(self, index):
        if index < len(self._graph_def):
            del self._graph_def[index]

    def del_param(self, name):
        if name in self._params:
            del self._params[name]

    def set_defs(self, graph_def):
        self._graph_def = graph_def

    def set_params(self, params):
        self._params = params

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
