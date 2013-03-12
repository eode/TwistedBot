# -*- coding: utf-8 -*-
"""
Model the inventory for the bot (and possibly for mobs as well)

This is a little convoluted, for the sake of abstracting minecraftian server
'logic'.

Inventories are groupings of items which have a fixed size, and do not change.
Windows are composed of various inventories in a specific order, and are
indexable from zero as an inventory is -- however, all slots are composed of
inventory slots, and the index value rolls over to the next inventory.

so, for example:
    # If a FooWindow object has three inventories, which are (in order) --
    # FooInv, PlayerInv, and ReadiedInv, and a FooInv has four slots, then
    w = FooWindow()
    w[0] = 'foo'   # set first item in FooInv
    w[3] = 'bar'   # set last item in FooInv
    w[4] = 'baz'   # set the first item in PlayerInv
Similarly, if you set past the last value of PlayerInv, it will roll over to
ReadiedInv, and finally give an IndexError.

Mostly, Inventory

Inventory(Window):
CraftingTable(Window):
Chest(Window):
LargeChest(Window):
Furnace(Window):
Dispenser(Window):
EnchantmentTable(Window):

..the expected thing to hold here would be Item objects from the items module.

@author: Brian Visel
"""

import logbot
from items import Item, NoItem
from Queue import Queue, Full, Empty

from construct import Container

log = logbot.getlogger('INVENTORY')

WID_INVENTORY = 0
WID_MOUSE = -1

TYPE_CHEST = 0
TYPE_CRAFTING = 1
TYPE_FURNACE = 2
TYPE_DISPENSER = 3
TYPE_ENCHANTMENT = 4
#TYPE_BREWING = 5

# Mouse clicks
OUTSIDE_WINDOW = -999
LEFT_CLICK = 0
RIGHT_CLICK = 1
MIDDLE_CLICK = 3


class GameContainer(list):
    name = "Container"

    def __init__(self, size, data=None):
        if size < 1:
            raise ValueError("Size less than 1?")
        if data is not None:
            assert len(data) == size
        else:
            data = [None for _ in xrange(size)]
        super(GameContainer, self).__init__(data)

    def append(self, item):
        raise NotImplementedError("Append not allowed.")

    def extend(self, item):
        raise NotImplementedError("Extend not allowed.")

    def __repr__(self):
        return "%s(size=%d, data=%s)" % (type(self).__name__, len(self),
                                        super(GameContainer, self).__repr__())

    def __str__(self):
        counter = {}
        free = 0
        for item in self:
            if item is None:
                free += 1
                continue
            name = Item.names.get(item.id, "Unknown")
            if name in counter:
                counter[name] += item.count
            else:
                counter[name] = item.count
        counter = counter.items()
        counter.sort()
        strings = [(str(count) + ' ' if count > 1 else '') + name
                        for name, count in counter]
        if free:
            slots = str(free) + ' free slot%s.' % ('' if free == 1 else 's')
            strings.append(('and ' if strings else '') + slots)
        return self.name + ": " + ', '.join(strings)

    def has_room(self):
        return any(True for i in self if not i)


class GameContainerArmor(GameContainer):
    name = "Armor"

    def __init__(self, data=None):
        super(GameContainerArmor, self).__init__(size=4, data=data)

    def __repr__(self):
        return "%s(data=%s)" % (type(self).__name__,
                                super(type(self), self).__repr__())

    def __str__(self):
        values = "%s(head), %s(chest), %s(legs), %s(feet)"
        values = values % (self.head, self.chest, self.legs, self.feet)
        return self.name + ": " + values

    head = property(lambda s: s[0], lambda s, v: setattr(s, 0, v),
                    lambda s: setattr(s, 0, None))

    chest = property(lambda s: s[1], lambda s, v: setattr(s, 1, v),
                     lambda s: setattr(s, 1, None))

    legs = property(lambda s: s[2], lambda s, v: setattr(s, 2, v),
                    lambda s: setattr(s, 2, None))

    feet = property(lambda s: s[3], lambda s, v: setattr(s, 3, v),
                    lambda s: setattr(s, 3, None))


