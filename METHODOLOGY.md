# Methodology and validation notes

## Provenance

The original private course-style workbook (provided by the author) contained project costs and NPVs, a frozen-catfish five-year operating model, and a separate ExcelSim trial report. It also contained personal contact information and legacy executable/add-in-oriented worksheets. This public version is a clean-room model rebuilt from **the hypothetical numbers and cash-flow assumptions**, not a republication of the historical file or a statement about real companies.

## Capital budgeting

The choice is an unweighted binary knapsack problem: maximize sum of supplied project NPVs subject to sum of project initial costs not exceeding $5 million. All ten projects have positive standalone NPVs in the source scenario. The optimal inclusion vector (A through J) is `(1,1,1,1,0,0,0,1,0,1)`.

The independent checker enumerates 1,024 combinations, of which 451 satisfy the cost constraint. The unique optimum has cost **$4,860,832**, total modeled NPV **$597,325**, and residual budget **$139,168**. There are no hidden additional constraints.

All Excel totals are formulas, so changing an inclusion flag immediately updates cost and NPV (it does **not** re-optimize automatically). For a changed budget or project list, rerun a numerical optimizer or update the independent verifier before claiming optimality.

## Operating project risk

Case primitives (USD unless noted): land outlay 250,000; equipment/buildings outlay 400,000; annual depreciation 40,000; horizon 5 years; terminal sale prices of 350,000 for land and 200,000 for equipment; annual volume growth 8%; fixed annual expenses 80,000; flat tax 35%; WACC 10%. The baseline has year-one volume 125,000 lbs, price $2.25/lb, and variable costs of 65% of sales.

For year $t = 1,\ldots,5$:

- Revenue: $R_t = V_1 P (1+g)^{t-1}$.
- Operating cash flow: $CF_t = [R_t(1-v)-F](1-\tau) + D\tau$.
- Land after-tax sale: $350{,}000 - (350{,}000-250{,}000)\times0.35 = 315{,}000$.
- Equipment after-tax sale: $200{,}000-(200{,}000-[400{,}000-5(40{,}000)])\times0.35 = 200{,}000$.
- Final-year after-tax salvage is therefore **515,000**, included separately in the final-year total cash flow; $CF_t$ denotes operating cash flow before salvage.
- NPV: $-650{,}000 + \sum_{t=1}^5 CF_t/(1+0.10)^t + 515{,}000/(1+0.10)^5$.

The original baseline NPV is independently reproduced to floating-point tolerance: **−$193,822.72953132878**. The reference Python implementation uses both discounted annual cash flows and an algebraically equivalent factorized formula, and unit tests check equality.

### Sampling protocol

The 500 draws use Python's `random.Random(2026)` and for each trial independently sample: normal volume `(200000,25000)`, normal price `(2.5,0.5)` and uniform variable-cost fraction `(.55,.65)`. Volume and price values below zero are replaced with zero; the probability of this under the stated parameters is tiny. No correlation is imposed. The project-specific normal and uniform assumptions are *scenarios*, not empirically fitted distributions.

The deterministic output has **mean NPV $98,620.76**, sample SD **$139,652.34**, negative count **132**, sample negative frequency **26.4%**, and NPV interval from the 5th to 95th sample percentile of **−$99,532 to $327,496**. An illustrative normal-approximation 95% confidence interval for negative-NPV frequency is **22.5% to 30.3%**, and does not account for the considerable model uncertainty.

### Historical add-in results

The historical ExcelSim tab records a mean NPV near $80,750.33, SD near $993,167.15, and 245 negative NPVs out of 500. Individual volume/price/variable-cost draws corresponding to its reported trial NPV values were not stored, so they cannot be directly audited against the displayed assumptions and cash-flow model. This public rebuild **does not infer** that the old figures are correct. It replaces them with traceable inputs and equations instead of artificially reproducing summary statistics.

### Limitations

1. The two exercises are separate; do not compare the optimal portfolio NPV with the separate catfish project risk distribution as if they were the same investment.
2. Cash flows implicitly assume immediate use of negative tax benefits; the accounting and tax treatment is simplified.
3. Forecasts do not incorporate empirical price-volume covariance, regulatory effects, working capital, variable financing costs, or operational capacity constraints.
4. The model is an educational worked example. Nothing here constitutes audited financial statements, a company recommendation, or demonstrated professional investment gains.
5. Excel re-computes derived cells from embedded trial inputs. Regenerating new draws in Python requires refreshing the fixed sample columns in the workbook if the distributions are modified.

## Quality-control evidence

- Unique optimum verified by brute-force enumeration, independent of Excel Solver.
- Base cash-flow NPV reproduces private source to <1e-6 USD.
- Algebraic NPV and year-by-year discounted cash-flow calculations agree on every generated scenario.
- 500 fixed-seed trials reproduce exactly across repeated script runs.
- Excel output NPV vector, mean, loss frequency and counts reconcile with the generated CSV (checked separately at build time).
- The rebuilt public workbook contains no personal contact details or linked external files.
