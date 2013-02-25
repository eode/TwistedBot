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
    # FooInv, PlayerInv, and HeldInv, and a FooInv has four slots, then
    w = FooWindow()
    w[0] = 'foo'   # set first item in FooInv
    w[3] = 'bar'   # set last item in FooInv
    w[4] = 'baz'   # set the first item in PlayerInv
Similarly, if you set past the last value of PlayerInv, it will roll over to
HeldInv, and finally give an IndexError.

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


#from items import Item


class _Inventory(list):
    def __init__(self, size, data=None):
        if size < 1:
            raise ValueError("Size less than 1?")
        if data is not None:
            assert len(data) == size
        else:
            data = [None for _ in xrange(size)]
        super(_Inventory, self).__init__(data)

    def append(self, item):
        raise NotImplementedError("Append not allowed.")

    def extend(self, item):
        raise NotImplementedError("Extend not allowed.")

    def __repr__(self):
        return "%s(size=%d, data=%s)" % (type(self).__name__, len(self),
                                        super(_Inventory, self).__repr__())

    def __str__(self):
        return "Inventory: " + ', '.join(str(i) for i in self)


class InventoryArmor(_Inventory):
    def __init__(self, data=None):
        super(InventoryArmor, self).__init__(size=4, data=data)

    def __repr__(self):
        return "%s(data=%s)" % (type(self).__name__,
                                super(type(self), self).__repr__())

    def __str__(self):
        return "Armor: %s(head), %s(chest), %s(legs), %s(feet)" % self
    head = property(lambda s: s[0], lambda s, v: setattr(s, 0, v),
                    lambda s: setattr(s, 0, None))

    chest = property(lambda s: s[1], lambda s, v: setattr(s, 1, v),
                     lambda s: setattr(s, 1, None))

    legs = property(lambda s: s[2], lambda s, v: setattr(s, 2, v),
                    lambda s: setattr(s, 2, None))

    feet = property(lambda s: s[3], lambda s, v: setattr(s, 3, v),
                    lambda s: setattr(s, 3, None))


class InventoryChest(_Inventory):
    def __init__(self, data=None):
        super(InventoryChest, self).__init__(size=27, data=data)

    def __repr__(self):
        return "%s(data=%s)" % (type(self).__name__,
                                super(type(self), self).__repr__())


class InventoryChestLarge(_Inventory):
    def __init__(self, data=None):
        super(InventoryChestLarge, self).__init__(size=54, data=data)

    def __repr__(self):
        return "%s(data=%s)" % (type(self).__name__,
                                super(type(self), self).__repr__())


class InventoryCraftingInput(_Inventory):
    def __init__(self, data=None):
        super(InventoryCraftingInput, self).__init__(size=9, data=data)

    def __repr__(self):
        return "%s(data=%s)" % (type(self).__name__,
                                super(type(self), self).__repr__())


class InventoryCraftingInputSmall(_Inventory):
    def __init__(self, data=None):
        super(InventoryCraftingInputSmall, self).__init__(size=4, data=data)

    def __repr__(self):
        return "%s(data=%s)" % (type(self).__name__,
                                super(type(self), self).__repr__())


class InventoryDispenser(_Inventory):
    def __init__(self, data=None):
        super(InventoryDispenser, self).__init__(size=9, data=data)

    def __repr__(self):
        return "%s(data=%s)" % (type(self).__name__,
                                super(type(self), self).__repr__())


class InventoryEnchantmentTable(_Inventory):
    def __init__(self, data=None):
        super(InventoryEnchantmentTable, self).__init__(size=9, data=data)

    def __repr__(self):
        return "%s(data=%s)" % (type(self).__name__,
                                super(type(self), self).__repr__())


