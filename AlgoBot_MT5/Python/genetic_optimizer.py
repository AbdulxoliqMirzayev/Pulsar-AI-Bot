from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import numpy as np

from backtest_engine import load_csv, run_backtest


PARAMETER_RANGES = {
    "rsi_period": (7, 21, 1),
    "ema_fast": (5, 15, 1),
    "ema_slow": (18, 30, 1),
    "ema_trend": (150, 240, 10),
    "bb_period": (15, 25, 1),
    "bb_stddev": (1.5, 3.0, 0.1),
    "atr_period": (10, 20, 1),
    "atr_multiplier": (1.5, 3.5, 0.1),
    "grid_spacing": (10, 40, 5),
    "ob_lookback": (30, 80, 5),
    "min_score": (6, 14, 1),
    "rr_ratio": (1.2, 3.0, 0.1),
    "risk_per_trade": (0.5, 2.0, 0.1),
}


def choices(rng: tuple[float, float, float]) -> list[float]:
    start, stop, step = rng
    return [round(float(x), 4) for x in np.arange(start, stop + step / 2, step)]


def generate_individual() -> dict[str, float]:
    return {key: random.choice(choices(value)) for key, value in PARAMETER_RANGES.items()}


def fitness(individual: dict[str, float], symbol: str, data=None, days: int = 90) -> float:
    result = run_backtest(symbol=symbol, params=individual, days=days, initial_balance=10000, data=data)
    if result["max_drawdown"] > 20 or result["total_trades"] < 5:
        return -1.0
    return float(result["sharpe_ratio"] * (1 - result["max_drawdown"] / 100) * max(result["win_rate"], 0.01))


def tournament_select(scored: list[tuple[dict[str, float], float]], k: int = 4) -> dict[str, float]:
    sample = random.sample(scored, min(k, len(scored)))
    sample.sort(key=lambda item: item[1], reverse=True)
    return sample[0][0]


def crossover(parent1: dict[str, float], parent2: dict[str, float]) -> dict[str, float]:
    return {key: parent1[key] if random.random() < 0.5 else parent2[key] for key in parent1}


def mutate(individual: dict[str, float], rate: float = 0.15) -> dict[str, float]:
    out = dict(individual)
    for key, rng in PARAMETER_RANGES.items():
        if random.random() < rate:
            out[key] = random.choice(choices(rng))
    return out


def run_genetic_optimizer(
    symbol: str = "EURUSD",
    csv: str | None = None,
    population_size: int = 50,
    generations: int = 100,
    elite_keep: int = 5,
    output: str = "../Models/genetic_best_params.json",
) -> dict[str, float]:
    data = load_csv(csv) if csv else None
    population = [generate_individual() for _ in range(population_size)]
    best: dict[str, float] | None = None
    best_fit = -999.0

    for gen in range(generations):
        scored = [(ind, fitness(ind, symbol, data=data)) for ind in population]
        scored.sort(key=lambda item: item[1], reverse=True)
        if scored[0][1] > best_fit:
            best_fit = scored[0][1]
            best = dict(scored[0][0])
            print(f"Gen {gen}: fitness={best_fit:.5f} params={best}")
        new_pop = [dict(item[0]) for item in scored[:elite_keep]]
        while len(new_pop) < population_size:
            p1 = tournament_select(scored)
            p2 = tournament_select(scored)
            new_pop.append(mutate(crossover(p1, p2)))
        population = new_pop

    result = best or generate_individual()
    result["_fitness"] = best_fit
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="EURUSD")
    parser.add_argument("--csv")
    parser.add_argument("--population", type=int, default=30)
    parser.add_argument("--generations", type=int, default=20)
    parser.add_argument("--output", default="../Models/genetic_best_params.json")
    args = parser.parse_args()
    result = run_genetic_optimizer(args.symbol, args.csv, args.population, args.generations, output=args.output)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
