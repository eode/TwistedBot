
from collections import deque

from twisted.internet.task import cooperate
from twisted.internet.defer import inlineCallbacks, returnValue

import config
import utils
import logbot
import fops
from pathfinding import AStar
from axisbox import AABB
from gridspace import GridSpace
from time import time

debug = True
log = logbot.getlogger("BEHAVIOUR_TREE")


class Status(object):
    names = {20: 'success', 25: 'partial success', 30: 'failure',
             40: 'running', 50: 'suspended'}
    success = 20
    partial_success = 25
    failure = 30
    running = 40
    suspended = 50


class Priorities(object):
    """When goals are set, the priority determines whether or not the goal
    may supplant the current behaviour.
    There are two reserved priorities -- 'sub_behaviour' and 'absolute_top'.
    All values must be below the absolute_top.
    Since sub_behaviours are supplanted by everything, they will be erased
    when a new goal is set.  Then, when the bot goes back to the old goal,
    he will restart it from the 'beginning', i.e., resetting the pathfinding,
    for example, because he may be in a new location.
    """
    # Generally, keep this one low.  Use only with short, non-repeatable
    # behaviours.
    sub_behaviour = 10
    idle = 20
    user_command = 30
    survival = 40
    absolute_top = 101  # don't use absolute_top priority in a behaviour.


class BehaviourTree(object):
    def __init__(self, world, bot):
        self.world = world
        self.bot = bot
        self.bqueue = deque()
        self.running = False
        self.user_command = None

    @property
    def current_behaviour(self):
        return self.bqueue[-1] if self.bqueue else None

    @property
    def current_goal(self):
        for b in reversed(self.bqueue):
            if b.priority > Priorities.sub_behaviour:
                return b
        return None

    @property
    def preferred_goal(self):
        fpriority = lambda b: b.priority  # return the priority of b.
        return max(self.bqueue, key=fpriority) if self.bqueue else None

    def recheck_goal(self):
        """Use to evaluate/interrupt behaviours -- perhaps each behaviour can
        have interrupt evaluation methods..  ..I'm guessing at the original
        purpose of this.."""
        if  not self.current_goal:
            return
        if self.bqueue[-1].evaluate():
            self.bqueue[-1].cancel()
        return

    def select_goal(self):
        """
        Select which (new) goal the bot should be going for.  I'd like to
        change this to an a* network graph, but for now..

        Prefer survival over player command,
        Prefer player command over idle behaviour,
        Prefer idle behaviour over doing nothing.
        """
        idle = self.get_idle_behaviour()
        player_command = self.get_player_command_behaviour()
        survival = self.get_survival_behaviour()

        command = player_command if player_command else idle
        command = survival if survival else command
        return command

    def get_idle_behaviour(self):
        if self.bqueue:  # we're already doing something.
            return None
        return (LookAtPlayerBehaviour, {'priority': Priorities.idle})

    def get_player_command_behaviour(self):
        user_command = self.user_command
        if user_command:
            user_command[1]['priority'] = Priorities.user_command
            self.user_command = None
            return user_command

    def get_survival_behaviour(self):
        """Check if a survival behaviour needs to be inserted into the queue.
        """
        # behaviour = (SomeBehaviour, {'priority': Priorities.survival})
        return None

    def tick(self, cancel=None):
        if cancel is not None:
            log.msg("Cancelling at value " + str(cancel))
            self.cancel_running(cancel)
        if not self.bqueue:
            self.select_goal()
        if self.running:
            return
        self.recheck_goal()
        self.run()

    @inlineCallbacks
    def run(self):
        self.running = True
        try:
            while 1:
                yield utils.reactor_break()
                self.check_new_command()
                g = self.current_behaviour
                if g.status == Status.running:
                    yield g.tick()
                self.bot.bot_object.hold_position_flag = g.hold_position_flag
