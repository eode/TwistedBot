# -*- coding: utf-8 -*-

from twistedbot.behaviours import BehaviourBase
from twistedbot import logbot

log = logbot.getlogger("DEBUG PLUGIN")


def neighbors(speaker, verb, data,  context):
    """Reports traversible neighbors of a coordinate."""
    wfc = context['world'], context['factory'], context['chat']
    world, factory, chat = wfc
    from twistedbot.utils import Vector
    from twistedbot.gridspace import GridSpace
    coords = [int(d.strip()) for d in data.split(',')]
    grid = GridSpace(world.dimension.grid)
    neigh = grid.neighbours_of(Vector(*coords))
    log.msg(repr([(i.coords, i.can_stand) for i in neigh]))
    chat.send_message("k.")


class PluginBehaviour(BehaviourBase):
    pass

verbs = {"neighbors": neighbors}