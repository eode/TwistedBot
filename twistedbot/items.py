# -*- coding: utf-8 -*-

#import sys
#import inspect

from resources import namedata
#import blocks
import logbot

try:
    from cStringIO import StringIO
except:
    from StringIO import StringIO


log = logbot.getlogger("ITEMS")


class Slot(object):
    # Slotdata
    id = -1
    count = None
    damage = None
    #size = <auto-calculated>
    data = None
    # referring-container info.  This is needed by the Mouse 'window' to
    # know which window to 'click' on and where.
    wid = None
    gc_slot_number = None
    window_slot_number = None

    names = dict((i.number, i.name) for i in namedata.block_items)
    names.update(dict((i.number, i.name) for i in namedata.nonblock_items))

    @property
    def size(self):
        if self.data is None:
            return -1
        else:
            sio = StringIO()
            self.data.save(sio, compression=self.data.Compression.GZIP)
            return sio.tell()

    @property
    def name(self):
        if self.id == -1:
            n = "<nothing>"
        else:
#            log.msg('self.id: ' + str(self.id))
            n = self.names.get(self.id, "Unknown Item!")
        return n

#    name = property(lambda self: "nothing" if self.id is None else \
#                                 self.names.get(self.id, "Unknown Item!"))


class NoItem(Slot):
    """This is returned by inventory windows when a window slot contains None.
    It compares as nonexistent in "if noitem_instance: .." statements, but it
    provides a namespace in which the 'slot' attribute can be set.
    """
    def __nonzero__(self):
        return False

    def __str__(self):
        return "<empty>"

    def __repr__(self):
        return "NoItem()"


class Item(Slot):
    def __init__(self, id, count, size,  damage, data):
        """Item(**slotdata) -> Item object
        slotdata must not be 'empty' -- empty slots are represented with None.
        For shorthand when dealing directly with slotdata, use
        Item.from_slotdata(slotdata)
        ..which will return either an Item or None as is appropriate.
        """
        super(Item, self).__init__()
        self.id = id
        self.count = count
        #self.size = size
        self.damage = damage
        self.data = data

    def __str__(self):
        name = self.name
        if self.count > 1:
            name = ("%s " % self.count) + name
        if self.data and 'enchanted' not in name.lower():
            name = name + " (probably enchanted or something)"
        return name

    def __nonzero__(self):
        return True

    def getitem(self, key):
        return getattr(self, key)

    @classmethod
    def from_slotdata(cls, slotdata):
        """Return an Item object (or None, if slot is empty) from the
        provided slotdata. None is returned when the slotdata says the slot
        is empty (e.g., the item id is -1).
        """
        if slotdata.id == -1:
            return None
        else:
            return cls(**slotdata)


##This mapping of items was unused, and I'm not certain it was current.

#class NonStackable(Item):
#    stackable = 1
#
#
#class Stackable(Item):
#    stackable = 64
#
#
#class IronShovel(NonStackable):
#    number = 256
#    name = "Iron Shovel"
#
#
#class IronPickAxe(NonStackable):
#    number = 257
#    name = "Iron Pickaxe"
#
#
#class IronAxe(NonStackable):
#    number = 258
#    name = "Iron Axe"
#
#
#class FlintAndSteel(NonStackable):
#    number = 259
#    name = "Flint and Steel"
#
#
#class RedApple(Stackable):
#    number = 260
#    name = "Red Apple"
#
#
#class Bow(NonStackable):
#    number = 261
#    name = "Bow"
#
#
#class Arrow(Stackable):
#    number = 262
#    name = "Arrow"
#
#
#class Coal(Stackable):
#    number = 263
#    name = "Coal"
#
#
#class Diamond(Stackable):
#    number = 264
#    name = "Diamond"
#
#
#class IronIngot(Stackable):
#    number = 265
#    name = "Iron Ingot"
#
#
#class GoldIngot(Stackable):
#    number = 266
#    name = "Gold Ingot"
#
#
#class GoldIngot(Stackable):
#    number = 266
#    name = "Gold Ingot"
#
#
#class IronSword(NonStackable):
#    number = 267
#    name = "Iron Sword"
#
#
#class WoodenSword(NonStackable):
#    number = 268
#    name = "Wooden Sword"
#
#
#class WoodenShovel(NonStackable):
#    number = 269
#    name = "Wooden Showel"
#
#
#class WoodenPickaxe(NonStackable):
#    number = 270
#    name = "Wooden Pickaxe"
#
#
#class WoodenAxe(NonStackable):
#    number = 271
#    name = "Wooden Axe"
#
#
#class StoneSword(NonStackable):
#    number = 272
#    name = "Stone Sword"
#
#
#class StoneShovel(NonStackable):
#    number = 273
#    name = "Stone Shovel"
#
#
#class StonePickaxe(NonStackable):
#    number = 274
#    name = "Stone Pickaxe"
#
#
#class StoneAxe(NonStackable):
#    number = 275
#    name = "Stone Axe"
#
#
#class DiamiondSword(NonStackable):
#    number = 276
#    name = "Diamond Sword"
#
#
#class String(Stackable):
#    number = 287
#    name = "String"
#
#
#class Sign(NonStackable):
#    number = 323
#    name = "Sign"
#
#
#class WoodenDoor(NonStackable):
#    number = 324
#    name = "Wooden Door"
#
#
#class IronDoor(NonStackable):
#    number = 330
#    name = "Iron Door"
#
#
#class RedstoneDust(Stackable):
#    number = 331
#    name = "Redstone Dust"
#
#
#class SugarCane(Stackable):
#    number = 338
#    name = "Sugar Cane"
#
#
#class Cake(NonStackable):
#    number = 354
#    name = "Cake"
#
#
#class Bed(NonStackable):
#    number = 355
#    name = "Bed"
#
#
#class RedstoneRepeater(Stackable):
#    number = 356
#    name = "Redstone Repeater"
#
#
#class NetherWart(Stackable):
#    number = 372
#    name = "Nether Wart"
#
#
#class BrewingStand(Stackable):
#    number = 379
#    name = "Brewing Stand"
#
#
#item_map = blocks.block_map[:]
#
#
#def prepare():
#    clsmembers = inspect.getmembers(sys.modules[__name__], inspect.isclass)
#    for _, cl in clsmembers:
#        try:
#            item_map[cl.number] = cl
#        except:
#            pass
#
#prepare()