#                if g.cancelled:
#                    break
                if g.status == Status.running:
                    break
                elif g.status == Status.suspended:
                    continue
                else:
                    self.leaf_to_parent()
        except:
            if self.current_behaviour:
                msg = "I want to try %s, but my brain hurts."
                msg = msg % self.current_behaviour.name
            else:
                msg = "I'm not even doing anything and my brain hurts."
            log.msg(msg)
            log.err()
            self.world.chat.send_message(msg)
            self.cancel_running(Priorities.absolute_top)
        self.running = False

    def leaf_to_parent(self):
        """Execute a leaf, and return values to its parent.
        The special variable "to_parent" is read from the leaf and sent to the
        parent.from_child() as kwargs if it is present."""
        leaf = self.bqueue.pop()
        status = Status.names[leaf.status]
        log.msg('"%s" returning %s' % (str(leaf.name), status))
        if self.bqueue:
            kwargs = leaf.to_parent if hasattr(leaf, 'to_parent') else {}
            self.current_behaviour.from_child(leaf.status, **kwargs)
        else:
            behaviour, kwargs = self.select_goal()
            self.bqueue.append(behaviour(manager=self, parent=None, **kwargs))

    def cancel_running(self, priority):
        """Cancel commands until:
          - a command with the given priority is found: cancel that, and return
          - a command of greater priority is found: return
          - all commands are canceled
        """
        log.msg("cancel_running")
        for behaviour in reversed(self.bqueue):
            if behaviour.priority < priority:
                log.msg("cancelling "+behaviour.name)
                behaviour.cancel()
            elif behaviour.priority == priority:
                log.msg("last cancel: "+behaviour.name)
                behaviour.cancel()
                return
            else:
                return

    def check_new_command(self):
        """Check for a new command, and execute it (or not) based on the
        priority of that command and those in-queue."""
        new = self.select_goal()
        if new is not None:
            behaviour, kwargs = new
            new_goal = behaviour(manager=self, parent=None, **kwargs)
            current_goal = self.current_goal
            if current_goal is not None:
                if current_goal.priority == new_goal.priority:
                    self.cancel_running(current_goal.priority)
            if (current_goal is None
              or new_goal.priority >= current_goal.priority):
                self.bqueue.append(new_goal)
                self.announce_behaviour(new_goal)
            else:
                msg = ("I'd like to try %s, but I'm currently %s, "
                       "which is more important.")
                msg = msg % (new_goal.name, current_goal.name)
                self.world.chat.send_message(msg)

    def new_command(self, behaviour, **kwargs):
        self.user_command = (behaviour, kwargs)
        #self.world.chat.send_message("New behaviour: %s" % bh.name)

    def announce_behaviour(self, bh=None):
        if bh is not None:
            log.msg("Added goal: "+bh.name)
            self.world.chat.send_message("Ok, " + bh.name)
            return
        behaviour, goal = self.current_behaviour, self.current_goal
        preferred = self.preferred_goal
        log.msg("Current Goal: %s" % goal.name)
        log.msg("Current Behaviour: %s" % behaviour.name)
        log.msg("Preferred Behaviour: %s" % preferred.name)
        msg = "I am currently " + behaviour.name
        if behaviour.name != goal.name:
            msg = msg + " because I am %s" % goal.name
        self.world.chat.send_message(msg)
        if preferred.name != goal.name and preferred.name != behaviour.name:
            msg = "..but I'd rather be " + preferred.name
            self.world.chat.send_message(msg)



class BehaviourBase(object):
    def __init__(self, **kwargs):
        self.to_parent = {}
        self.manager = kwargs['manager']
        self.priority = kwargs['priority']
        self.world = self.manager.world
        self.bot = self.manager.bot
        self.status = Status.running
        self.hold_position_flag = True
        # behaviour names should be in present progressive -- e.g.,
        # they should fit after "I am.." and make a sentence.
        # kwargs sent to parent's 'from_child' method on exit
        name = "thinking someone forgot to change their behaviour name."
        self.cancelled = False
        self.failure_count = 1
        self.failure_max = 5

    cancelled = property(lambda s: s.to_parent['cancelled'],
                         lambda s, v: s.to_parent.__setitem__('cancelled', v))

    priority = property(lambda s: s.to_parent['priority'],
                        lambda s, v: s.to_parent.__setitem__('priority', v))

    @inlineCallbacks
    def tick(self):
        if self.cancelled:
            returnValue(None)
        yield self._tick()

    def evaluate(self):
        """Behaviour currently undefined.  In theory, this will be used to
        evaluate whether or not this leaf is succeeding at its goal, and return
        some existent value to indicate what should be done.  May be entirely
        unnecessary."""
        return False

    def cancel(self):
        self.cancelled = True
        self.status = Status.failure

    def _tick(self):
        raise NotImplemented('_tick')

    def from_child(self, child_status, cancelled, **kwargs_from_child):
        """Modify behaviour based on child's exit status"""
        if self.cancelled == True:
            return
        self.status = Status.running
        if child_status == Status.failure:
            self.failure_count += 1
        if self.failure_count >= self.failure_max:
            self.status = Status.failure

    def add_subbehaviour(self, behaviour, *args, **kwargs):
        if 'priority' not in kwargs:
            kwargs['priority'] = Priorities.sub_behaviour
        g = behaviour(manager=self.manager, parent=self, **kwargs)
        self.manager.bqueue.append(g)
        self.status = Status.suspended


