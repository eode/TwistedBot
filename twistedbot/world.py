

from collections import defaultdict
from datetime import datetime
from Queue import Empty, Full

import logbot
import utils
import config
from entities import Entities
from grid import Grid
from statistics import Statistics
from chat import Chat
from botentity import BotEntity
from signwaypoints import SignWayPoints


log = logbot.getlogger("WORLD")


class Dimension(object):

    def __init__(self, world):
        self.world = world
        self.entities = Entities(self)
        self.grid = Grid(self)
        self.sign_waypoints = SignWayPoints(self)


class DummyQueue(object):
    close = lambda s: None
    empty = lambda s: True
    full = lambda s: True
    get = close
    put = lambda s, v: None
    put_nowait = put

    def get_nowait(self):
        raise Empty()


class World(object):
    def __init__(self, host=None, port=None,
                 commander_name=None, bot_name=None,
                 to_bot_q=None, to_gui_q=None):
        self._to_bot = DummyQueue() if to_bot_q is None else to_bot_q
        self._to_gui = DummyQueue() if to_gui_q is None else to_gui_q
        self.to_gui("name", bot_name)
        self.server_host = host
        self.server_port = port
        self.commander = Commander(commander_name)
        # Users who can give the bot non-administrative commands
        self.managers = {}     # {'name1': eid} (or {'name1': None} if offline)
        self.chat = Chat(self)
        self.bot = BotEntity(self, bot_name)
        self.stats = Statistics()
        self.game_ticks = 0
        self.connected = False
        self.logged_in = False
        self.protocol = None
        self.factory = None
        self.entities = None
        self.grid = None
        self.sign_waypoints = None
        self.dimension = None
        self.dimensions = [Dimension(self), Dimension(self), Dimension(self)]
        self.spawn_position = None
        self.game_mode = None
        self.difficulty = None
        self.players = defaultdict(int)
        self.last_tick_time = datetime.now()
        self.period_time_estimation = config.TIME_STEP
        utils.do_later(config.TIME_STEP, self.tick)
        self.shutdown_reason = ''

    def predict_next_ticktime(self, tick_start):
        tick_end = datetime.now()
        # time this step took
        d_run = (tick_end - tick_start).total_seconds()
        # decreased by computation in tick
        t = config.TIME_STEP - d_run
        # real tick period
        d_iter = (tick_start - self.last_tick_time).total_seconds()
        # diff from scheduled by
        r_over = d_iter - self.period_time_estimation
        t -= r_over
        t = max(0, t)  # cannot delay into past
        self.period_time_estimation = t + d_run
        self.last_tick_time = tick_start
        return t

    def tick(self):
        tick_start = datetime.now()
        if self.logged_in:
            self.bot.tick()
            self.chat.tick()
            self.every_n_ticks()
        utils.do_later(self.predict_next_ticktime(tick_start), self.tick)

    def every_n_ticks(self, n=100):
        self.game_ticks += 1

    def on_connection_lost(self):
        self.connected = False
        self.logged_in = False
        self.protocol = None
        self.bot.on_connection_lost()

    def connection_made(self):
        self.connected = True

    def on_shutdown(self):
        reason = self.shutdown_reason
        reason = reason if reason else "(no reason given)"
        log.msg("Shutting Down: " + reason)
        self.to_gui('shutting down', reason)
        self._to_gui.close()
        self._to_bot.close()
        self.factory.log_connection_lost = False

    def send_packet(self, name, payload):
        if self.protocol is not None:
            self.protocol.send_packet(name, payload)
        else:
            log.msg("Trying to send %s while disconnected" % name)

    def dimension_change(self, dimension):
        dim = dimension + 1  # to index from 0
        d = self.dimensions[dim]
        self.dimension = d
        self.entities, self.grid = d.entities, d.grid
        self.sign_waypoints = d.sign_waypoints
        if not self.entities.has_entity(self.bot.eid):
            self.entities.new_bot(self.bot.eid)

    def on_login(self, bot_eid=None, game_mode=None, dimension=None,
                 difficulty=None):
        self.bot.eid = bot_eid
        self.logged_in = True
        self.dimension_change(dimension)
        self.game_mode = game_mode
        self.difficulty = difficulty

    def on_spawn_position(self, x, y, z):
        self.spawn_position = (x, y, z)
        self.bot.spawn_point_received = True

    def on_respawn(self, game_mode=None, dimension=None, difficulty=None):
        self.dimension_change(dimension)
        self.game_mode = game_mode
        self.difficulty = difficulty
        self.bot.location_received = False
        self.bot.spawn_point_received = False
        self.bot.i_am_dead = False

    def on_time_update(self, age_of_world=None, daytime=None):
        self.age_of_world = age_of_world
        self.daytime = daytime

    def to_bot(self):
        """Convenience method for getting data from the _to_bot queue.
        Returns data if there is data, else returns None
        :rtype: Message
        """
        return None if self._to_bot.empty() else self._to_bot.get()

    def to_gui(self, name, data):
        """world.to_gui('foo', 'stuff') -> send Message 'foo' w/data to gui.
        This is just a convenience method to turn:
            world._to_gui.put(Message('foo', data))
            into:
            world.to_gui('foo', data)
        :rtype: Message
        """
        self._to_gui.put(utils.Message(name, data))


class Commander(object):
    def __init__(self, name):
        self.name = name
        self.eid = None
        self.last_position = None
        self.last_block = None

    @property
    def in_game(self):
        return self.eid is not None
