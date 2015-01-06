from __future__ import unicode_literals

import logging
import os, sys, subprocess

import socket, threading
import tornado.web, tornado.websocket, tornado.ioloop, tornado.iostream
import json
import nad_tornado


from mopidy import config, ext

from configobj import ConfigObj, ConfigObjError
from validate import Validator
import jinja2

__version__ = '0.0.1'

logger = logging.getLogger(__name__)

class Extension(ext.Extension):
    dist_name = 'Mopidy-NadSettings'
    ext_name = 'nadsettings'
    version = __version__

    def setup(self, registry):
        registry.add('http:app', {
            'name': 'nadsettings',
            'factory': websettings_app_factory,
        })

    def get_default_config(self):
        conf_file = os.path.join(os.path.dirname(__file__), 'ext.conf')
        return config.read(conf_file)

    def get_config_schema(self):
        schema = super(Extension, self).get_config_schema()
        schema['ip_address'] = config.String()
        return schema

def websettings_app_factory(config, core):
    return [
	('/nadws', nad_tornado.WebSocketHandler, {'core': core, 'config': config}),
	('/', nad_tornado.IndexHandler, {'core': core})
    ]
