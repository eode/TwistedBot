
import heapq
import time

import config
import logbot
from gridspace import GridSpace


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
        return "Path nodes %d\n\t%s" % (len(self.nodes), '\n\t'.join([str(n) for n in self.nodes]))

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
    def __init__(self, dimension=None, start_coords=None, end_coords=None, max_cost=config.PATHFIND_LIMIT):
        self.dimension = dimension
        self.grid = dimension.grid
        self.start_node = PathNode(start_coords)
        self.goal_node = PathNode(end_coords)
        self.gridspace = GridSpace(self.grid)
        self.max_cost = max_cost
        self.path = None
        self.closed_set = set()
        goal_state = self.gridspace.get_state_coords(end_coords)
        if goal_state.can_stand or goal_state.can_hold:
            self.open_heap = [self.start_node]
            self.open_set = set([self.start_node])
        else:
            self.open_heap = []
            self.open_set = set([])
        self.start_node.set_score(0, self.heuristic_cost_estimate(self.start_node, self.goal_node))
        self.iter_count = 0
        self.t_start = time.time()

    def get_edge_cost(self, node_from, node_to,
                      x_neighbors=None, y_neighbors=None):
        return config.COST_DIRECT

    def neighbours(self, node):
        for state in self.gridspace.neighbours_of(node.coords):
            if state.coords not in self.closed_set:
                yield PathNode(state.coords)

    def heuristic_cost_estimate(self, start, goal):
        adx = abs(start.coords.x - goal.coords.x)
        adz = abs(start.coords.z - goal.coords.z)
        h_diagonal = min(adx, adz)
        h_straight = adx + adz
        h = config.COST_DIAGONAL * h_diagonal + config.COST_DIRECT * (h_straight - 2 * h_diagonal)
        return h

    def next(self):
        self.iter_count += 1
        if not self.open_set:
            log.msg('time consumed %s sec, made %d iterations' % (time.time() - self.t_start, self.iter_count))
            log.err("Did not find path between %s and %s" % (self.start_node.coords, self.goal_node.coords))
            raise StopIteration()
        x = heapq.heappop(self.open_heap)
        if x == self.goal_node:
            self.path = Path(dimension=self.dimension, nodes=x.path)
            self.gridspace = None
            log.msg('finished in %s sec, length %d, made %d iterations' % (time.time() - self.t_start, len(self.path.nodes), self.iter_count))
            log.msg('nodes %s' % self.path.nodes)
            raise StopIteration()
        self.open_set.remove(x)
        self.closed_set.add(x.coords)
        x_neighbours = self.neighbours(x)
        for y in x_neighbours:
            if y.coords in self.closed_set:
                continue
            tentative_g_core = x.g + self.get_edge_cost(x, y, x_neighbours)
            if y not in self.open_set or tentative_g_core < y.g:
#TODO: decrease this score when discovering an impassable edge.
                y.set_score(tentative_g_core, self.heuristic_cost_estimate(y, self.goal_node))
                y.parent = x
                if y not in self.open_set:
                    heapq.heappush(self.open_heap, y)
                    self.open_set.add(y)
                if y.step > self.max_cost:
                    log.err("Finding path over limit between %s and %s" % (self.start_node.coords, self.goal_node.coords))
                    raise StopIteration()