class LookAtPlayerBehaviour(BehaviourBase):
    def __init__(self, *args, **kwargs):
        super(LookAtPlayerBehaviour, self).__init__(*args, **kwargs)
        self.player = kwargs['player'] if 'player' in kwargs else 'me'
        if self.player == 'me':
            self.player = config.COMMANDER
        self.hold_position_flag = False
        self.name = 'looking at player %s' % self.player

    def _tick(self):
        if self.cancelled:
            self.status = Status.failure
            return
        if not self.player in self.world.entities.players:
            return
        player_eid = self.world.entities.players[self.player]
        player = self.world.entities.get_entity(player_eid)
        if player is None:
            return
        p = player.position + utils.Vector(0, config.PLAYER_EYELEVEL, 0)
        self.bot.turn_to_point(self.bot.bot_object, p.tuple)


class WalkSignsBehaviour(BehaviourBase):
    def __init__(self, *args, **kwargs):
        super(WalkSignsBehaviour, self).__init__(*args, **kwargs)
        self.signpoint = None
        self.signpoint_forward_direction = True
        self.group = kwargs.get("group")
        self.walk_type = kwargs.get("type")
        self.name = '%s signs in group "%s"' % (self.walk_type[:-1]+'ing',
                                                self.group)
        self._prepare()

    def _prepare(self):
        if self.walk_type == "circulate":
            self.next_sign = self.world.sign_waypoints.get_groupnext_circulate
        elif self.walk_type == "rotate":
            self.next_sign = self.world.sign_waypoints.get_groupnext_rotate
        else:
            raise Exception("unknown walk sign type")

    def _tick(self):
        if self.cancelled:
            self.status = Status.failure
            return
        if not self.world.sign_waypoints.has_group(self.group):
            msg = "No group named '%s'" % self.group
            self.world.chat.send_message(msg)
            self.status = Status.failure
            return
        sign_data = self.next_sign(self.group, self.signpoint,
                                   self.signpoint_forward_direction)
        new_signpoint, self.signpoint_forward_direction = sign_data
        if new_signpoint == self.signpoint:
            self.status = Status.success
            return
        else:
            self.signpoint = new_signpoint
        if self.signpoint is not None:
            if not self.world.sign_waypoints.check_sign(self.signpoint):
                return
            log.msg("Go to sign %s" % self.signpoint)
            self.add_subbehaviour(TravelToBehaviour,
                                  coords=self.signpoint.coords)
        else:
            self.status = Status.failure


class GoToSignBehaviour(BehaviourBase):
    def __init__(self, *args, **kwargs):
        super(GoToSignBehaviour, self).__init__(*args, **kwargs)
        self.sign_name = kwargs.get("sign_name", "")
        self.name = 'going to the sign "%s"' % self.sign_name

    def from_child(self, status, **kwargs):
        if self.cancelled:
            return
        self.status = status

    def _tick(self):
        waypoints = self.world.sign_waypoints
        if self.cancelled or self.status == Status.failure:
            self.status = Status.failure
            return
        self.signpoint = waypoints.get_namepoint(self.sign_name)
        if self.signpoint is None:
            self.signpoint = waypoints.get_name_from_group(self.sign_name)
        if self.signpoint is None:
            msg = "cannot identify sign with name %s"
            self.world.chat.send_message(msg % self.sign_name)
            self.status = Status.failure
            return
        if not waypoints.check_sign(self.signpoint):
            self.status = Status.failure
            return
        log.msg("Go To: sign details %s" % self.signpoint)
        self.add_subbehaviour(TravelToBehaviour, coords=self.signpoint.coords,
                              recurse=False, estimate=False)


class FollowPlayerBehaviour(BehaviourBase):
    def __init__(self, *args, **kwargs):
        super(FollowPlayerBehaviour, self).__init__(*args, **kwargs)
        self.player = kwargs['player'] if 'player' in kwargs else 'me'
        if self.player == 'me':
            self.player = config.COMMANDER
        self.last_block = None
        self.last_position = None
        self.name = "following %s" % self.player
        self.last_attempt = 0
        # distance * recalc_multiplier = seconds before automatic recalc
        self.recalc_multiplier = 0.25

    def from_child(self, status, goal=None, endpoint=None, estimated=None,
                   **kwargs):
        """kwargs in child's 'to_parent' dict must include the following:
            status := (Status attribute)
            goal := Goal as set last round
            endpoint := Actual point traversed to
            estimated := Bool - Whether or not the endpoint was estimated.
        This information is recorded so that the stuck method can determine
        if the bot is stuck or not.
        """
        if self.cancelled:
            return
        # Even if our child fails, Status should still be 'running', since this
        # is a persistent behaviour.
        self.status = Status.running
        self.return_processed = True

