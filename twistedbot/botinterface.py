# -*- coding: utf-8 -*-
"""
A high-level interface for the bot.

@author: silver
"""

from inventory import LEFT_CLICK, RIGHT_CLICK, WID_INVENTORY, WID_MOUSE
import logbot
import entities
import items
import plugins


log = logbot.getlogger('INTERFACE')


class BotInterface(object):
    """This is meant to be a high-level abstraction of the bot, implementing
    all aspects of a normal player interface, as well as being a central,
    unified location for bot behaviour access gained through plugins."""
    def __init__(self, bot_entity):
        self._entity = bot_entity
        self.world = bot_entity.world
        self.behaviours = plugins.behaviours
        self.verbs = {}
        for plugin in plugins.behaviours:
            plugin = plugins.behaviours[plugin]
            for verb in plugin.verbs:
                if verb in self.verbs:
                    msg = 'Cannot override pre-existing verb "%s"' % verb
                    self.world.chat.send_message(msg)
                    continue
                else:
                    self.verbs[verb] = plugin.verbs[verb]

    def __getattr__(self, name):
        if name in self.verbs:
            return self.verbs[name]
        raise AttributeError("BotInterface object has no attribute '%s'"
                             % name)

    @property
    def inventory(self):
        return self.world.inventories[WID_INVENTORY]

    @property
    def mouse(self):
        return self.world.inventories[WID_MOUSE]

    def _use_entity(self, target, button):
        """Accepts an entity or entity id.  Later, this should accept a block
        or block coord as well.
        """
        # LEFT_CLICK and RIGHT_CLICK are pulled from inventory, but this
        # command uses an opposite schema from what inventory uses.. *sigh*..
        button = not button
        target_eid = target if type(target) == int else target.eid
        self.world.send_packet('animation', eid=self.entity.eid, animation=1)
        self.world.send_packet('use entity', eid=self.entity.eid,
                               target=target_eid, button=button)

    def _click_window(self, button, window, slot, func=None, shift=False):
        func = lambda x: x if not func else func
        return self.mouse.click_window(button, window, slot, func, shift)

    def click(self, clickable, mouse_button, shift, **kwargs):
        """click(entity, button) -> None
        click(slot_item, button, shift, func=None) -> [] (read below)

        'Click' on the clickable.  This should mirror the minecraft UI, so
        whatever you would click on on the UI should have the same effect here.

        For this to work, you must send in a recognized item type.  Currently,
        the recognized types are:
            Entity
            Slot (Item or NoItem)

        Slots can be acquired through the inventory attribute of this class.
        Entities can be acquired through world.entities.
        """
        if isinstance(clickable, entities.Entity):
            self._click_entity(clickable, mouse_button)
        elif isinstance(clickable, items.Slot):
            self._click_window(mouse_button, clickable.wid, clickable.slot,
                               shift)
        else:
            log.msg("Unrecognized item type to click: " + str(type(clickable)))

    def click_left(self, what, shift=False):
        """Shortcut for click, using mouse_button=LEFT_CLICK"""
        self._click(what, LEFT_CLICK, shift)

    def click_right(self, what, shift=False):
        """Shortcut for click, using mouse_button=RIGHT_CLICK"""
        self._click(what, RIGHT_CLICK, shift)

    def hold(self, item, lookup=True):
        """hold(item) -> None or error message
        hold the specified item, which must be in the ready inventory.
        if item is a Slot object, hold that item.
        if item is a string, look for that item, and hold that.
        """
        if lookup and isinstance(item, (str, unicode)):
            item_str = item
            options = self.inventory.ready.lookup(item)
            if options:
                item = options[0]
            else:
                return "Couldn't find '" + item_str + "' in readied inventory."
        if item not in self.inventory.ready:
            return "Could not find '" + item.name + "' in readied inventory."
        else:
            self.world.send_packet('held item change', {'item': item.sub_slot})


