"""Симуляция партии по правилам первого прототипа (README «Первый прототип»).

Видимые игроки, без диких, тумана, укрытия и модификаторов. Часы замка,
линька, бои, одна лавка, погоня. Бои игроков решаются 50 на 50: прокачка
здесь не моделируется, нам важны время и ход партии.
"""
import random
from collections import deque
from dataclasses import dataclass, field

from castle import Castle, GATES, GRAIL

# --- Тайминги хода, секунды (gameplay.md: «Ход», «Встречи и бой») ------------
ROLES_REVEAL = 3
ROLE_DECISION = (1, 4)       # на каждого ждущего: решение роли, таймер 5 с
DICE = 2
DOOR_CHOICE = (2, 4)         # на каждую комнату пути
NEW_ROOM = (8, 15)           # содержимое новой комнаты
OLD_ROOM = 2                 # отработанная комната
FIGHT = (25, 35)             # рулетка, выбор зрителей, бой, трофей
SHOP = (8, 12)
RESULT = (3, 6)
CAMERA = 1
SETUP = {2: (50, 90), 3: (70, 120), 4: (90, 150)}   # сборка динозавров и старт
LETOPIS = (30, 60)
LINKA = 15                   # линька: все выбирают часть тела

# --- Поведение (предположения) -----------------------------------------------
DETOUR_CHANCE = 0.3          # фазы 1–2: свернуть за добычей вместо курса на грааль
ATTACK_CHANCE = 0.5          # фазы 1–2: напасть при встрече, а не разойтись мирно
OBSTACLE_PER_STEP = 0.03     # завал или баррикада останавливают движение
STRONG_MONSTER = 0.07        # доля сильных монстров среди новых комнат
SHOP_ROOM = 0.05
REVEAL_ROUND = 6             # часы: на 6-м круге комната грааля открывается всем
COLLAPSE_ROUNDS = 5          # часы: столько кругов после взятия грааля
LINKA_ROUND = 4


def turn_seconds(rng, waiting, steps, new_room, fight, shop):
    t = ROLES_REVEAL + DICE + CAMERA + rng.uniform(*RESULT)
    t += sum(rng.uniform(*ROLE_DECISION) for _ in range(waiting))
    t += sum(rng.uniform(*DOOR_CHOICE) for _ in range(steps))
    t += rng.uniform(*NEW_ROOM) if new_room else OLD_ROOM
    if fight:
        t += rng.uniform(*FIGHT)
    if shop:
        t += rng.uniform(*SHOP)
    return t


@dataclass
class Player:
    gate: tuple
    pos: tuple
    protected_until: int = -1    # номер хода, до конца которого действует защита


@dataclass
class Result:
    rounds: int
    seconds: float
    reason: str
    pickups: int
    pvp_fights: int
    turns: int
    fight_turns: int = 0
    gate_win: bool = field(default=False)
    first_pickup: int = 0

    @property
    def minutes(self):
        return self.seconds / 60


def _path(castle, start, goal):
    prev = {start: None}
    queue = deque([start])
    while queue:
        room = queue.popleft()
        if room == goal:
            break
        for nb in castle.neighbors(room):
            if nb not in prev:
                prev[nb] = room
                queue.append(nb)
    if goal not in prev:
        return []
    path, node = [], goal
    while node != start:
        path.append(node)
        node = prev[node]
    return list(reversed(path))


def play(n_players, rng):
    castle = Castle.with_walls(rng)
    gates = {2: [GATES[1], GATES[2]], 3: [GATES[0], GATES[1], GATES[3]], 4: list(GATES)}[n_players]
    players = [Player(gate=g, pos=g) for g in gates]
    explored = set(gates)
    grail_pos, holder = GRAIL, None
    grail_taken, collapse_end = False, None
    seconds = rng.uniform(*SETUP[n_players]) + rng.uniform(*LETOPIS)
    pickups = pvp = turns = fight_turns = 0
    first_pickup = 0
    turn_no = 0

    for rnd in range(1, 31):
        if rnd == LINKA_ROUND:
            seconds += LINKA
        for i, me in enumerate(players):
            turn_no += 1
            turns += 1
            phase3 = grail_taken
            occupied = {p.pos: j for j, p in enumerate(players) if j != i}

            if holder == i:
                target = me.gate
            elif phase3 and holder is not None:
                target = players[holder].pos
            elif grail_pos is not None:
                target = grail_pos
            else:
                target = GRAIL
            if not phase3 and rng.random() < DETOUR_CHANCE:
                near = [r for r in castle.rooms if r not in explored and r not in occupied
                        and (castle.distance(me.pos, r) or 99) <= 2]
                if near:
                    target = rng.choice(near)

            dice = rng.randint(1, 3)
            path = _path(castle, me.pos, target)
            steps = 0
            met = None
            fought = False
            for room in path[:dice]:
                steps += 1
                me.pos = room
                if holder == i and room == me.gate:
                    seconds += turn_seconds(rng, n_players - 1, steps, False, False, False)
                    return Result(rnd, seconds, "ворота", pickups, pvp, turns, fight_turns, True, first_pickup)
                j = occupied.get(room)
                if j is not None and players[j].protected_until < turn_no:
                    met = j
                    break
                if grail_pos == room or rng.random() < OBSTACLE_PER_STEP:
                    break

            if met is not None:
                if phase3 or rng.random() < ATTACK_CHANCE:
                    fought = True
                    pvp += 1
                    i_win = rng.random() < 0.5
                    loser = met if i_win else i
                    if holder == loser:
                        holder, grail_pos = None, players[loser].pos
                    free = [r for r in castle.neighbors(players[loser].pos)
                            if r not in {p.pos for p in players}]
                    if free:
                        players[loser].pos = rng.choice(free)
                    players[loser].protected_until = turn_no + n_players

            new_room = me.pos not in explored
            explored.add(me.pos)
            strong = new_room and rng.random() < STRONG_MONSTER
            shop = new_room and rng.random() < SHOP_ROOM
            fight_now = fought or strong
            fight_turns += fight_now
            seconds += turn_seconds(rng, n_players - 1, steps, new_room, fight_now, shop)

            if holder is None and grail_pos == me.pos and not fought:
                holder, grail_pos = i, None
                pickups += 1
                if not grail_taken:
                    grail_taken, collapse_end = True, rnd + COLLAPSE_ROUNDS
                    seconds += LINKA
                    first_pickup = rnd
                if me.pos == me.gate:
                    return Result(rnd, seconds, "ворота", pickups, pvp, turns, fight_turns, True, first_pickup)

        if grail_taken and rnd >= collapse_end:
            return Result(rnd, seconds, "обвал", pickups, pvp, turns, fight_turns, False, first_pickup)
    return Result(30, seconds, "обвал", pickups, pvp, turns, fight_turns, False, first_pickup)
