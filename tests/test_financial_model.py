"""Independent invariant checks for the publishable case study."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from verify_models import (Assumptions, portfolio_audit, npv_closed_form,
                           npv_year_by_year, scenarios, summarize)


class FinancialModelTests(unittest.TestCase):
    def test_unique_optimum(self):
        found=portfolio_audit()
        self.assertEqual(found["optimal_npv_usd"],597325)
        self.assertEqual(found["selected_cost_usd"],4860832)
        self.assertEqual(found["optimal_projects"],["A","B","C","D","H","J"])
        self.assertEqual(found["feasible_portfolios"],451)

    def test_original_baseline_cashflow(self):
        a=Assumptions()
        baseline=npv_closed_form(a.baseline_volume,a.baseline_price,a.baseline_variable)
        self.assertAlmostEqual(baseline,-193822.72953132878,places=6)
        self.assertAlmostEqual(a.terminal_after_tax,515000)

    def test_discounted_cashflow_implementations_agree(self):
        for v,p,c in [(125000,2.25,.65),(200000,2.50,.55),(250000,3.0,.62),(0,0,.65)]:
            self.assertAlmostEqual(npv_closed_form(v,p,c),npv_year_by_year(v,p,c),places=6)

    def test_simulation_determinism(self):
        a=list(scenarios())
        b=list(scenarios())
        self.assertEqual(a,b)
        self.assertEqual(len(a),500)
        self.assertTrue(all(.55<=x['variable_cost_fraction']<=.65 for x in a))
        self.assertTrue(all(x['year1_volume_lbs']>=0 and x['price_per_lb_usd']>=0 for x in a))
        self.assertEqual(summarize(a),summarize(b))

if __name__=="__main__":
    unittest.main()
