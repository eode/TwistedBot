# -*- coding: utf-8 -*-
"""commands relating to inventory and manipulating objects"""


from twistedbot.behaviours import BehaviourBase
from twistedbot import logbot


log = logbot.getlogger("INVENTORY PLUGIN")

inventory_names = {
    'armor': 'interface.inventory.armor',
    'chest': '"<not yet implemented>"',
    'general': 'interface.inventory.general',
    'full': 'interface.inventory',
    'ready': 'interface.inventory.ready',
    }


def hold(speaker, verb, data, interface):
    """hold <item name> - Switch to that item (must be in ready inventory)"""
    item_name = data.strip()
    # Look for it in our ready inventory
    try:
        interface.hold(item_name, general_inventory=True)
    except Exception, e:
        if not str(e):
            raise
        interface.world.chat.send_message(str(e))


def move(speaker, verb, data, interface):
    """move <item> from <inventory> to <inventory>"""
    chat = interface.world.chat
    data = data.lower()
    try:
        item_name, data = data.split(' from ')
        source_name, dest_name = data.split(' to ')
    except:
        chat.send_message("huh?")
        return
#    try:
#        count, i = item_name.split(None, 1)
#        count = int(count)
#        item_name = i
#    except:
#        count = None

    # Check to see if we have that inventory name..
    for name in (source_name, dest_name):
        if name not in inventory_names:
            names = ', '.join(inventory_names.keys())
            chat.send_message("Inventory name options: " + names)
            return
    source = eval(inventory_names[source_name])
    dest = eval(inventory_names[dest_name])
    items = source.lookup(item_name)
    if not items:
        chat.send_message("%s inventory does not contain %s"
                            % (source_name, item_name))
        return
    item = items[0]
    invs = interface.world.inventories
    assert item is invs[item.wid][item.window_slot_number]
    if not dest.has_room():
        chat.send_message(dest_name + " has no room.")
    interface.move_stack(item, dest)


def list_inventory(speaker, verb, data, interface):
    """list: list inventories.  list <inventory>: list items in an inventory"""
    chat = interface.world.chat
    name = data.strip().lower()

    # Check to see if we have that inventory name..
    if name not in inventory_names:
        names = ', '.join(inventory_names.keys())
        chat.send_message("Inventory name options: " + names)
        return
    inventory = eval(inventory_names[name])

    interface.world.chat.send_message(str(inventory))


class PluginBehaviour(BehaviourBase):
    pass


verbs = {"hold": hold,
         "list": list_inventory,
         "move": move,
         }