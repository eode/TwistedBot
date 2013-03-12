# -*- coding: utf-8 -*-
"""programming tools - commander only"""

from twistedbot.behaviours import BehaviourBase
from twistedbot import logbot
from twistedbot import config

log = logbot.getlogger("DEBUG PLUGIN")


def commander_only(method):
    def authorized_method(speaker, verb, data, interface):
        if speaker.lower() != config.COMMANDER.lower():
            msg = "This command is commander-only (not for you)"
            interface.world.chat.send_message(msg)
            return
        return method(speaker, verb, data, interface)
    return authorized_method


@commander_only
def eid(speaker, verb, data, interface):
    """eid <number> - Display the entity referenced by the given entity id"""
    wfc = interface.world, interface.world.factory, interface.world.chat
    world, factory, chat = wfc
    try:
        eid = int(data.strip())
    except ValueError:
        chat.send_message("Expected a number, but got '%s' instead." % data)
        return
    chat.send_message(str(world.entities.get(eid, None)))


@commander_only
def neighbors(speaker, verb, data, interface):
    """Reports traversible neighbors of a coordinate."""
    wfc = interface.world, interface.world.factory, interface.world.chat
    world, factory, chat = wfc
    from twistedbot.utils import Vector
    from twistedbot.gridspace import GridSpace
    coords = [int(d.strip()) for d in data.split(',')]
    grid = GridSpace(world.dimension.grid)
    neigh = grid.neighbours_of(Vector(*coords))
    log.msg(repr([(i.coords, i.can_stand) for i in neigh]))
    chat.send_message("k.")


@commander_only
def py_eval(user, verb, data, interface):
    """evaluate basic python code
    There are some limitations due to allowed characters in minecraft chat."""
    wfc = interface.world, interface.world.factory, interface.world.chat
    world, factory, chat = wfc
    try:
        val = str(eval(data.strip()))
    except Exception, e:
        log.err()
        val = "Exception: " + str(type(e))
    # chat will balk on messages if they contain specific characters.
    chat.send_message(val)


class PluginBehaviour(BehaviourBase):
    pass


def longmsg(user, verb, data, interface):
    msg = 'x' * 85
    msg = msg + 'abcdefghijklmnopqrstuvwxyz'
    if data.strip() == 'whisper':
        interface.world.chat.send_message("Whispering!")
        interface.world.chat.send_message(msg, whisper=True)
    else:
        interface.world.chat.send_message(msg)


def exception(user, verb, data, interface):
    {}['causing an exception']


verbs = {
    "eid": eid,
    "neighbors": neighbors,
    "eval": py_eval,
    "longmsg": longmsg,
    "exception": exception,
    }