class GameContainerChest(GameContainer):
    name = "Chest"

    def __init__(self, data=None):
        super(GameContainerChest, self).__init__(size=27, data=data)

    def __repr__(self):
        return "%s(data=%s)" % (type(self).__name__,
                                super(type(self), self).__repr__())


class GameContainerChestLarge(GameContainer):
    name = "Large Chest"

    def __init__(self, data=None):
        super(GameContainerChestLarge, self).__init__(size=54, data=data)

    def __repr__(self):
        return "%s(data=%s)" % (type(self).__name__,
                                super(type(self), self).__repr__())


class GameContainerCraftingInput(GameContainer):
    name = "Crafting Area"

    def __init__(self, data=None):
        super(GameContainerCraftingInput, self).__init__(size=9, data=data)

    def __repr__(self):
        return "%s(data=%s)" % (type(self).__name__,
                                super(type(self), self).__repr__())


class GameContainerCraftingInputSmall(GameContainer):
    name = "Small Crafting Area"

    def __init__(self, data=None):
        sup = super(GameContainerCraftingInputSmall, self)
        sup.__init__(size=4, data=data)

    def __repr__(self):
        return "%s(data=%s)" % (type(self).__name__,
                                super(type(self), self).__repr__())

    def __str__(self):
        sup = super(GameContainerCraftingInputSmall, self)
        return sup.__str__().replace('\n', ' ')


class GameContainerDispenser(GameContainer):
    name = "Dispenser"

    def __init__(self, data=None):
        super(GameContainerDispenser, self).__init__(size=9, data=data)

    def __repr__(self):
        return "%s(data=%s)" % (type(self).__name__,
                                super(type(self), self).__repr__())


class GameContainerEnchantmentTable(GameContainer):
    name = "Item to Enchant"

    def __init__(self, data=None):
        super(GameContainerEnchantmentTable, self).__init__(size=1, data=data)

    def __repr__(self):
        return "%s(data=%s)" % (type(self).__name__,
                                super(type(self), self).__repr__())

    def __str__(self):
        return "Item for Enchantment: " + ', '.join(i for i in self if i)


class GameContainerEntityEquipment(GameContainer):
    """This is the class for the (generally visible) entity equipment for all
    mobs and players other than The Player/the bot."""
    name = "Equipment"

    def __init__(self, data=None):
        super(GameContainerEntityEquipment, self).__init__(size=4, data=data)

    def __repr__(self):
        return "%s(data=%s)" % (type(self).__name__,
                                super(type(self), self).__repr__())

    in_hand = property(lambda s: s[0], lambda s, v: setattr(s, 1, v),
                    lambda s: setattr(s, 0, None))

    head = property(lambda s: s[0], lambda s, v: setattr(s, 1, v),
                    lambda s: setattr(s, 0, None))

    chest = property(lambda s: s[1], lambda s, v: setattr(s, 2, v),
                     lambda s: setattr(s, 1, None))

    legs = property(lambda s: s[2], lambda s, v: setattr(s, 3, v),
                    lambda s: setattr(s, 2, None))

    feet = property(lambda s: s[3], lambda s, v: setattr(s, 4, v),
                    lambda s: setattr(s, 3, None))

    def __str__(self):
        tags = ["In Hand: %s", "Head: %s", "Chest: %s", "Legs: %s", "Feet: %s"]
        items = (tags[i] % self[i] for i in xrange(len(self)) if self[i])
        value = ', '.join(items)
        return self.name + ": " + value if value else ''


class GameContainerFurnaceFuel(GameContainer):
    name = "Fuel"

    def __init__(self, data=None):
        super(GameContainerFurnaceFuel, self).__init__(size=1, data=data)

    def __repr__(self):
        return "%s(data=%s)" % (type(self).__name__,
                                super(type(self), self).__repr__())


class GameContainerFurnaceItem(GameContainer):
    name = "Raw Item"

    def __init__(self, data=None):
        super(GameContainerFurnaceItem, self).__init__(size=1, data=data)

    def __repr__(self):
        return "%s(data=%s)" % (type(self).__name__,
                                super(type(self), self).__repr__())


class GameContainerReady(GameContainer):
    name = "Ready Items"

    def __init__(self, data=None):
        super(GameContainerReady, self).__init__(size=9, data=data)

    def __repr__(self):
        return "%s(data=%s)" % (type(self).__name__,
                                super(type(self), self).__repr__())


class GameContainerMouse(GameContainer):
    name = "Pointer"

    def __init__(self, data=None):
        super(GameContainerMouse, self).__init__(size=1, data=data)

    def __repr__(self):
        return "%s(data=%s)" % (type(self).__name__,
                                super(type(self), self).__repr__())


class GameContainerOutput(GameContainer):
    name = "Output"

    def __init__(self, data=None):
        super(GameContainerOutput, self).__init__(size=1, data=data)

    def __repr__(self):
        return "%s(data=%s)" % (type(self).__name__,
                                super(type(self), self).__repr__())

    def __str__(self):
        return super(GameContainerOutput, self).__str__().replace('\n', ' ')


class GameContainerGeneralInv(GameContainer):
    name = "General Inventory"

    def __init__(self, data=None):
        super(GameContainerGeneralInv, self).__init__(size=27, data=data)

    def __repr__(self):
        return "%s(data=%s)" % (type(self).__name__,
                                super(type(self), self).__repr__())


class GCProxy(object):
    def __init__(self, gc, window):
        self.start = 0
        self.window = window
        self.gc = gc
        for inv in window.inventories:
            if inv is gc:
                break
            self.start += len(inv)

    def __getitem__(self, index):
        if isinstance(index, (str, unicode)):
            return self.lookup(index)
        if isinstance(index, slice):
            if index.start is None:
                index = slice(0, index.stop, index.step)
            if index.stop is None:
                index = slice(index.start, len(self), index.step)
            if index.start < 0 and index.stop < 0:
                index = slice(len(self) + index.start, len(self) + index.stop,
                              index.step)
            index = slice(index.start + self.start, index.stop + self.start,
                          index.step)
        else:
            if index < 0:
                index = len(self) + index
            index = index + self.start
        return self.window[index]

    def __setitem__(self, index, value):
        if isinstance(index, slice):
            if index.start < 0 and index.stop < 0:
                index = slice(len(self) + index.start, len(self) + index.stop,
                              index.step)
            index = slice(index.start + self.start, index.stop + self.start,
                          index.step)
        else:
            if index < 0:
                index = len(self) + index
            index = index + self.start
        self.window[index] = value

    def __iter__(self):
        for i in xrange(len(self)):
            yield self[i]

    def __len__(self):
        return len(self.gc)

    def __str__(self):
        return str(self.gc)

    def __getattr__(self, name):
        if name in self.__dict__:
            return self.__dict__[name]
        return getattr(self.gc, name)

    def _general_lookup(self, name):
        hits = []
        name = name.lower().strip()
        for i in self:
            if name.strip().lower() in i.name.lower():
                hits.append(i)
        return hits

    def lookup(self, name, lenient=True):
        try:
            i = int(name.strip())
            return [self[i]]
        except ValueError:
            pass
        hits = []
        name = name.lower().strip()
        count = 0
        for item in self:
            count += 1
            if name.strip().lower() == item.name.lower():
                hits.append(item)
        if lenient and not hits:
            hits = self._general_lookup(name)
        return hits


class InventoryBase(object):
    """Combine various Inventory objects into one (fake) window, which we
    'open' when looking at player inventory, chest inventory, etc.

    Sub-inventories:
    sub-inventories may be accessed via an inventory by name or slot -- for
    example:
        inv = InventoryCraftingTable(foo, bar)
        inv.output[0] is inv[0]  # output is the first inventory in this window
        inv.ready[-1] is inv[-1]  # ready is the last inventory in this window


    the 'wid' and 'slot' attributes may change, depending on the last window
    to reference them.  It is wise to always grab a recent copy of the item
    if you have yielded, as data may have changed.

    e.g.:
        item = my_inv[3]
        data1 = item.wid, item.slot
        yield
        data2 = item.wid, item.slot
        data1 == data2  # may be false
        item = my_inv[3]
        data3 = item.wid, item.slot
        data1 == data3  # True
    """
    name = "Generic Inventory"
    window_manager = None

    def __init__(self, wid=None, *args):
        self.wid = int(wid)
        self.inventories = args
        self.inventories = [GCProxy(gc, self) for gc in args]

    def __len__(self):
        return sum(len(i) for i in self.inventories)

    def __getitem__(self, index):
        """o[start:end] -> list of Slot objects
        o[index] -> Slot object at index
        o[string] -> list of slots whose names (leniently) match string
        """
        if isinstance(index, (int, long)):
            # Works for pos or neg numbers, during slicing or otherwise
            if index < 0:
                index = len(self) + index
            i = index
            for inv in self.inventories:
                if i < len(inv):
                    item = inv.gc[i]
                    if item is None:
                        item = NoItem()
                    item.gc_slot_number = i
                    item.window_slot_number = index
                    item.wid = self.wid
                    return item
                else:
                    i = i - len(inv)
        elif isinstance(index, slice):
            if index.step:
                raise NotImplementedError("Window may not be step-sliced.")
            retval = []
            for i in xrange(index.start, index.stop):
                retval.append(self[i])
            return retval
        elif isinstance(index, (str, unicode)):
            return self.lookup(index)
        raise IndexError("Index out of range.")

    def __setitem__(self, index, value):
        if type(index) == slice:
            start = 0 if index.start is None else index.start
            stop = len(self) if index.stop is None else index.stop
            if index.step:
                raise NotImplementedError("Window may not be step-sliced.")
            x = 0
            for i in xrange(start, stop):
                self[i] = value[x]
                x += 1
            return
        if index < 0:
            index = len(self) + index
        for inv in self.inventories:
            if index < len(inv):
                inv.gc[index] = value
                return
            else:
                index = index - len(inv)
        raise IndexError("Index out of range")

    def __str__(self):
        return self.name + ': \n' + self.contents

    def _general_lookup(self, name):
        hits = []
        for inv in self.inventories:
            hits.extend(inv._general_lookup(name))
        return hits

    def lookup(self, name, lenient=True):
        hits = []
        for inv in self.inventories:
            new_hits = inv.lookup(name, lenient)
            hits.extend(new_hits)
        return hits

    contents = property(lambda s: '\n'.join(str(i) for i
                            in s.inventories))


class InventoryWindow(InventoryBase):
    """All 'inventory windows' subclass this, except the mouse."""
    def close(self):
        world = self.window_manager.world
        world.send_packet('close window', {'wid': self.wid})

    general = property(lambda s: s.inventories[-2],
                       lambda s, v: setattr(s.inventories, -2, v))

    ready = property(lambda s: s.inventories[-1],
                    lambda s, v: setattr(s.inventories, -1, v))


class Mouse(InventoryBase):
    name = "Mouse"

    def __init__(self, wid):
        super(Mouse, self).__init__(
            wid,
            GameContainerMouse(),
            )

    @property
    def slot(self):
        return self.inventories[0][-1]

    def take_stack(self, slot, func=None):
        """Assign slot to self, and disassociate it from its current window.
        This is a local action only, generally completed on success of a
        click transaction."""
        def take_stack_callback(success):
            if not success:
                self.window_manager.world.chat.send_message(
                    "Oops! click to take stack was rejected.")
                func(success)
                return
            if self.slot:
                log.msg("take_stack: virtual mouse already has full slot.")
                func(False)
                return
            inventory = self.window_manager.get(slot.wid, None)
            if not inventory:
                log.msg("Invalid window id: " + str(slot.wid))
            if inventory[slot.window_slot_number] is not slot:
                log.msg("slot: %s  inventory[slot.window_slot_number]: %s" %
                        (slot, inventory[slot.window_slot_number]))
                return False
            inventory[slot.window_slot_number] = None
            slot.wid = -1
            slot.window_slot_number = -1
            slot.gc_slot_number = None
            self[-1] = slot
            log.msg("self[-1]: %s  slot: %s" % (self[-1], slot))
            if func:
                func(True)
        # If the click succeeds, mirror the changes locally.
        self.click_slot(LEFT_CLICK, slot, take_stack_callback, False)

    def put_stack(self, inventory, func=None):
        if not self.slot:
            raise ValueError("Virtual mouse pointer has no item to put.")
        for i in xrange(len(inventory)):
            slot = inventory[i]
            if not slot:  # free slot exists
                break
        if slot:
            self.window_manager.world.chat.send_message(
                "No free slot to move stuff to")

        def put_stack_callback(success):
            if not success:
                self.window_manager.world.chat.send_message(
                    "Oops! click rejected..")
                func(False)
                return
            selfslot = self.slot
            self[-1] = None
            inventory[i] = selfslot
            if func:
                func(success)
        self.click_slot(LEFT_CLICK, slot, put_stack_callback, False)

    _send_packet = property(lambda self:
                            self.window_manager.world.send_packet)
    _transact = property(lambda self:
                         self.window_manager.world.protocol.transact)

    def click_slot(self, button, slot, func=lambda s: s, shift=False):
        """click_window(self, button, slot, func, shift) -> []
        Attempt to perform a click transaction with the server returning an
        empty list that will be updated when the response comes back from the
        server, appending the return value of func.  Func should be a method
        taking one parameter (True/False to indicate success/failure of the
        click transaction).

        Typical use, (for simple success checking):
            myfunc = lambda success: success   # just return the success value
            result = _click_window(func=myfunc, **other_args)
            while True:
                # result will have the return of myfunc appended when it runs
                if result:
                    if click.pop() == True:
                        <do successful click stuff you couldn't do in myfunc>
                    else:
                        <do failed click stuff you couldn't do in myfunc>
                yield  # or do other stuff while waiting for response from svr

        Arguments:
            button := The button clicked - LEFT_CLICK or RIGHT_CLICK
            slot := The number of the slot to click
            func := method which will be called with the Success value, and
                whose return value will be appended to the result list
            shift := Whether or not shift is held while clicking
        """
        result = []
        f = lambda success: result.append(func(success))
        token = self._transact(func=f)
        packet = {'button': button, 'shift': shift, 'token': token,
                  'wid': slot.wid, 'slot': slot.window_slot_number,
                  'slotdata': slot}
        log.msg('packet: ' + str(packet))
        log.msg('slot type: ' + str(type(slot)))
        log.msg('slotdata.size: ' + str(slot.size))
        self._send_packet('click window', packet)
        return result


class InventoryFull(InventoryWindow):
    name = "Full Inventory"

    def __init__(self, wid):
        super(InventoryFull, self).__init__(
            wid,
            GameContainerOutput(),
            GameContainerCraftingInputSmall(),
            GameContainerArmor(),
            GameContainerGeneralInv(),
            GameContainerReady()
            )
    output = property(lambda self: self.inventories[0])
    input = property(lambda self: self.inventories[1])
    armor = property(lambda self: self.inventories[2])


class InventoryCraftingTable(InventoryWindow):
    name = "Crafting Table Inventory"

    def __init__(self, window_manager, wid):
        super(InventoryCraftingTable, self).__init__(
            wid,
            GameContainerOutput(),
            GameContainerCraftingInput(),
            window_manager[WID_INVENTORY].player,
            window_manager[WID_INVENTORY].ready,
            )
        self.name = "Crafting Table"

    output = property(lambda self: self.inventories[0])
    input = property(lambda self: self.inventories[1])


class InventoryChest(InventoryWindow):
    name = "Chest Inventory"

    def __init__(self, window_manager, wid):
        super(InventoryChest, self).__init__(
            wid,
            GameContainerChest(),
            window_manager[WID_INVENTORY].player,
            window_manager[WID_INVENTORY].ready,
            )
        self.name = "Chest"
    contents = property(lambda self: self.inventories[0])


class InventoryLargeChest(InventoryWindow):
    name = "Large Chest Inventory"

    def __init__(self, window_manager, wid):
        super(InventoryLargeChest, self).__init__(
            wid,
            GameContainerChestLarge(),
            window_manager[WID_INVENTORY].player,
            window_manager[WID_INVENTORY].ready,
            )
        self.name = "Large Chest"
    contents = property(lambda self: self.inventories[0])


class InventoryFurnace(InventoryWindow):
    name = "Furnace Inventory"

    def __init__(self, window_manager, wid):
        super(InventoryFurnace, self).__init__(
            wid,
            GameContainerFurnaceItem(),
            GameContainerFurnaceFuel(),
            GameContainerOutput(),
            window_manager[WID_INVENTORY].player,
            window_manager[WID_INVENTORY].ready,
            )
        self.name = "Furnace"
    item = property(lambda self: self.inventories[0])
    fuel = property(lambda self: self.inventories[1])
    output = property(lambda self: self.inventories[2])


class InventoryDispenser(InventoryWindow):
    name = "Dispenser Inventory"

    def __init__(self, window_manager, wid):
        super(InventoryDispenser, self).__init__(
            wid,
            GameContainerDispenser(),
            window_manager[WID_INVENTORY].player,
            window_manager[WID_INVENTORY].ready,
            )
        self.name = "Dispenser"
    contents = property(lambda self: self.inventories[0])


class InventoryEnchantmentTable(InventoryWindow):
    name = "Enchantment Table Inventory"

    def __init__(self, window_manager, wid):
        super(InventoryEnchantmentTable, self).__init__(
            wid,
            GameContainerEnchantmentTable(),
            window_manager[WID_INVENTORY].player,
            window_manager[WID_INVENTORY].ready,
            )
        self.name = "Enchantment Table"
    item = property(lambda self: self.inventories[0])


#0 	Chest/Large chest
#1 	Workbench
#2 	Furnace
#3 	Dispenser
#4 	Enchantment table
#5 	Brewing Stand

class Inventories(dict):
    window_type_lookup = {
        TYPE_CHEST: InventoryChest,
        TYPE_CRAFTING: InventoryCraftingTable,
        TYPE_FURNACE: InventoryFurnace,
        TYPE_DISPENSER: InventoryDispenser,
        TYPE_ENCHANTMENT: InventoryEnchantmentTable,
    #    TYPE_BREWING: BrewingStand
        }

    def __init__(self, bot):
        # Inventory windows should have window manager base
        InventoryBase.window_manager = self
        super(Inventories, self).__init__()
        self.world = bot.world
        self.bot = bot
        self[WID_INVENTORY] = InventoryFull(WID_INVENTORY)
        self[WID_MOUSE] = Mouse(WID_MOUSE)

    def set_window_items(self, length, slotdata, window_id):
        try:
            window = self[window_id]
        except KeyError:
            msg = "Could not find window for window ID " + str(window_id)
            log.msg("ERROR: " + msg)
            return
        assert len(window) == length == len(slotdata)
        window[:] = [Item.from_slotdata(slot) for slot in slotdata]
        log.msg("set_window_items: " + str(window))

    def window_slot(self, slot, wid, slotdata):
        try:
            window = self[wid]
        except KeyError:
            msg = "Could not find window for window ID " + str(wid)
            log.msg("ERROR: " + msg)
            return
        window[slot] = Item.from_slotdata(slotdata)
        log.msg("Updated %s slot %s with %s" % (window.name, slot,
                                                str(window[slot])))

