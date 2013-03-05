# -*- coding: utf-8 -*-
"""built-in fighting behaviours"""


from twistedbot.behaviours import BehaviourBase
from twistedbot import logbot

log = logbot.getlogger("Example Plugin")


def strike(speaker, verb, data, interface):
    """"strike <player>": Strike a player with whatever is in-hand (or bare handed)"""
    name = data.strip()
    if name in interface.world.entities.players:
        player_eid = interface.world.entities.players[name]
        interface.world.bot_interface.click(player_eid, True)


class PluginBehaviour(BehaviourBase):
    pass

verbs = {"strike": strike}