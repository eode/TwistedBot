# -*- coding: utf-8 -*-
"""
This is a method of providing plugins for bot functionality.

Each public member of this module should be a dict, where the key is the name
of the module, and the value is the imported module.  The rest should be
handled internally, or by the module developer.

@author: silver
"""
import os as _os
import sys as _sys
import inspect as _inspect
from glob import glob as _glob

import twistedbot.logbot as _logbot

_log = _logbot.getlogger('PLUGINS')


def _load_plugins(prefix, plugins, plugins_folder):
        """Load plugins which have a specific prefix and suffix, e.g.:
            "behaviours_" and "_plugin.py".  Attach them to 'plugins', minus
            the prefix and suffix.  Add their verbs into self.verbs.
        """
        suffix = '_plugin.py'
        files = _glob(''.join((plugins_folder, '/', prefix, '*', suffix)))
        for f in files:
            assert _os.path.exists(f)
            name = _os.path.basename(f)[len(prefix):-len(suffix)]
            fullname = _os.path.basename(f)[:-len('.py')]
            if name in plugins:
                msg = 'Skipping plugin "{}" (name exists already)'
                _log.msg(msg.format(name))
                continue
            msg = 'Loading Plugin -- Type: {}, Name: "{}", Filename: "{}"'
            _log.msg(msg.format(prefix, name, f))
            module = __import__(fullname)
            plugins[name] = module

        _log.msg(str(plugins))

_plugins_folder = _os.path.dirname(_inspect.getfile(_inspect.currentframe()))

if _plugins_folder not in _sys.path:
    _log.msg("Adding "+_plugins_folder+" to sys.path")
    _sys.path.append(_plugins_folder)

behaviours = {}

_load_plugins('behaviour_', behaviours, _plugins_folder)
