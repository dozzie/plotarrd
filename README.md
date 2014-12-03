Plotarrd -- web-based RRD browser
=================================

Plotarrd is a small webapplication for browsing RRD files and plotting them in
some simple way.

The central function of Plotarrd is to expose predefined, named graph through
a friendly URL, like

    http://example.net/plotarrd/temperature.png

assuming, of course, that Plotarrd is deployed under
<http://example.net/plotarrd/> and the predefined graph is called
*temperature*.

To make things easier for operator, Plotarrd allows also to define new graphs
and save them for later.

All the fuss is to combine [collectd](http://collectd.org) as a data collector
and [DashWiki](http://dashwiki.jarowit.net/) as a dashboard. Of course,
there's no problem to use Plotarrd with any other metrics collector (as long
as it writes RRD files) or dashboard application.


URL interface
-------------

All PNG URLs allow specifying image size and graph period.

    http://example.net/plotarrd/temperature.png?size=800x500
    http://example.net/plotarrd/temperature.png?timespan=2weeks

Currently, only the recent period is displayed (i.e. there's no way to make
a graph for 3 days that were two months ago).

The timespan is anything that RRDtool accepts, especially in the form of
`{number}{unit}`, where `{unit}` can be `minute`, `hour`, `day`, `week`,
`month` or `year` (of course, it's not limited to those).

All editing resides under `.../edit/*` path
(`http://example.net/plotarrd/edit/` with our current convention for
examples), so even though Plotarrd doesn't provide any access control, it
should be fairly easy to add one with HTTP server.


Parametrized graphs
-------------------

Several graphs can use parameters in the form of `${name}` in various places:

  * variable label
  * RRD database path
  * datasource
  * title
  * Y-axis label

These parameters typically will be passed as *GET* parameters. They can also
have default values (this is recommended practice, so one can quickly see what
this graph is about).

For instance, one could define a graph *free_disk* as follows:

    | label | file                                         | DS    |
    | used  | ${host}/df-${filesystem}/df_complex-used.rrd | value |

This graph could be then displayed as

    http://example.net/plotarrd/free_disk.png?host=web01.example.net&filesystem=root

Installation
------------

Simple WSGI application, requiring Python bindings for RRDtool and
[Flask](http://flask.pocoo.org/) (0.6+; older versions were not checked).
Python 2.6 or newer (it possibly works under 2.5, but this was not checked).

**TODO**: be more verbose.


Contact
-------

Plotarrd is written by Stanislaw Klekot `(dozzie at jarowit.net)`.
The primary distribution point is
[dozzie.jarowit.net](http://dozzie.jarowit.net/), with
a secondary address on [GitHub](https://github.com/dozzie/plotarrd).

Plotarrd is distributed under 3-clause BSD license. See `COPYING` file for
details.
