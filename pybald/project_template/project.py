#!/usr/bin/env python
# encoding: utf-8
"""
project.py

A module to hold project specific members and configuration.

Created by mikepk on 2009-07-24.
Copyright (c) 2009 Michael Kowalchik. All rights reserved.
"""

# temporary until I have pybald be installable
pybald_path = '/usr/share/tzl/pybald'

# define the project path (the location of this file)
path = os.path.dirname( os.path.realpath( __file__ ) )
debug = True

def get_db_connection_string():
    '''Get the database credentials for connection.'''
    return {'host':'HOSTNAME', 'user':'USER', 'passwd':'PWD', 'db':'DB'}


# define project routes for the URL mapper
def set_routes(rmap):
    '''Simple function to define routes. A routes map object should be passed in.'''

    # the order of the routes is important, more specific should come before
    # more generic
    
    # home
    rmap.connect('home','', controller='home')
    rmap.connect('index/{action}', controller='home')    

    # cards RESTful mapping
    # rmap.resource('x', 'x')

    # generic pattern
    rmap.connect('{controller}/{action}/{id}')

def get_path():
    '''Return the project path.'''
    return path
