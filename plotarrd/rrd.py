#!/usr/bin/python

import rrdtool
import os

#-----------------------------------------------------------------------------

_AUTO_COLOURS = [
    "#b35f35",
    "#b3aa35",
    "#70b335",
    #"#35b346",
    #"#35b391",
    "#3589b3",
    "#353eb3",
    "#7835b3",
    "#b335a2",
    #"#b33557",
]


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

def plot(values, rrd_root, width = None, height = None, timespan = None,
         title = None, ylabel = None, ymin = None, ymax = None):
    defs = []
    lines = []
    auto_colour_idx = 0

    for v in values:
        val_name = v['name']
        line_label = val_name

        if 'rrd' in v and 'ds' in v:
            datasource = v['ds']
            rrd_file = os.path.join(rrd_root, v['rrd'])
            consolidation_function = "AVERAGE" # let's hope it's there
            defs.append(
                "DEF:%s=%s:%s:%s" % \
                    (val_name, rrd_file, datasource, consolidation_function)
            )
        elif 'expr' in v:
            expression = v['expr']
            defs.append("CDEF:%s=%s" % (val_name, expression))

        if not val_name.startswith("_"):
            colour = _AUTO_COLOURS[auto_colour_idx]
            auto_colour_idx += 1
            lines.append("LINE:%s%s:%s" % (val_name, colour, line_label))

    rrd_commands = [
        '-', '--imgformat', 'PNG',
    ]
    if width is not None and height is not None:
        rrd_commands.extend([
            "--full-size-mode",
            "--width",  "%d" % (width),
            "--height", "%d" % (height),
        ])
    if title is not None:
        rrd_commands.extend(['--title', str(title)])
    if timespan is not None:
        rrd_commands.extend([
            '--start', 'now - %s' % (timespan,),
            '--end', 'now - 1',
        ])
    if ylabel is not None:
        rrd_commands.extend(['--vertical-label', ylabel])
    if ymin is not None:
        rrd_commands.extend(['--lower-limit', str(ymin)])
    if ymax is not None:
        rrd_commands.extend(['--upper-limit', str(ymax)])

    rrd_commands.extend(defs)
    rrd_commands.extend(lines)
    # make sure it's a string everywhere
    for i in range(len(rrd_commands)):
        rrd_commands[i] = str(rrd_commands[i])

    try:
        result = rrdtool.graphv(*rrd_commands)
        return result['image']
    except rrdtool.error, e:
        # XXX: pity I have to discriminate errors this way, but rrdtool
        # provides no other way
        if e.args[0].startswith('opening'):
            raise IOError(e)
        else:
            raise ValueError(e)

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
