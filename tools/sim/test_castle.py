import random
import unittest

from castle import Castle, FUNNEL_EXIT, GATES, GRAIL


class CastleGeometryTest(unittest.TestCase):
    def test_castle_has_twenty_seven_rooms(self):
        self.assertEqual(len(Castle.full().rooms), 27)

    def test_no_dead_ends_without_walls(self):
        castle = Castle.full()
        for room in castle.rooms:
            if room == GRAIL:
                continue
            self.assertGreaterEqual(len(castle.neighbors(room)), 2, room)

    def test_every_gate_is_seven_steps_from_grail_without_walls(self):
        castle = Castle.full()
        for gate in GATES:
            self.assertEqual(castle.distance(gate, GRAIL), 7, gate)

    def test_corridor_before_grail_is_single_file(self):
        castle = Castle.full()
        self.assertEqual(sorted(castle.neighbors((3, 7))), [(3, 6), (3, 8)])


class CastleWallsTest(unittest.TestCase):
    def test_random_walls_keep_two_disjoint_paths_from_funnel_to_each_gate(self):
        for seed in range(30):
            castle = Castle.with_walls(random.Random(seed))
            for gate in GATES:
                self.assertGreaterEqual(castle.disjoint_paths(gate, FUNNEL_EXIT), 2, (seed, gate))

    def test_random_walls_keep_grail_reachable(self):
        for seed in range(30):
            castle = Castle.with_walls(random.Random(seed))
            for gate in GATES:
                self.assertIsNotNone(castle.distance(gate, GRAIL), (seed, gate))

    def test_random_walls_actually_remove_some_doors(self):
        full = Castle.full()
        walled = Castle.with_walls(random.Random(1))
        self.assertLess(walled.door_count(), full.door_count())


if __name__ == "__main__":
    unittest.main()
