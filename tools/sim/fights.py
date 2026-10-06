"""Модели 12 боёв из gameplay.md («Двенадцать боёв»).

Боец A сильнее на k уровней своей характеристики: k — сколько раз срабатывает
бонус характеристики. Боец B — без бонуса. Защитник (за кем ничья) выбирается
случайно, поэтому при k=0 бой честный. Все числа, которых нет в правилах,
вынесены сюда и помечены: их подбираем на прототипе.
"""
import random
from functools import lru_cache
from itertools import product

# --- Умение игрока в боях на реакцию (предположения) -------------------------
SKILL = {
    #            нажатий/с  ошибка пика  промах ритма  реакция, с  ложное нажатие
    "casual":  dict(mash=5.5, peak=0.12, miss=0.12, rt=0.42, false=0.15),
    "regular": dict(mash=6.5, peak=0.09, miss=0.08, rt=0.36, false=0.10),
    "gamer":   dict(mash=7.5, peak=0.06, miss=0.04, rt=0.30, false=0.06),
}

# --- Параметры, которых нет в правилах (подбираем на прототипе) --------------
RACE_LENGTH = 40          # Забег: нажатий до финиша
RACE_HEAD_START = 3       # Забег: фора за уровень, нажатий
PEAK_ZONE = 0.05          # Удар хвостом: полуширина пика
PEAK_ZONE_PER_K = 0.02    # Удар хвостом: расширение пика за уровень
PIT_FALL_ON = (1, 2)      # Короткая дорога: на этих гранях падаешь в яму
PIT_PENALTY = 3           # Короткая дорога: шагов за падение
ROPE_SNAP = (3.0, 8.0)    # Кто дольше держит: канат рвётся в этом интервале, с
ROPE_SHIFT_PER_K = 0.5    # Кто дольше держит: свой канат у сильного рвётся позже, с


def d6(rng):
    return rng.randint(1, 6)


# --- Реакция ------------------------------------------------------------------
def zabeg(k, rng, sa, sb, head=None):
    """Скорость. Жми чаще всех, у сильного старт впереди."""
    ra = max(2.0, rng.gauss(sa["mash"], 0.8))
    rb = max(2.0, rng.gauss(sb["mash"], 0.8))
    head = RACE_HEAD_START if head is None else head
    ta = (RACE_LENGTH - head * k) / ra
    tb = RACE_LENGTH / rb
    return _compare(-ta, -tb, rng)


def udar_hvostom(k, rng, sa, sb, zone_per_k=None):
    """Сила. Три удара, жми на пике, у сильного пик шире."""
    def hits(skill, zone):
        total = 0.0
        for _ in range(3):
            err = abs(rng.gauss(0, skill["peak"]))
            total += 10 if err <= zone else max(0.0, 10 - 40 * (err - zone))
        return total
    zone_per_k = PEAK_ZONE_PER_K if zone_per_k is None else zone_per_k
    return _compare(hits(sa, PEAK_ZONE + zone_per_k * k), hits(sb, PEAK_ZONE), rng)


def baraban(k, rng, sa, sb, base_lives=3, per_k=1.0):
    """Броня. Жми в такт, три трещины — проиграл, сильному прощается k трещин."""
    lives_a, lives_b = base_lives + int(per_k * k), base_lives
    defender_a = rng.random() < 0.5
    for _ in range(500):
        if rng.random() < sa["miss"]:
            lives_a -= 1
        if rng.random() < sb["miss"]:
            lives_b -= 1
        if lives_a <= 0 or lives_b <= 0:
            if lives_a <= 0 and lives_b <= 0:
                return defender_a
            return lives_b <= 0
    return defender_a


def zolotoe_yaitso(k, rng, sa, sb, egg_head=0.0, rt_noise=0.06):
    """Хитрость. Хватай только золотые яйца, сильному прощается k ложных нажатий."""
    eggs_a, eggs_b = int(egg_head * k), 0
    forgive = k if not egg_head else 0
    defender_a = rng.random() < 0.5
    for _ in range(500):
        if rng.random() < 1 / 3:
            ta = rng.gauss(sa["rt"], rt_noise)
            tb = rng.gauss(sb["rt"], rt_noise)
            if ta < tb:
                eggs_a += 1
            else:
                eggs_b += 1
        else:
            if rng.random() < sa["false"]:
                if forgive > 0:
                    forgive -= 1
                else:
                    eggs_a = max(0, eggs_a - 1)
            if rng.random() < sb["false"]:
                eggs_b = max(0, eggs_b - 1)
        if eggs_a >= 3 or eggs_b >= 3:
            if eggs_a >= 3 and eggs_b >= 3:
                return defender_a
            return eggs_a >= 3
    return defender_a