#    def __del__(self):
#        log.msg("Destroying Behaviour: " + self.name)

    def _tick(self):
        if self.cancelled:
            self.status = Status.failure
            return
        if not self.player in self.world.entities.players:
            return
        eid = self.world.entities.players[self.player]
        entity = self.world.entities.get_entity(eid)
        bot_object = self.world.bot.bot_object
        bb = AABB.from_player_coords(entity.position)
        block = self.world.grid.standing_on_block(bb)
        if block is None:
            block = self.world.grid.actual_block(bb)
#        #block = self.world.grid.downward_block(bb)
        distance = bot_object.position.distance(entity.position)
        delay = distance * self.recalc_multiplier
        #don't auto-recalculate more than once a second.
        delay = delay if delay > 1 else 1
        if (self.last_block != block
#          or distance > config.PATHFIND_MAX * 0.5  #actual path may be crooked
          or time() - self.last_attempt > delay):
          #or self.last_position != self.bot.bot_object.position_grid):
            log.msg('recalculating move..')
            # Cancel any other running behaviours we're doing
            self.manager.cancel_running(priority=self.priority - 1)
            self.last_position = self.bot.bot_object.position_grid
            self.last_attempt = time()
            self.last_block = block
            self.add_subbehaviour(TravelToBehaviour, coords=block.coords,
                                  shorten_path_by=2, estimate=True)


class TravelToBehaviour(BehaviourBase):
    """"Travel to a coordinate, and abort if there is something that prevents
    that.
        coords := Coordinates to travel to
        shorten_path_by := remove a number of steps at the end of the path
        recurse := Use an additional instance to smooth motion
    """
    def __init__(self, *args, **kwargs):
        super(TravelToBehaviour, self).__init__(*args, **kwargs)
        # used when travel_coords is set, so this line must go before that.
        self.recurse = kwargs.get('recurse', True)
        self.travel_coords = kwargs["coords"]
        self.shorten_path_by = kwargs.get("shorten_path_by", 0)
        self.estimate = kwargs.get('estimate', True)
        self.ready = False
        self.start_time = time()
        self.fail_count = 0
        self.fail_limit = config.PATHFIND_MIN * 1.5 if self.recurse else 4
        #log.msg(self.name)

    @property
    def travel_coords(self):
        return self._travel_coords

    @travel_coords.setter
    def travel_coords(self, value):
        self._travel_coords = value
        name = 'traveling from %s to %s %s'
        self.name = name % (self.bot.standing_on_block(self.bot.bot_object),
                            self.world.grid.get_block_coords(value),
                            '(parent)' if self.recurse else '')

    @inlineCallbacks
    def _prepare(self):
        sb = self.bot.standing_on_block(self.bot.bot_object)
        if sb is None:
            self.ready = False
        else:
            d = cooperate(AStar(dimension=self.world.dimension,
                                start_coords=sb.coords,
                                end_coords=self.travel_coords,
                                estimate=self.estimate)).whenDone()
            d.addErrback(logbot.exit_on_error)
            astar = yield d
            if astar is None or astar.path is None:
                self.status = Status.failure
            else:
                current_start = self.bot.standing_on_block(self.bot.bot_object)
                if sb == current_start:
                    self.path = astar.path
                    self.path.remove_last(self.shorten_path_by)
                    self.ready = True
                    if len(astar.path) <= self.shorten_path_by + 0.5:
                        self.status = Status.success

    def from_child(self, status, no_op=None, **kwargs):
        if self.cancelled:
            return
        # When recursing, we can treat failures almost as if they were
        # successes -- the path we actually want will advance, and the
        # child will pathfind to the next node on our path.
        if self.recurse:
            if status == Status.failure:
                self.fail_count += 1
                if self.fail_count >= self.fail_limit:
                    self.status = Status.failure
                    return
                self.status = Status.running
                return
            elif status == Status.success:
                self.fail_count = 0
                self.status == Status.running
            self.status == status
        # When not recursing, our child is a MoveToBehaviour.  Anything but
        # success means it failed, and we should recalculate our path.
        if status != Status.success:
            self.ready = False
            self.fail_count += 1
        else:
            # When a child returns 'no_op = True' in its 'to_parent' attr,
            # we shouldn't count it as a successful move.
            self.fail_count = 0 if not no_op else self.fail_count
        if self.fail_count >= self.fail_limit:
            self.status = Status.failure
        else:
            self.status = Status.running

    @inlineCallbacks
    def _tick(self):
        if self.cancelled:
            self.status = Status.failure
        if self.status == Status.failure:
            return
        while not self.ready:
            yield self._prepare()
            self.fail_count += 1
            if self.fail_count == self.fail_limit:
                self.ready = True
                self.status = Status.failure
                return
        if self.status == Status.failure:
            return
        self.follow(self.path)

    def follow(self, path):
        b_obj = self.bot.bot_object
        if path.is_finished:
            if path.estimated:
                self.to_parent['estimated'] = True
                self.status = Status.partial_success
            else:
                self.status = Status.success
            return
        step = path.take_step()
        if step is None:
            self.status = Status.failure
            return
        else:
            current_start = self.bot.standing_on_block(self.bot.bot_object)
            if current_start is None:
                log.msg("Got 'None' for current bot location, failing..")
                self.status = Status.failure
                return
