# -*- coding: utf-8 -*-
"""commands relating to inventory and manipulating objects"""


from twistedbot.behaviours import BehaviourBase
from twistedbot import logbot

log = logbot.getlogger("INVENTORY PLUGIN")


def hold(speaker, verb, data,  interface):
    """hold <item name> - Switch to that item (must be in ready inventory)"""
    item_name = data.strip()
    message = interface.hold(item_name)
    if message:
        interface.world.chat.send_message(message)


def ready(speaker, verb, data, interface):
    """ready: show the items in the ready inventory area"""
    items = [item.name for item in interface.inventory.ready[:] if item]
    free = len([item for item in interface.inventory.ready if not item])
    if free:
        items.append('and ' if items else '' + '%d free slots.' % free)
    interface.world.chat.send_message(', '.join(items))


def inventory(speaker, verb, data, interface):
    """inventory: show the items in the general inventory area"""
    items = [item.name for item in interface.inventory.player[:] if item]
    free = len([item for item in interface.inventory.player if not item])
    if free:
        items.append('and ' if items else '' + '%d free slots.' % free)
    interface.world.chat.send_message(', '.join(items))


class PluginBehaviour(BehaviourBase):
    pass

verbs = {"hold": hold,
         "ready": ready,
         "inventory": inventory,
         }