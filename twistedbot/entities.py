

import logbot
from axisbox import AABB
from utils import Vector
from resources import namedata
import config

log = logbot.getlogger("ENTITIES")

# These aren't sent by the server, but are determined locally.
# It's mostly a means of assigning a name and info which is consistent with the
# existing structure.
ADDITIONAL_ETYPES = [
    namedata.EntityData(number=-1, name="Myself (%s)" % config.USERNAME,
                        width=config.PLAYER_DIAMETER,
                        height=config.PLAYER_HEIGHT),
    namedata.EntityData(number=-2, name="Player",
                        width=config.PLAYER_DIAMETER,
                        height=config.PLAYER_HEIGHT),
    namedata.EntityData(number=-3, name="Experience Orb",
                        width=0.1, height=0.1),
#    -1: namedata.EntityData(number=, name=, width=, height=),
    ]


class equipment(object):
    def __init__(self, container):
        self.c = container

#TODO: keep original Container object, and just reference it w/properties
class Entity(object):
    names = dict((e.number, e) for e in namedata.object_entities)
    # ADDITIONAL_ETYPES are defined purely internally.
    names.update(dict((e.number, e) for e in ADDITIONAL_ETYPES))
    world = None  # set on initialization of an 'Entities' instance

    def __init__(self, **kwargs):
        """Entity(eid=eid, etype=etype, x=x, y=y, z=z) -> Entity"""
        self.eid = kwargs["eid"]
        self.x = kwargs["x"]
        self.y = kwargs["y"]
        self.z = kwargs["z"]
        self.velocity = None
        log.msg(str(self))

    equipment = property(lambda s: s._inv if hasattr(s, '_inv') else False,
                         lambda s, v: setattr(s, '_inv', v))

    is_bot = property(lambda s: s._bot if hasattr(s, '_bot') else False,
                      lambda s, v: setattr(s, '_bot', v))

    is_manager = property(lambda s: s._mgr if hasattr(s, '_mgr') else False,
                          lambda s, v: setattr(s, '_mgr', v))

    is_commander = property(lambda s: s._cmd if hasattr(s, '_cmd') else False,
                            lambda s, v: setattr(s, '_cmd', v))

    @property
    def name(self):
        return self._name()

    def _name(self):
        try:
            name = self.names[self.etype].name
        except KeyError:
            name = "Unknown Entity Type ({})".format(self.etype)
        return name

    @property
    def grid_position(self):
        x = self.x / 32
        y = self.y / 32
        z = self.z / 32
        return Vector(x, y, z)

    @property
    def position(self):
        return Vector(self.x / 32.0, self.y / 32.0, self.z / 32.0)

    def distance(self, other):
        """Return the distance between two entities"""
        return self.position.distance(other.position)

    def __str__(self):
        equipment = ', ' + str(self.equipment) if self.equipment else ''
        equipment = ', with ' + equipment if equipment else equipment
        return "{} at {}{}".format(self.name, self.position, equipment)


class EntityBot(Entity):
    def __init__(self, **kwargs):
        """EntityBot(eid=eid, x=x, y=y, z=z) -> Entity
        etype doesn't matter, we shouldn't be sending/receiving any data
        to/from the server about this entity anyways -- the player(bot) is
        handled through other means (and a different packet set).
        If we make the interface match (at least partially), it will be a
        inaccurate of the underlying structure -- ..so, why does this exist
        at all, unless we mirror the entity api to in some way or other affect
        the player..?
        """
        self.etype = -1
        super(EntityBot, self).__init__(**kwargs)
        self.is_bot = True
        log.msg(str(self))

class EntityLiving(Entity):
    def __init__(self, **kwargs):
        super(EntityLiving, self).__init__(**kwargs)
        self.yaw = kwargs["yaw"]
        self.pitch = kwargs["pitch"]

    @property
    def orientation(self):
        return (self.yaw, self.pitch)

    @property
    def location(self):
        x, y, z = self.position
        yaw, pitch = self.orientation
        return (x, y, z, yaw, pitch)


class EntityMob(EntityLiving):
    names = dict((e.number, e) for e in namedata.mob_entities)
    def __init__(self, **kwargs):
        # This must come before class init, or log message will fail.
        self.etype = kwargs['etype']
        super(EntityMob, self).__init__(**kwargs)
        self.head_yaw = kwargs["yaw"]
        self.status = None
        #TODO assign mob type according to the etype and metadata


class EntityPlayer(EntityLiving):
    last_known_position = {}
    def __init__(self, **kwargs):
        # this is sorta bad form, but creation of 'username' must come before
        # superclass initialization calls, to allow the 'name' property to
        # function properly.
        self.username = kwargs["username"]
        self.etype = -3
        super(EntityPlayer, self).__init__(**kwargs)
        self.world = kwargs["world"]
        self.held_item = kwargs["held_item"]
        # Player's looking direction
        self.yaw = kwargs["yaw"]
        self.pitch = kwargs["pitch"]
