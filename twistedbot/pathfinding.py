
import heapq
import time

import config
import logbot
from gridspace import GridSpace


debug = False
log = logbot.getlogger("ASTAR")


class PathNode(object):
    __slots__ = ['coords', 'g', 'h', 'parent']
    def __init__(self, coords, parent=None):
        self.coords = coords
        self.g = 0
        self.h = 0
        self.parent = parent

    def __str__(self):
        return str(self.coords)

    def __repr__(self):
        return self.__str__()

    def __lt__(self, other):
        return self.f < other.f

    def __eq__(self, other):
        return self.coords == other.coords

    def __hash__(self):
        return self.hash

    @property
    def f(self):
        return self.g + self.h

    @property
    def hash(self):
        return hash(self.coords)

    def set_score(self, g, h):
        self.g = g
        self.h = h

    @property
    def step(self):
        step = 0
        parent = self
        while parent is not None:
            parent = parent.parent
            step += 1
        return step

    def _backpath(self):
        parent = self
        while parent is not None:
            yield parent
            parent = parent.parent
        raise StopIteration()

    @property
    def path(self):
        path = list(self._backpath())
        path.reverse()
        return path


class Path(object):
    __slots__ = ['dimension', 'nodes', 'start_aabb',
                 'node_step', 'is_finished']

    def __init__(self, dimension=None, nodes=None, start_aabb=None):
        self.dimension = dimension
        self.nodes = nodes
        self.start_aabb = start_aabb
        self.node_step = 0
        self.is_finished = False

    def __str__(self):
        nodes = '\n\t'.join([str(n) for n in self.nodes])
        return "Path nodes %d\n\t%s" % (len(self.nodes), nodes)

    def __len__(self):
        return len(self.nodes)

    def take_step(self):
        try:
            step = self.nodes[self.node_step]
            self.node_step += 1
            if self.node_step == len(self.nodes):
                self.is_finished = True
            return step
        except IndexError:
            return None

    def remove_last(self, n):
        if n < 1:
            return
        self.nodes = self.nodes[:-n]
        if not self.nodes:
            self.is_finished = True


class AStar(object):
#TODO: change 'use_best' to 'estimate' for consistency with behaviours module
#TODO: (in behaviours) set recursive call of astar to not estimate
#TODO: explore limiting by execution time rather than by path distance

    def __init__(self, dimension=None, start_coords=None, end_coords=None,
                 path_max=config.PATHFIND_MAX, use_best=True):
        self.t_start = time.time()
        self.dimension = dimension
        self.grid = dimension.grid
        self.start_node = PathNode(start_coords)
        self.goal_node = PathNode(end_coords)
        self.gridspace = GridSpace(self.grid)
        # keep max_cost between the configured values
        values = [config.PATHFIND_MAX, path_max, config.PATHFIND_MIN]
        self.max_cost = list(sorted(values))[1]
        self.path = None
        self.closed_set = set()
        goal_state = self.gridspace.get_state_coords(end_coords)
        if goal_state.can_stand or goal_state.can_hold or use_best:
            self.open_heap = [self.start_node]
            self.open_set = set([self.start_node])
        else:
            self.open_heap = []
            self.open_set = set([])
        self.start_node.set_score(0, self.heuristic_cost_estimate(
                                              self.start_node, self.goal_node))
        self.iter_count = 0
        self.best = self.start_node
        self.use_best = use_best

        self.distance = self.start_node.coords.distance(self.goal_node.coords)
        self.excessive = 2.5

    def get_edge_cost(self, node_from, node_to,
                      x_neighbors=None, y_neighbors=None):
        return config.COST_DIRECT

    def neighbours(self, node):
        for state in self.gridspace.neighbours_of(node.coords):
            if state.coords not in self.closed_set:
                yield PathNode(state.coords)

    def heuristic_cost_estimate(self, start, goal):
        """Takes a path node, and tries to estimate the cost to the goal."""
#        y = start.coords.y - goal.coords.y
#        adx = abs(start.coords.x - goal.coords.x)
#        adz = abs(start.coords.z - goal.coords.z)
#
#        fall, rise = (abs(y), 0) if y < 0 else (0, abs(y))
#        h_diagonal = min(adx, adz)
#        h_straight = adx + adz
#        h = (config.COST_DIAGONAL * h_diagonal +
#             config.COST_DIRECT * (h_straight - 2 * h_diagonal) +
#             config.COST_FALL * fall +
#             config.COST_JUMP * rise)
        vertical = start.coords.y - goal.coords.y
        if vertical < 0:
            vertical = abs(vertical) * config.COST_FALL
        else:
            vertical = vertical * config.COST_JUMP
        distance = start.coords.distance(goal.coords)
        h = distance + vertical
        return h

    def _excessive_path(self, start):
        """Cheap evalutation of whether this path is excessive, only usable on
        a scored node."""
        excessive = start.step > self.distance * self.excessive
        if excessive:
            debug and log.msg(msg % (start.h, start.g))
        return excessive

    def report(self):
        nodes = ''
        if not self.path:
            path = '<PATH NOT FOUND>'
        else:
            estimated = '' if self.best == self.goal_node else "(estimated)"
            path = 'path length %s %s' % (self.best.step, estimated)
            nodes = 'Nodes: %s' % self.path.nodes
        msg = "Finished in %s sec, %s iterations, %s"
        log.msg(msg % (time.time() - self.t_start, self.iter_count, path))
        debug and log.msg(nodes)

    def next(self):
        self.iter_count += 1
        if not self.open_set:
            if self.use_best:
                self.path = Path(dimension=self.dimension,
                                 nodes=self.best.path)
            self.report()
            self.gridspace = None
            raise StopIteration()
        x = heapq.heappop(self.open_heap)
        if x == self.goal_node:
            self.best = x
            self.path = Path(dimension=self.dimension, nodes=x.path)
            self.gridspace = None
            self.report()
            raise StopIteration()
        self.open_set.remove(x)
        self.closed_set.add(x.coords)
        x_neighbours = self.neighbours(x)
        for y in x_neighbours:
            if y.coords in self.closed_set:
                continue
            tentative_g_core = x.g + self.get_edge_cost(x, y, x_neighbours)
            if y not in self.open_set or tentative_g_core < y.g:
                y.set_score(tentative_g_core,
                            self.heuristic_cost_estimate(y, self.goal_node))
                if y.h < self.best.h:
                    self.best = y
                y.parent = x
                if y not in self.open_set:
                    heapq.heappush(self.open_heap, y)
                    self.open_set.add(y)
                if y.step > self.max_cost or self._excessive_path(y):
                    if self.use_best:
                        self.path = Path(dimension=self.dimension,
                                         nodes=self.best.path)
                        self.gridspace = None
                        self.report()
                        raise StopIteration()
                    log.err("Finding path over limit between %s and %s" % (self.start_node.coords, self.goal_node.coords))
                    raise StopIteration()

