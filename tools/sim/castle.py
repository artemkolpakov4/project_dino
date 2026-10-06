"""Замок-воронка из location.md: 30 комнат, четверо ворот, коридор к граалю."""
from collections import deque

GATES = {"В1": (1, 3), "В2": (2, 2), "В3": (4, 2), "В4": (5, 3)}
GATES = list(GATES.values())
GRAIL = (3, 8)
FUNNEL_EXIT = (3, 5)  # последняя комната воронки перед коридором (3,6)-(3,7)

_ROWS = {
    0: range(2, 6),   # крыло сверху
    1: range(3, 6),   # В1 + 2 комнаты
    2: range(2, 6),   # В2 + 3 комнаты
    3: range(1, 9),   # главный ряд: 7 комнат и грааль
    4: range(2, 6),   # В3 + 3 комнаты
    5: range(3, 6),   # В4 + 2 комнаты
    6: range(2, 6),   # крыло снизу
}
ROOMS = [(r, c) for r, cols in _ROWS.items() for c in cols]


def _grid_doors(rooms):
    room_set = set(rooms)
    doors = set()
    for r, c in rooms:
        for nb in ((r + 1, c), (r, c + 1)):
            if nb in room_set:
                doors.add(frozenset({(r, c), nb}))
    return doors


class Castle:
    def __init__(self, rooms, doors):
        self.rooms = list(rooms)
        self.doors = set(doors)
        self._adj = {room: [] for room in self.rooms}
        for door in self.doors:
            a, b = tuple(door)
            self._adj[a].append(b)
            self._adj[b].append(a)

    @classmethod
    def full(cls):
        return cls(ROOMS, _grid_doors(ROOMS))

    @classmethod
    def with_walls(cls, rng, wall_share=0.25, tries=200):
        """Убирает примерно wall_share дверей, сохраняя гарантии из location.md."""
        all_doors = _grid_doors(ROOMS)
        for _ in range(tries):
            doors = set(all_doors)
            for door in sorted(all_doors, key=lambda d: sorted(d)):
                if rng.random() < wall_share:
                    doors.discard(door)
            castle = cls(ROOMS, doors)
            if castle._satisfies_guarantees():
                return castle
        return cls(ROOMS, all_doors)

    def _satisfies_guarantees(self):
        if any(self.distance(gate, GRAIL) is None for gate in GATES):
            return False
        if any(self.distance(ROOMS[0], room) is None for room in self.rooms):
            return False
        return all(self.disjoint_paths(gate, FUNNEL_EXIT) >= 2 for gate in GATES)

    def neighbors(self, room):
        return list(self._adj[room])

    def door_count(self):
        return len(self.doors)

    def distances_from(self, start):
        dist = {start: 0}
        queue = deque([start])
        while queue:
            room = queue.popleft()
            for nb in self._adj[room]:
                if nb not in dist:
                    dist[nb] = dist[room] + 1
                    queue.append(nb)
        return dist

    def distance(self, a, b):
        return self.distances_from(a).get(b)

    def disjoint_paths(self, a, b):
        """Число путей a→b без общих дверей (макс. поток с единичными рёбрами)."""
        used = set()  # направленные рёбра потока
        flow = 0
        while True:
            parent = {a: None}
            queue = deque([a])
            while queue and b not in parent:
                room = queue.popleft()
                for nb in self._adj[room]:
                    if nb in parent:
                        continue
                    forward_free = (room, nb) not in used
                    if forward_free:
                        parent[nb] = room
                        queue.append(nb)
            if b not in parent:
                return flow
            node = b
            while parent[node] is not None:
                prev = parent[node]
                if (node, prev) in used:
                    used.discard((node, prev))
                else:
                    used.add((prev, node))
                node = prev
            flow += 1
