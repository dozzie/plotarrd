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

def plot(values, rrd_root, width = None, height = None, title = None, timescale = None):
    used_names = {}
    defs = []
    lines = []
    auto_colour_idx = 0

    for v in values:
        if v['ds'] in used_names:
            val_name = "%s%d" % (v['ds'], used_names[v['ds']])
            used_names[v['ds']] += 1
        else:
            val_name = v['ds']
            used_names[v['ds']] = 1
        datasource = v['ds']
        rrd_file = os.path.join(rrd_root, v['rrd'])
        consolidation_function = "AVERAGE" # let's hope it's there
        line_label = val_name
        colour = _AUTO_COLOURS[auto_colour_idx]
        auto_colour_idx += 1

        defs.append(
            "DEF:%s=%s:%s:%s" % (
                val_name, rrd_file, datasource, consolidation_function
            )
        )
        lines.append(
            "LINE:%s%s:%s" % (
                val_name, colour, line_label
            )
        )

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
    if timescale is not None:
        rrd_commands.extend([
            '--start', 'now - %s' % (timescale,),
            '--end', 'now - 1' % (timescale,),
        ])

    rrd_commands.extend(defs)
    rrd_commands.extend(lines)
    # make sure it's a string everywhere
    for i in range(len(rrd_commands)):
        rrd_commands[i] = str(rrd_commands[i])

    result = rrdtool.graphv(*rrd_commands)
    return result['image']

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
