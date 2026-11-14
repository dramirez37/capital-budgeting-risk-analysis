"""Audit a hypothetical capital-selection case and regenerate 500 risk scenarios.

No third-party packages or external datasets are required. Run from repository root:
    python scripts/verify_models.py
    python -m unittest discover -s tests -v
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from math import sqrt
from pathlib import Path
from random import Random
from statistics import mean, median, stdev
import csv
import json

ROOT = Path(__file__).resolve().parents[1]
SEED = 2026
TRIALS = 500
BUDGET = 5_000_000
PROJECTS = (
    ("A", 922_775, 106_728),
    ("B", 488_486, 50_524),
    ("C", 1_432_913, 244_053),
    ("D", 892_192, 77_709),
    ("E", 166_844, 15_277),
    ("F", 1_159_674, 66_922),
    ("G", 2_697_950, 107_166),
    ("H", 239_625, 69_015),
    ("I", 1_777_453, 52_614),
    ("J", 884_841, 49_296),
)
EXPECTED_OPTIMUM = ("A", "B", "C", "D", "H", "J")


@dataclass(frozen=True)
class Assumptions:
    land_cost: float = 250_000
    equipment_cost: float = 400_000
    depreciation: float = 40_000
    life_years: int = 5
    land_terminal: float = 350_000
    equipment_terminal: float = 200_000
    growth: float = 0.08
    fixed_cost: float = 80_000
    tax_rate: float = 0.35
    wacc: float = 0.10
    sales_mu: float = 200_000
    sales_sigma: float = 25_000
    price_mu: float = 2.50
    price_sigma: float = 0.50
    variable_low: float = 0.55
    variable_high: float = 0.65
    baseline_volume: float = 125_000
    baseline_price: float = 2.25
    baseline_variable: float = 0.65

    @property
    def terminal_after_tax(self) -> float:
        land_gain = self.land_terminal - self.land_cost
        equipment_book_value = self.equipment_cost - self.depreciation * self.life_years
        equipment_gain = self.equipment_terminal - equipment_book_value
        return (self.land_terminal - land_gain * self.tax_rate
                + self.equipment_terminal - equipment_gain * self.tax_rate)

    @property
    def initial_outlay(self) -> float:
        return self.land_cost + self.equipment_cost

    @property
    def annuity_factor(self) -> float:
        return sum((1 + self.wacc) ** (-t) for t in range(1, self.life_years + 1))

    @property
    def revenue_pv_factor(self) -> float:
        return sum(((1 + self.growth) ** (t-1)) / ((1 + self.wacc) ** t)
                   for t in range(1, self.life_years + 1))


def portfolio_audit():
    feasible = []
    for inclusion in product((0, 1), repeat=len(PROJECTS)):
        cost = sum(p[1] * include for p, include in zip(PROJECTS, inclusion))
        if cost <= BUDGET:
            npv = sum(p[2] * include for p, include in zip(PROJECTS, inclusion))
            ids = tuple(p[0] for p, include in zip(PROJECTS, inclusion) if include)
            feasible.append((npv, cost, ids))
    maximum = max(p[0] for p in feasible)
    optimal = [p for p in feasible if p[0] == maximum]
    assert len(optimal) == 1, "Expected a unique capital allocation optimum"
    result = optimal[0]
    assert result[2] == EXPECTED_OPTIMUM, result
    return {"combinations_evaluated": 2 ** len(PROJECTS),
            "feasible_portfolios": len(feasible),
            "optimal_projects": list(result[2]),
            "optimal_npv_usd": result[0],
            "selected_cost_usd": result[1],
            "unspent_budget_usd": BUDGET - result[1],
            "unique_optimum": True}


def npv_closed_form(volume: float, price: float, variable_ratio: float,
                    assumptions: Assumptions = Assumptions()) -> float:
    a = assumptions
    operating_margin_pv = (volume * price * (1-variable_ratio) * (1-a.tax_rate)
                           * a.revenue_pv_factor)
    fixed_and_depreciation_pv = ((-a.fixed_cost * (1-a.tax_rate)
                                   + a.depreciation * a.tax_rate) * a.annuity_factor)
    salvage_pv = a.terminal_after_tax / ((1+a.wacc) ** a.life_years)
    return -a.initial_outlay + operating_margin_pv + fixed_and_depreciation_pv + salvage_pv


def npv_year_by_year(volume: float, price: float, variable_ratio: float,
                     assumptions: Assumptions = Assumptions()) -> float:
    """Independent cash-flow formulation used to cross-check the shortcut."""
    a = assumptions
    total = -a.initial_outlay
    for t in range(1, a.life_years+1):
        revenue = volume*price * (1+a.growth)**(t-1)
        pretax = revenue * (1-variable_ratio) - a.fixed_cost
        aftertax_cf = pretax*(1-a.tax_rate) + a.depreciation*a.tax_rate
        if t == a.life_years:
            aftertax_cf += a.terminal_after_tax
        total += aftertax_cf / ((1+a.wacc)**t)
    return total


def scenarios(assumptions: Assumptions = Assumptions(), seed: int = SEED, n: int = TRIALS):
    rng = Random(seed)
    for trial in range(1, n + 1):
        volume = max(0.0, rng.gauss(assumptions.sales_mu, assumptions.sales_sigma))
        price = max(0.0, rng.gauss(assumptions.price_mu, assumptions.price_sigma))
        variable_ratio = rng.uniform(assumptions.variable_low, assumptions.variable_high)
        npv = npv_closed_form(volume, price, variable_ratio, assumptions)
        assert abs(npv - npv_year_by_year(volume,price,variable_ratio,assumptions)) < 1e-6
        yield {"trial":trial, "year1_volume_lbs":volume, "price_per_lb_usd":price,
               "variable_cost_fraction":variable_ratio, "npv_usd":npv,
               "negative_npv":int(npv<0)}


def quantile(data, prob):
    values = sorted(data)
    point = (len(values)-1)*prob
    lower=int(point)
    weight=point-lower
    if lower==len(values)-1:
        return values[-1]
    return values[lower]*(1-weight)+values[lower+1]*weight


def summarize(data):
    values=[r["npv_usd"] for r in data]
    n=len(values)
    losses=sum(v<0 for v in values)
    p=losses/n
    margin=1.96*sqrt(p*(1-p)/n)
    a=Assumptions()
    return {"seed":SEED,"trials":n,
            "mean_npv_usd":mean(values),"median_npv_usd":median(values),
            "std_npv_usd":stdev(values),"loss_count":losses,
            "loss_fraction":p,"loss_fraction_95ci_normal_approx":[max(0,p-margin),min(1,p+margin)],
            "fifth_percentile_npv_usd":quantile(values,0.05),
            "ninety_fifth_percentile_npv_usd":quantile(values,0.95),
            "min_npv_usd":min(values),"max_npv_usd":max(values),
            "baseline_npv_usd":npv_closed_form(a.baseline_volume,a.baseline_price,a.baseline_variable)}


def run():
    ROOT.joinpath("data").mkdir(parents=True,exist_ok=True)
    optimization=portfolio_audit()
    rows=list(scenarios())
    summary=summarize(rows)
    with (ROOT / "data" / "simulated_scenarios.csv").open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    with (ROOT / "data" / "validation_results.json").open("w",encoding="utf-8") as f:
        json.dump({"optimization":optimization,"simulation":summary},f,indent=2)
        f.write("\n")
    print(json.dumps({"optimization":optimization,"simulation":summary},indent=2))


if __name__ == "__main__":
    run()
