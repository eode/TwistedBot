# -*- coding: utf-8 -*-
"""
Created on Fri Feb 15 15:32:22 2013

@author: silver
"""


from twistedbot.behaviours import BehaviourBase
from twistedbot import logbot

log = logbot.getlogger("Example Plugin")

def punch(speaker, verb, data, context):
    world, factory = context['world'], context['factory']
    name = data.strip()
    if name in world.entities.players:
        player_eid = world.entities.players[name]
        world.bot_interface.click(player_eid, True)


class PluginBehaviour(BehaviourBase):
    pass

verbs = {"punch": punch}