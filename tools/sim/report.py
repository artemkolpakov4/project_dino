"""Пересчитывает таблицы для REPORT.md. Запуск: python3 report.py"""
import random
import statistics

import fights
import match

N_FIGHT = 8000
N_MATCH = 1500


def pct(x):
    return f"{x:.0%}"


def fights_as_written():
    print("| Бой | Характеристика | Формат | k=0 | k=1 | k=2 | k=3 |")
    print("|---|---|---|---|---|---|---|")
    for name, meta in fights.FIGHTS.items():
        row = [fights.win_rate(name, k, n=N_FIGHT, rng=random.Random(100 + k)) for k in range(4)]
        print(f"| {name} | {meta['stat']} | {meta['format']} | " + " | ".join(pct(p) for p in row) + " |")


def fights_calibrated():
    print("| Бой | Δ=0 | Δ=1 | Δ=2 | Δ=3 | Δ=4 | Δ=5 |")
    print("|---|---|---|---|---|---|---|")
    for name, params in fights.CALIBRATED.items():
        row = [fights.win_rate(name, d, n=N_FIGHT, rng=random.Random(300 + d), **params) for d in range(6)]
        print(f"| {name} | " + " | ".join(pct(p) for p in row) + " |")


def reaction_skill_gap():
    print("| Бой | Геймер против новичка | Новичок с перевесом 5 против геймера |")
    print("|---|---|---|")
    for name, meta in fights.FIGHTS.items():
        if meta["format"] != "реакция":
            continue
        params = fights.CALIBRATED[name]
        g = fights.win_rate(name, 0, n=N_FIGHT, rng=random.Random(9), skill_a="gamer", skill_b="casual", **params)
        c = fights.win_rate(name, 5, n=N_FIGHT, rng=random.Random(10), skill_a="casual", skill_b="gamer", **params)
        print(f"| {name} | {pct(g)} | {pct(c)} |")
    both = (4 / 12) * (3 / 11)
    print(f"\nШанс, что рулетка предложит зрителям два боя на реакцию сразу: {both:.0%}.")


def matches():
    print("| Игроков | Обвал, кругов | Минут в среднем | 10–90% партий | Кругов | Грааль взят на круге | Вынос воротами | Сколько раз брали грааль | Боёв игроков | Секунд на ход |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for n in (2, 3, 4):
        for collapse in (5, 9):
            match.COLLAPSE_ROUNDS = collapse
            rs = [match.play(n, random.Random(7000 + s)) for s in range(N_MATCH)]
            mins = sorted(r.minutes for r in rs)
            lo, hi = mins[len(mins) // 10], mins[9 * len(mins) // 10]
            print(f"| {n} | {collapse} | {statistics.mean(mins):.1f} | {lo:.0f}–{hi:.0f} | "
                  f"{statistics.mean(r.rounds for r in rs):.1f} | {statistics.mean(r.first_pickup for r in rs):.1f} | "
                  f"{pct(sum(r.reason == 'ворота' for r in rs) / len(rs))} | {statistics.mean(r.pickups for r in rs):.1f} | "
                  f"{statistics.mean(r.pvp_fights for r in rs):.1f} | {statistics.mean(r.seconds / r.turns for r in rs):.0f} |")
    match.COLLAPSE_ROUNDS = 5


if __name__ == "__main__":
    print("## Бои с бонусами как записано\n"); fights_as_written()
    print("\n## Бои с подобранными бонусами\n"); fights_calibrated()
    print("\n## Реакция и умение\n"); reaction_skill_gap()
    print("\n## Длина партии\n"); matches()