# --- Кубики -------------------------------------------------------------------
def razbeg_score(rolls):
    total = sum(rolls)
    return 0 if total > 10 else total


def _razbeg_turn(rng, target, rerolls):
    """Бросает, пока сумма < target. Переброс тратится, только чтобы не перебрать."""
    rolls = []
    while sum(rolls) < target:
        roll = d6(rng)
        while sum(rolls) + roll > 10 and rerolls > 0:
            rerolls -= 1
            roll = d6(rng)
        rolls.append(roll)
        if sum(rolls) > 10:
            break
    return razbeg_score(rolls)


def razbeg(k, rng, sa=None, sb=None, per_k=1.0):
    """Скорость. Бросай сколько хочешь, сумма не больше 10, сильный перебрасывает k кубиков."""
    a_first = rng.random() < 0.5
    if a_first:
        a = _razbeg_turn(rng, 7, int(per_k * k))
        b = _razbeg_turn(rng, a + 1 if a else 1, 0)
    else:
        b = _razbeg_turn(rng, 7, 0)
        a = _razbeg_turn(rng, b + 1 if b else 1, int(per_k * k))
    return _compare(a, b, rng)


def lob_v_lob(k, rng, sa=None, sb=None, target=3, per_k=1.0, dice=1):
    """Сила. Кубик + сила, разница двигает метку, до 3 делений."""
    marker = 0
    for _ in range(200):
        roll_a = sum(d6(rng) for _ in range(dice)) + per_k * k
        roll_b = sum(d6(rng) for _ in range(dice))
        marker += roll_a - roll_b
        if marker >= target:
            return True
        if marker <= -target:
            return False
    return rng.random() < 0.5


def grad_kamney(k, rng, sa=None, sb=None, per_die=True, per_k=1.0):
    """Броня. Три кубика урона, броня гасит урон с каждого кубика."""
    dmg_a = sum(max(0, d6(rng) - (k if per_die else 0)) for _ in range(3))
    if not per_die:
        dmg_a = max(0, dmg_a - per_k * k)
    dmg_b = sum(d6(rng) for _ in range(3))
    return _compare(-dmg_a, -dmg_b, rng)


def _shuler_hand(rng, rerolls):
    dice = [d6(rng) for _ in range(3)]
    for _ in range(rerolls):
        dice = [d6(rng) if v <= 3 else v for v in dice]
    return sum(dice)


def kosti_shulera(k, rng, sa=None, sb=None, per_k=1.0):
    """Хитрость. Три кубика и переброс, у хитрого k лишних перебросов."""
    return _compare(_shuler_hand(rng, 1 + int(per_k * k)), _shuler_hand(rng, 1), rng)


# --- Решение ------------------------------------------------------------------
ROUTES = {"длинная": (5, 0), "средняя": (4, 1), "короткая": (3, 2)}


@lru_cache(maxsize=None)
def _route_dist(steps, pits, p_fall=None):
    """Распределение итоговой длины тропы с учётом ям."""
    p_fall = len(PIT_FALL_ON) / 6 if p_fall is None else p_fall
    dist = {}
    for falls in range(pits + 1):
        from math import comb
        p = comb(pits, falls) * p_fall ** falls * (1 - p_fall) ** (pits - falls)
        total = steps + PIT_PENALTY * falls
        dist[total] = dist.get(total, 0) + p
    return tuple(sorted(dist.items()))


def _p_a_wins_route(ra, rb, k, a_defender, mode="steps"):
    sa, pa = ROUTES[ra]
    sb, pb = ROUTES[rb]
    p = 0.0
    if mode == "steps":
        dist_a = _route_dist(max(1, sa - k), pa)
    else:
        dist_a = _route_dist(sa, pa, max(0.0, len(PIT_FALL_ON) / 6 - 0.04 * k))
    for ta, qa in dist_a:
        for tb, qb in _route_dist(sb, pb):
            if ta < tb or (ta == tb and a_defender):
                p += qa * qb
    return p


def korotkaya_doroga(k, rng, sa=None, sb=None, mode="steps"):
    """Скорость. Выбор тропы с ямами; второй видит выбор первого; у быстрого тропа короче на k."""
    a_defender = rng.random() < 0.5
    a_first = rng.random() < 0.5
    names = list(ROUTES)
    if a_first:
        best_a = max(names, key=lambda ra: min(_p_a_wins_route(ra, rb, k, a_defender, mode) for rb in names))
        best_b = min(names, key=lambda rb: _p_a_wins_route(best_a, rb, k, a_defender, mode))
    else:
        best_b = min(names, key=lambda rb: max(_p_a_wins_route(ra, rb, k, a_defender, mode) for ra in names))
        best_a = max(names, key=lambda ra: _p_a_wins_route(ra, best_b, k, a_defender, mode))
    return rng.random() < _p_a_wins_route(best_a, best_b, k, a_defender, mode)


def _rope_safe(t, shift):
    lo, hi = ROPE_SNAP[0] + shift, ROPE_SNAP[1] + shift
    if t <= lo:
        return 1.0
    if t >= hi:
        return 0.0
    return (hi - t) / (hi - lo)


@lru_cache(maxsize=None)
def _rope_equilibrium(k, shift_per_k=ROPE_SHIFT_PER_K):
    """Цена игры «Кто дольше держит» для A при оптимальной игре обоих (фиктивная игра)."""
    grid = [3.0 + 0.1 * i for i in range(int((ROPE_SNAP[1] + shift_per_k * k - 3.0) / 0.1) + 1)]
    shift_a = shift_per_k * k

    def payoff(ta, tb):
        pa, pb = _rope_safe(ta, shift_a), _rope_safe(tb, 0)
        win = pa * (1 - pb) + pa * pb * (1.0 if ta > tb else 0.5 if ta == tb else 0.0)
        win += 0.5 * (1 - pa) * (1 - pb)  # оба сорвались: ничья достаётся защитнику
        return win

    m = [[payoff(ta, tb) for tb in grid] for ta in grid]
    n = len(grid)
    count_a, count_b = [0] * n, [0] * n
    count_a[0] = count_b[0] = 1
    for _ in range(4000):
        tot_b = sum(count_b)
        ia = max(range(n), key=lambda i: sum(m[i][j] * count_b[j] for j in range(n)) / tot_b)
        tot_a = sum(count_a)
        jb = min(range(n), key=lambda j: sum(m[i][j] * count_a[i] for i in range(n)) / tot_a)
        count_a[ia] += 1
        count_b[jb] += 1
    tot_a, tot_b = sum(count_a), sum(count_b)
    return sum(m[i][j] * count_a[i] * count_b[j] for i in range(n) for j in range(n)) / (tot_a * tot_b)


def kto_dolshe_derzhit(k, rng, sa=None, sb=None, shift=None):
    """Сила. Отпусти позже соперника, но до обрыва своего каната; у сильного канат крепче."""
    return rng.random() < _rope_equilibrium(k, ROPE_SHIFT_PER_K if shift is None else shift)


def oblomki_damage(own_plates, opponent_spikes):
    return max(0, opponent_spikes - own_plates)


def _oblomki_value(cards, a_plates, a_spikes, b_plates, b_spikes, a_turn, k, a_defender, memo):
    key = (cards, a_plates, a_spikes, b_plates, b_spikes, a_turn)
    if key in memo:
        return memo[key]
    if not cards:
        da = oblomki_damage(a_plates + k, b_spikes)
        db = oblomki_damage(b_plates, a_spikes)
        result = 1.0 if da < db else 0.0 if da > db else (1.0 if a_defender else 0.0)
    else:
        options = []
        for i, (kind, value) in enumerate(cards):
            rest = cards[:i] + cards[i + 1:]
            if a_turn:
                state = (a_plates + value * (kind == "plate"), a_spikes + value * (kind == "spike"), b_plates, b_spikes)
            else:
                state = (a_plates, a_spikes, b_plates + value * (kind == "plate"), b_spikes + value * (kind == "spike"))
            options.append(_oblomki_value(rest, *state, not a_turn, k, a_defender, memo))
        result = max(options) if a_turn else min(options)
    memo[key] = result
    return result


def oblomki(k, rng, sa=None, sb=None, per_k=1.0):
    """Броня. Шесть открытых карт, по очереди берёте по три; у бронированного k пластин заранее."""
    cards = tuple(sorted((rng.choice(("plate", "spike")), rng.randint(1, 3)) for _ in range(6)))
    a_defender = rng.random() < 0.5
    return _oblomki_value(cards, 0, 0, 0, 0, rng.random() < 0.5, per_k * k, a_defender, {}) > 0.5


def more_less_best_guess_rate():
    """Правило как записано: «больше трёх или меньше», тройка перебрасывается."""
    higher = sum(1 for v in range(1, 7) if v > 3)
    lower = sum(1 for v in range(1, 7) if v < 3)
    return max(higher, lower) / (higher + lower)


