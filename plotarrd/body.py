#!/usr/bin/python

import flask
app = flask.Flask(__name__)

#-----------------------------------------------------------------------------

@app.route("/")
def hello():
    return "Hello World!\n"

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker
