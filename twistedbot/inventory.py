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
from Queue import Queue

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
        strings = [str(i[1]) + ' ' + i[0] for i in counter]
        if free:
            prefix = ("and " if strings else '')
            strings.append(prefix + "%d free slots" % free)
        return self.name + ": " + ', '.join(strings)


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


class GameContainerPlayerInv(GameContainer):
    name = "Player Inventory"

    def __init__(self, data=None):
        super(GameContainerPlayerInv, self).__init__(size=27, data=data)

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

    def __len__(self):
        return len(self.gc)

    def __str__(self):
        return str(self.gc)

    def __getattr__(self, name):
        if name in self.__dict__:
            return self.__dict__[name]
        return getattr(self.gc, name)

    def general_lookup(self, name):
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
        for item in self:
            if name.strip().lower() == item.name.lower():
                hits.append(item)
        if lenient and not hits:
            hits = self.general_lookup(name)
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

    def __init__(self, wid=None, *args):
        self.wid = int(wid)
        self.inventories = args
        self.inventories = [GCProxy(gc, self) for gc in args]

    def __len__(self):
        return sum(len(i) for i in self.inventories)

    def __getitem__(self, index):
        if type(index) == slice:
            if index.step:
                raise NotImplementedError("Window may not be step-sliced.")
            retval = []
            for i in xrange(index.start, index.stop):
                item = self[i]
                item.slot = i
                retval.append(item)
            return retval
        # Works for positive or negative numbers, during slicing or otherwise
        if index < 0:
            index = len(self) + index
        i = index
        for inv in self.inventories:
            if i < len(inv):
                item = inv.gc[i]
                if item is None:
                    item = NoItem()
                item.wid = self.wid
                item.slot = index
                item.sub_slot = index - inv.start
                return item
            else:
                i = i - len(inv)
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

    def general_lookup(self, name):
        hits = []
        for inv in self.inventories:
            hits.extend(inv.general_lookup(name))
        return hits

    def lookup(self, name, lenient=True):
        hits = []
        for inv in self.inventories:
            hits.extend(inv.lookup(name, lenient))
        return hits


class InventoryWindow(InventoryBase):
    """All 'inventory windows' subclass this, except the mouse."""
    player = property(lambda s: s.inventories[-2],
                      lambda s, v: setattr(s.inventories, -2, v))

    ready = property(lambda s: s.inventories[-1],
                    lambda s, v: setattr(s.inventories, -1, v))

    contents = property(lambda s: '\n'.join(str(i) for i
                            in s.inventories))


class Mouse(InventoryBase):
    name = "Mouse"
    clicking = Queue(maxsize=1)

    def __init__(self, window_manager, wid):
        super(Mouse, self).__init__(
            wid,
            GameContainerMouse(),
            )
        self.manager = window_manager
        self.clicking = False

    _send_packet = property(lambda s: s.manager.world.factory.send_packet)
    _transact = property(lambda self: self.manager.world.factory.transact)

    def __setitem__(self, index, value):
        if index is not -1:
            raise ValueError("Mouse only has slot -1, not slot " + str(index))
        super(Mouse, self).__setitem__(index, value)

    def __getitem__(self, index):
        if index is not -1:
            raise ValueError("Mouse only has slot -1, not slot " + str(index))
        super(Mouse, self).__getitem__(index)

    def _get_window(self, window_ref):
        """window_ref may be a window or an int reference to a window."""
        try:
            # If we were given a window ref, get the window.
            window = self.window_manager[int(window_ref)]
        except TypeError:
            pass
        int(window.wid)
        return window

    def click_window(self, button, window, slot, func, shift):
        """click_window(self, func, wid, slot, button, shift) -> []
        Attempt to perform a click transaction with the server returning an
        empty list that will be updated when the response comes back from the
        server, appending the return value of func.  Func should be a method
        taking one parameter (True/False to indicate success/failure of the
        click transaction).

        Typical use, (for func=lambda success: success):
            click = _click_window(*args)
            if click:
                if click.pop() == True:
                    <do successful click stuff>
                else:
                    <do failed click stuff>

        Arguments:
            func := method which will be called with the Success value, and
                whose return value will be appended to the result list
            window := Window or wid of the window to click
            slot := The number of the slot to click
            button := The button clicked - LEFT_CLICK or RIGHT_CLICK
            shift := Whether or not shift is held while clicking
        """
        result = []
        wid = self._get_window(window).wid
        if wid is None:
            raise ValueError("wid %s does not refer to an existing window."
                                % wid)
        f = lambda success: result.append(func(success))
        token = self._transact(func=f)
        packet = {'wid': wid, 'slot': slot, 'button': button, 'token': token,
                  'shift': shift}
        self._send_packet('click window', packet)
        return result

    def click_left(self, window, slot, func=lambda val: val, shift=False):
        """click_left(window, slot, func=lambda val: val, shift=False) -> []
        convenience method for click_window()
        window := window or wid to click
        slot := slot number to click
        func := method to call on success/failure. Defaults to lambda val:val
            which means that the result list will have True or False appended
            to it on success or failure.
        shift := whether or not shift is held

        ..see click_window for more details.
        """
        return self.click_window(func, window, slot, LEFT_CLICK, shift)

    def click_right(self, window, slot, func=lambda val: val, shift=False):
        """click_right(window, slot, func=lambda val: val, shift=False) -> []
        convenience method for click_window()
        window := window or wid to click
        slot := slot number to click
        func := method to call on success/failure. Defaults to lambda val:val
            which means that the result list will have True or False appended
            to it on success or failure.
        shift := whether or not shift is held

        ..see click_window for more details.
        """
        return self._click_window(func, window, slot, RIGHT_CLICK, shift)


class InventoryPlayer(InventoryWindow):
    name = "Full Inventory"

    def __init__(self, window_manager, wid):
        super(InventoryPlayer, self).__init__(
            wid,
            GameContainerOutput(),
            GameContainerCraftingInputSmall(),
            GameContainerArmor(),
            GameContainerPlayerInv(),
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
        super(Inventories, self).__init__()
        self.world = bot.world
        self.bot = bot
        self[WID_INVENTORY] = InventoryPlayer(self, WID_INVENTORY)
        self[WID_MOUSE] = Mouse(self, WID_MOUSE)

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