# path changes now handled by recursion -- this *should* be unecessary now..
#            if current_start.coords.distance(step.coords) >= 2:
#                log.msg("Path has changed! rerouting..")
#                self.add_subbehaviour(TravelToBehaviour,
#                                      coords=self.travel_coords,
#                                      shorten_path_by=self.shorten_path_by)
            if self.recurse:
                self.add_subbehaviour(TravelToBehaviour,
                                      coords=step.coords,
                                      shorten_path_by=0,
                                      estimate=False,
                                      recurse=False,
                                      max_cost=config.PATHFIND_MIN)
            else:
                self.add_subbehaviour(MoveToBehaviour,
                                      start=current_start.coords,
                                      target=step.coords)


class MoveToBehaviour(BehaviourBase):
    def __init__(self, *args, **kwargs):
        super(MoveToBehaviour, self).__init__(*args, **kwargs)
        self.target_coords = kwargs["target"]
        self.start_coords = kwargs["start"]
        self.to_parent['no_op'] = self.start_coords == self.target_coords
        self.was_at_target = False
        self.hold_position_flag = False
        self.name = 'moving to %s' % str(self.target_coords)
        self.start_time = time()
        # If this much time has passed, we failed at moving.
        self.max_time = config.MAX_SINGLE_MOVE_TIME

    def check_status(self, b_obj):
        if time() - self.start_time >= self.max_time:
            return Status.failure
        gs = GridSpace(self.world.grid)
        self.start_state = gs.get_state_coords(self.start_coords)
        self.target_state = gs.get_state_coords(self.target_coords)
        go = gs.can_go(self.start_state, self.target_state)
        if not go:
            log.msg('Cannot go between %s and %s' % (self.start_state,
                                                     self.target_state))
            return Status.failure
        if not self.was_at_target:
            self.was_at_target = self.target_state.vertical_center_in(
                                                                b_obj.position)
        if (self.target_state.base_in(b_obj.aabb)
          and self.target_state.touch_platform(b_obj.position)):
            return Status.success
        return Status.running

    def _tick(self):
        if self.cancelled:
            self.status = Status.failure
            return
        b_obj = self.bot.bot_object
        self.status = self.check_status(b_obj)
        if self.status != Status.running:
            return
        on_ladder = self.bot.is_on_ladder(b_obj)
        in_water = self.bot.is_in_water(b_obj)
        if on_ladder or in_water:
            elev = self.target_state.platform_y - b_obj.y
            if fops.gt(elev, 0):
                self.jump(b_obj)
                self.move(b_obj)
            elif fops.lt(elev, 0):
                self.move(b_obj)
            else:
                if on_ladder:
                    self.sneak(b_obj)
                self.move(b_obj)
        elif self.bot.is_standing(b_obj):
            elev = self.target_state.platform_y - b_obj.y
            if fops.lte(elev, 0):
                self.move(b_obj)
            elif fops.gt(elev, 0):
                if self.start_state.base_in(b_obj.aabb):
                    self.jump(b_obj)
                self.move(b_obj)
        else:
            self.move(b_obj)

    def move(self, b_obj):
        direction = utils.Vector2D(self.target_state.center_x - b_obj.x,
                                   self.target_state.center_z - b_obj.z)
        direction.normalize()
        if not self.was_at_target:
            self.bot.turn_to_direction(b_obj, direction.x, direction.z)
        b_obj.direction = direction

    def jump(self, b_obj):
        b_obj.is_jumping = True

    def sneak(self, b_obj):
        self.bot.start_sneaking(b_obj)