def _guess_ok(rng, prev, vs_previous):
    while True:
        roll = d6(rng)
        pivot = prev if vs_previous else 3
        if roll == pivot:
            continue
        higher = sum(1 for v in range(1, 7) if v > pivot)
        lower = sum(1 for v in range(1, 7) if v < pivot)
        guess_higher = higher >= lower
        return (roll > pivot) == guess_higher, roll


def bolshe_menshe(k, rng, sa=None, sb=None, vs_previous=False, lives=1, per_k=1.0):
    """Хитрость. По очереди угадываешь больше или меньше; хитрому прощается k ошибок."""
    lives_a, lives_b = lives + int(per_k * k), lives
    a_turn = rng.random() < 0.5
    prev = d6(rng)
    for _ in range(500):
        ok, prev = _guess_ok(rng, prev, vs_previous)
        if not ok:
            if a_turn:
                lives_a -= 1
                if lives_a <= 0:
                    return False
            else:
                lives_b -= 1
                if lives_b <= 0:
                    return True
        a_turn = not a_turn
    return rng.random() < 0.5


def _compare(a, b, rng):
    if a == b:
        return rng.random() < 0.5  # ничья — защитнику, защитник случайный
    return a > b


FIGHTS = {
    "Забег":             dict(stat="скорость", format="реакция", fn=zabeg),
    "Разбег":            dict(stat="скорость", format="кубики",  fn=razbeg),
    "Короткая дорога":   dict(stat="скорость", format="решение", fn=korotkaya_doroga),
    "Удар хвостом":      dict(stat="сила",     format="реакция", fn=udar_hvostom),
    "Лоб в лоб":         dict(stat="сила",     format="кубики",  fn=lob_v_lob),
    "Кто дольше держит": dict(stat="сила",     format="решение", fn=kto_dolshe_derzhit),
    "Барабан":           dict(stat="броня",    format="реакция", fn=baraban),
    "Град камней":       dict(stat="броня",    format="кубики",  fn=grad_kamney),
    "Обломки":           dict(stat="броня",    format="решение", fn=oblomki),
    "Золотое яйцо":      dict(stat="хитрость", format="реакция", fn=zolotoe_yaitso),
    "Кости шулера":      dict(stat="хитрость", format="кубики",  fn=kosti_shulera),
    "Больше-меньше":     dict(stat="хитрость", format="решение", fn=bolshe_menshe),
}


def win_rate(name, k, n=10000, rng=None, skill_a="regular", skill_b="regular", **kwargs):
    rng = rng or random.Random(0)
    fn = FIGHTS[name]["fn"]
    sa, sb = SKILL[skill_a], SKILL[skill_b]
    wins = sum(1 for _ in range(n) if fn(k, rng, sa, sb, **kwargs))
    return wins / n


# --- Подобранные бонусы: перевес в 5 уровней даёт около 70% --------------------
# k = перевес в уровнях характеристики. Дробные значения — «за каждые N уровней».
CALIBRATED = {
    "Забег":             dict(head=0.7),                      # фора 0,7 нажатия (≈2% дистанции) за уровень
    "Разбег":            dict(per_k=0.5),                     # +1 переброс за каждые 2 уровня
    "Короткая дорога":   dict(mode="pits"),                   # шанс упасть в яму −4% за уровень
    "Удар хвостом":      dict(zone_per_k=0.0065),             # пик шире на 13% за уровень
    "Лоб в лоб":         dict(dice=2, per_k=0.2),             # 2 кубика каждому, +1 к броску за 5 уровней
    "Кто дольше держит": dict(shift=0.4),                     # канат крепче на 0,4 с за уровень
    "Барабан":           dict(base_lives=7, per_k=0.5),       # 7 трещин, +1 за каждые 2 уровня
    "Град камней":       dict(per_die=False, per_k=0.4),      # −1 урон к сумме за каждые 2–3 уровня (−2 при перевесе 5)
    "Обломки":           dict(per_k=0.4),                     # +1 пластина за каждые 2–3 уровня
    "Золотое яйцо":      dict(egg_head=0.34),                 # +1 яйцо форы с перевеса 3 уровня
    "Кости шулера":      dict(per_k=0.4),                     # +1 переброс за каждые 2–3 уровня
    "Больше-меньше":     dict(vs_previous=True, lives=3, per_k=0.34),  # от прошлого броска, 3 ошибки, +1 за 3 уровня
}