#TODO: remove this
        log.msg(str(self))

        if self.world.commander.name == self.username:
            self.world.commander.eid = self.eid
        if self.is_commander:
            log.msg("Found commander: " + self.username)
            self.world.chat.send_message("Hello, commander "+self.username)
        elif self.is_manager:
            log.msg("Found manager: " + self.username)
            self.world.chat.send_message("Oh, hai, "+self.username)
        else:
            log.msg("Found player: " + self.username)

    def __del__(self):
        if not hasattr(self, 'world'):
            log.msg("%s object had no world attribute." % str(type(self)))
            return
        self.last_known_position[self.username] = self.position
        if self.is_commander:
            if self.world.commander.eid == self.eid:
                log.msg("Lost commander (%s)" % self.username)
                self.world.chat.send_message("Don't forget me, "+self.username)
                self.world.commander.eid = None
            else:
                log.msg("Warning, destroyed a commander entity, but "
                        "eid does not match world.commander.eid")
        elif self.is_manager:
            if self.world.entities.players.get(self.username) == self.eid:
                log.msg("Lost manager '%s'" % self.username)
                self.world.chat.send_message("See you 'round, "+self.username)
            else:
                log.msg("Warning, destroyed a manager player entity, but "
                        "eid does not match the one in entities.players")
        else:
            log.msg("Player '%s' logged off." % self.username)

    def _name(self):
        return 'Player "%s"' % self.username

    is_manager = property(lambda s: s.username in s.world.managers)

    is_commander = property(lambda s: s.username == s.world.commander.name)


class EntityVehicle(Entity):
    def __init__(self, **kwargs):
        self.etype = kwargs["etype"]
        super(EntityVehicle, self).__init__(**kwargs)
        self.thrower = kwargs["object_data"]
        if self.thrower > 0:
            self.vel_x = kwargs["velocity"]["x"]
            self.vel_y = kwargs["velocity"]["y"]
            self.vel_z = kwargs["velocity"]["z"]
        #TODO assign vehicle type according to the etype and metadata


class EntityExperienceOrb(Entity):
    def __init__(self, **kwargs):
        self.etype = -3
        super(EntityExperienceOrb, self).__init__(**kwargs)
        self.quantity = kwargs["count"]


class EntityDroppedItem(Entity):
    def __init__(self, **kwargs):
        super(EntityDroppedItem, self).__init__(**kwargs)
        self.nbt = kwargs["slotdata"]


class EntityPainting(Entity):
    def __init__(self, **kwargs):
        super(EntityPainting, self).__init__(**kwargs)
        self.title = kwargs["title"]


class Entities(dict):
    def __init__(self, dimension):
        """Contains entities keyed by eid, and has various operations which
        can be done on an entity."""
        super(Entities, self).__init__()
        self.dimension = dimension
        self.world = dimension.world
        self.players = {}

    def __setitem__(self, k, v):
        if k is None:
            raise ValueError("Entity man not have an eid of None")
        return super(Entities, self).__setitem__(k, v)

    def get_entity(self, eid):
        return self.get(eid, None)

    def maybe_commander(self, entity):
        """Note the commander's last position, presumably usable somewhere."""
        if self.world.commander.eid != entity.eid:
            return
        gpos = entity.grid_position
        block = self.dimension.grid.standing_on_block(AABB.from_player_coords(entity.position))
        if block is None:
            return
        if self.world.commander.last_block is not None and self.world.commander.last_block == block:
            return
        self.world.commander.last_block = block
        #TODO put some nice debug code here
        self.world.commander.last_position = gpos

    def entityupdate(fn):
        def f(self, *args, **kwargs):
            eid = args[0]
            entity = self.get_entity(eid)
            if entity is None:
                # received entity update packet for entity
                # that was not initialized with new_*, this should not happen
                log.msg("do not have entity id %d registered" % eid)
                return
            if entity.is_bot:
                #log.msg("Server is changing my %s with %s %s" % (fn.__name__, args, kwargs))
                pass
            fn(self, entity, *args[1:], **kwargs)
            self.maybe_commander(entity)
        return f

    def on_new_player(self, **kwargs):
        username, eid = kwargs['username'], kwargs['eid']
        self[eid] = EntityPlayer(world=self.world, **kwargs)
        self.players[username] = eid

    def on_new_dropped_item(self, **kwargs):
        self[kwargs["eid"]] = EntityDroppedItem(**kwargs)

    def on_new_vehicle(self, **kwargs):
        self[kwargs["eid"]] = EntityVehicle(**kwargs)

    def on_new_mob(self, **kwargs):
        self[kwargs["eid"]] = EntityMob(**kwargs)

    def on_new_painting(self, **kwargs):
        self[kwargs["eid"]] = EntityPainting(**kwargs)

    def on_new_experience_orb(self, **kwargs):
        self[kwargs["eid"]] = EntityExperienceOrb(**kwargs)

    def on_destroy(self, eids):
        for eid in eids:
            entity = self.get_entity(eid)
            if entity:
                del self[eid]
                if isinstance(entity, EntityPlayer):
                    self.players.pop(entity.username)
            else:
                log.msg('Cannot destroy entity %d: it is not registered' % eid)

    @entityupdate
    def on_move(self, entity, dx, dy, dz):
        entity.x += dx
        entity.y += dy
        entity.z += dz

    @entityupdate
    def on_look(self, entity, yaw, pitch):
        entity.yaw = yaw
        entity.pitch = pitch

    @entityupdate
    def on_head_look(self, entity, yaw):
        entity.yaw = yaw

    @entityupdate
    def on_move_look(self, entity, dx, dy, dz, yaw, pitch):
        entity.x += dx
        entity.y += dy
        entity.z += dz
        entity.yaw = yaw
        entity.pitch = pitch

    @entityupdate
    def on_teleport(self, entity, x, y, z, yaw, pitch):
        entity.x = x
        entity.y = y
        entity.z = z
        entity.yaw = yaw
        entity.pitch = pitch

    @entityupdate
    def on_velocity(self, entity, dx, dy, dz):
        entity.velocity = (dx, dy, dz)

    @entityupdate
    def on_status(self, entity, status):
        entity.status = status

    @entityupdate
    def on_attach(self, entity, vehicle):
        pass

    @entityupdate
    def on_metadata(self, entity, metadata):
        pass
