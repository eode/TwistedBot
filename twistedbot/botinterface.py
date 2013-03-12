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
        self._active_slot = None

    def __getattr__(self, name):
        if name in self.verbs:
            return self.verbs[name]
        raise AttributeError("BotInterface object has no attribute '%s'"
                             % name)

    @property
    def held(self):
        return self.inventory.ready[self._active_slot]

    @held.setter
    def held(self, item):
        self.inventory.ready[self._active_slot] = item

    @property
    def inventory(self):
        return self.world.inventories[WID_INVENTORY]

    @property
    def mouse(self):
        return self.world.inventories[WID_MOUSE]

    def click_entity(self, entity_ref, button):
        """Click on given entity or entity id.
        entity_ref := eid or entity object
        button := LEFT_CLICK or RIGHT_CLICK
        """
        # LEFT_CLICK and RIGHT_CLICK are pulled from inventory, but this
        # packet uses an opposite schema from what inventory uses.. *sigh*..
        button = not button
        target_eid = entity_ref if type(entity_ref) == int else entity_ref.eid
        self.world.send_packet('animation', eid=self.entity.eid, animation=1)
        self.world.send_packet('use entity', eid=self.entity.eid,
                               target=target_eid, button=button)

    def click_slot(self, button, slot, shift=False, func=None):
        func = lambda x: x if not func else func
        return self.mouse.click_slot(button, slot, func, shift)

    def click(self, clickable, mouse_button, shift=False, func=None):
        """click(entity, button) -> None
        click(slot_item, button, shift=False, func=None) -> [] (read below)

        'Click' on the clickable.  This should mirror the minecraft UI, so
        'clicking' here should have the same effect as clicking on the same
        item in the minecraft client.

        For this to work, you must send in a recognized item type.  Currently,
        the recognized types are:
            Entity
            Slot (Item or NoItem)
                If sending 'Slot'

        Slots can be acquired through the inventory attribute of this class.
        Entities can be acquired through world.entities.
        """
        if isinstance(clickable, entities.Entity):
            self.click_entity(clickable, mouse_button)
        elif isinstance(clickable, items.Slot):
            self.click_slot(mouse_button, clickable, shift, func)
        else:
            log.msg("Unrecognized item type to click: " + str(type(clickable)))

    def _drop_item(self, item):
        """Drop given item, moving it to held slot if needed."""
        def drop(success):
            if success:
                self.world.reactor.callLater(0.2, self.drop)
            return success
        self.hold(item, func=drop)

    def drop(self, count=-1, item=None):
        """drop() -> drop the whole stack of the currently-held item
        drop(13) -> drop 13 of the currently-held item
        """
        packet = {'state': None, 'x': 0, 'y': 0, 'z': 0, 'face': 0}
        if count < 0:
            packet['state'] = 3
            self.world.send_packet("player digging", packet)
            self.held = None
        else:
            packet['state'] = 4
            for I in xrange(count):
                if self.held.count:
                    self.world.send_packet('player digging', packet)
                    self.held.count -= 1
                    if not self.held.count:
                        self.held = None

    def drop_everything(self, cycling=False):
        delay = 0
        increment = 0.3
        for item in self.inventory.ready:
            if not item:
                continue
            self.world.reactor.callLater(delay, self._drop_item, item)
            delay += increment

        for item in self.inventory.general:
            if not item:
                continue
            self.world.reactor.callLater(delay, self._drop_item, item)
            delay += increment


    def left_click(self, what, shift=False, func=None):
        """Shortcut for click, using mouse_button=LEFT_CLICK"""
        self.click(what, LEFT_CLICK, shift, func)

    def right_click(self, what, shift=False, func=None):
        """Shortcut for click, using mouse_button=RIGHT_CLICK"""
        self.click(what, RIGHT_CLICK, shift, func)

    def hold(self, item, lookup=True, general_inventory=True,
             func=lambda x: x):
        """hold(item) -> True, [], or Exception is raised with error message.
        hold the specified item, which must be in the ready inventory.
        if item is a Slot object, hold that item.
        if item is a string, look for that item, and hold that.

        if general_inventory is True, then the action will be performed
        asynchronously, and a list will be returned instead of True.  Once the
        asynchronous activity is completed, the results (True or False) will be
        appended to the list.
        """
        if lookup and isinstance(item, (str, unicode)):
            item_str = item
            options = self.inventory.ready.lookup(item)
            if options:
                item = options[0]
            elif general_inventory:
                options = self.inventory.general.lookup(item)
                if options:
                    item = options[0]
                else:
                    msg = "Couldn't find '" + item_str + "' in inventory."
                    raise Exception(msg)
            else:
                msg = "Couldn't find '" + item_str + "' in ready inventory."
                raise Exception(msg)
        if item not in self.inventory.ready:
            if not general_inventory or (item not in self.inventory.general):
                msg = "Could not find '" + item.name + "' in inventory."
                raise Exception(msg)
        if item in self.inventory.ready:
            self.world.send_packet('held item change',
                                   {'item': item.gc_slot_number})
            func(True)
            return True
        # now for the more complex, async case..
        ready = self.inventory.ready
        general = self.inventory.general
        item_str = item.name  # now that we have the item, use it exactly
        # the methods we create can set the result[0] to whatever, thus adding
        # a deferred result.  ..we should really make an event engine.
#TODO: event engine (avoid this circuitous stuff)
        result = []

        ## if the move of the stack succeeds, this will be executed.
        def switch_to(success):
            if not success:
                result.append(False)
            options = ready.lookup(item_str)
            if not options:
                result.append(False)
                return False
            item = options[0]
            self.world.send_packet('held item change',
                                   {'item': item.gc_slot_number})
            result.append(func(True))
        if ready.has_room():
            self.move_stack(item, ready, switch_to)
            return result

        # ready does not have room.  Make method to pass to move_stack
        # in case it succeeds at swapping out an item from ready
        def general_to_ready(success):
            if not success or not ready.has_room():
                result.append(False)
            self.move_stack(item, ready, switch_to)
        swappable = general[8]  # ..may as well use the last item..
        self.move_stack(swappable, general, general_to_ready)
        return result

    def move_stack(self, item, dest, func=None):
        """Try to move the given items to the given destination.  If we
        succeed, run func(True), otherwise, run func(False)"""
        def put_callback(success):
            if not success:
                func(False)
                return False
            self.mouse.put_stack(dest, func=func)
        # Execution order (dependent upon success of each):
        # take_stack -> put_callback -> put_stack -> func
        self.mouse.take_stack(item, func=put_callback)