class InventoryEntityEquipment(_Inventory):
    """This is the class for the (generally visible) entity equipment for all
    mobs and players other than The Player/the bot."""
    def __init__(self, data=None):
        super(InventoryEntityEquipment, self).__init__(size=4, data=data)

    def __repr__(self):
        return "%s(data=%s)" % (type(self).__name__,
                                super(type(self), self).__repr__())

    held = property(lambda s: s[0], lambda s, v: setattr(s, 1, v),
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
        tags = ["Held: %s", "Head: %s", "Chest: %s", "Legs: %s", "Feet: %s"]
        items = (tags[i] % self[i] for i in xrange(len(self)) if self[i])
        return ', '.join(items)


class InventoryFurnaceFuel(_Inventory):
    def __init__(self, data=None):
        super(InventoryFurnaceFuel, self).__init__(size=1, data=data)

    def __repr__(self):
        return "%s(data=%s)" % (type(self).__name__,
                                super(type(self), self).__repr__())


class InventoryFurnaceItem(_Inventory):
    def __init__(self, data=None):
        super(InventoryFurnaceItem, self).__init__(size=1, data=data)

    def __repr__(self):
        return "%s(data=%s)" % (type(self).__name__,
                                super(type(self), self).__repr__())


class InventoryHeld(_Inventory):
    def __init__(self, data=None):
        super(InventoryHeld, self).__init__(size=9, data=data)

    def __repr__(self):
        return "%s(data=%s)" % (type(self).__name__,
                                super(type(self), self).__repr__())


class InventoryMouse(_Inventory):
    def __init__(self, data=None):
        super(InventoryMouse, self).__init__(size=1, data=data)

    def __repr__(self):
        return "%s(data=%s)" % (type(self).__name__,
                                super(type(self), self).__repr__())


class InventoryOutput(_Inventory):
    def __init__(self, data=None):
        super(InventoryOutput, self).__init__(size=1, data=data)

    def __repr__(self):
        return "%s(data=%s)" % (type(self).__name__,
                                super(type(self), self).__repr__())


class InventoryPlayer(_Inventory):
    def __init__(self, data=None):
        super(InventoryPlayer, self).__init__(size=27, data=data)

    def __repr__(self):
        return "%s(data=%s)" % (type(self).__name__,
                                super(type(self), self).__repr__())


class Window(object):
    """Combine various Inventory objects into one (fake) window, which we
    'open' when looking at player inventory, chest inventory, etc."""

    def __init__(self, *args):
        self.inventories = args

    def __len__(self):
        return sum(len(i) for i in self.inventories)

    def __getitem__(self, index):
        if type(index) == slice:
            if index.step:
                raise NotImplementedError("Window may not be step-sliced.")
            retval = []
            for i in xrange(index.start, index.stop):
                retval.append(self[i])
            return retval
        if index < 0:
            inventories = reversed(self.inventories)
            neg = -1
            decrement = 1
        else:
            inventories = self.inventories
            neg = 1
            decrement = 0
        for inv in inventories:
            if abs(index) - decrement < len(inv):
                return inv[index]
            else:
                index = neg * (abs(index) - len(inv))
        raise IndexError("Index out of range.")

    def __setitem__(self, index, value):
        if type(index) == slice:
            if index.step:
                raise NotImplementedError("Window may not be step-sliced.")
            x = 0
            for i in xrange(index.start, index.stop):
                self[i] = value[x]
                x += 1
            return
        if index < 0:
            inventories = reversed(self.inventories)
            neg = -1
            decrement = 1
        else:
            inventories = self.inventories
            neg = 1
            decrement = 0
        for inv in inventories:
            if abs(index) - decrement < len(inv):
                inv[index] = value
                return
            else:
                index = neg * (abs(index) - len(inv))
        raise IndexError("Index out of range")

    inv = property(lambda s: s.inventories[-2],
                   lambda s, v: setattr(s.inventories, -2, v))

    held = property(lambda s: s.inventories[-1],
                    lambda s, v: setattr(s.inventories, -1, v))


class Inventory(Window):
    def __init__(self, bot):
        super(Inventory, self).__init__(
            InventoryOutput(),
            InventoryCraftingInputSmall(),
            bot.armor,
            bot.inventory,
            bot.held_items,
            )


class CraftingTable(Window):
    def __init__(self, bot):
        super(CraftingTable, self).__init__(
            InventoryOutput(),
            InventoryCraftingInput(),
            bot.inventory,
            bot.held_items,
            )


class Chest(Window):
    def __init__(self, bot):
        super(Chest, self).__init__(
            InventoryChest(),
            bot.inventory,
            bot.held_items,
            )


class LargeChest(Window):
    def __init__(self, bot):
        super(LargeChest, self).__init__(
            InventoryChestLarge(),
            bot.inventory,
            bot.held_items,
            )


class Furnace(Window):
    def __init__(self, bot):
        super(Furnace, self).__init__(
            InventoryFurnaceItem(),
            InventoryFurnaceFuel(),
            bot.inventory,
            bot.held_items,
            )


class Dispenser(Window):
    def __init__(self, bot):
        super(Dispenser, self).__init__(
            InventoryDispenser(),
            bot.inventory,
            bot.held_items,
            )


class EnchantmentTable(Window):
    def __init__(self, bot):
        super(EnchantmentTable, self).__init__(
            InventoryEnchantmentTable(),
            bot.inventory,
            bot.held_items,
            )


class Mouse(Window):
    def __init__(self, bot):
        super(Mouse, self).__init__(
            InventoryMouse(),
            bot.inventory,
            bot.held_items,
            )

class Windows(dict):
    pass


