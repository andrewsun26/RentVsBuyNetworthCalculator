#!/usr/bin/env python3
"""
Example demonstrating rent vs buy analysis with comprehensive sensitivity testing.
"""

from RentvsBuy import BuyScenario, RentScenario, Assumptions, RentVsBuyCalculator, get_seattle_defaults
from sensitivity_analysis import SensitivityAnalysis

def main():
    """Run example rent vs buy analysis with sensitivity testing"""
    
    # Get Seattle market defaults
    seattle_defaults = get_seattle_defaults()
    
    # Define scenarios
    buy_scenario = BuyScenario(
        purchase_price=700_000,
        down_payment_pct=0.20,
        mortgage_rate=0.0425,
        amortization_years=30,
        property_tax_rate=seattle_defaults['property_tax_rate'],
        maintenance_cost_pct=seattle_defaults['maintenance_cost_pct'],
        home_insurance_monthly=seattle_defaults['home_insurance_monthly'],
        hoa_monthly=550,  # Typical Seattle condo HOA
        home_appreciation_rate=seattle_defaults['home_appreciation_rate']
    )
    
    rent_scenario = RentScenario(
        monthly_rent=2500,
        renters_insurance_monthly=seattle_defaults['renters_insurance_monthly']
    )
    
    assumptions = Assumptions(
        income=350_000,
        time_horizon_years=10,
        investment_tax_enabled=True,
        long_term_capital_gains_tax_rate=0.15,  # Long term capital gains tax rate up to 600K
        inflation_rate=0.025,
        selling_cost_pct=0.06,
        investment_return_rate=0.09,
        rent_increase_rate=seattle_defaults['rent_increase_rate'],
        income_growth_rate=0.05,
        starting_net_worth=140_000  # Equals down payment needed
    )
    
    # Run basic analysis
    calculator = RentVsBuyCalculator(buy_scenario, rent_scenario, assumptions)
    results = calculator.run_analysis()
    
    # Print basic results
    print("=== RENT VS BUY ANALYSIS RESULTS ===")
    print(f"Starting Net Worth Assumption: ${assumptions.starting_net_worth:,.0f}")
    print(f"Time Horizon: {results['time_horizon_years']} years")
    print(f"Purchase Price: ${results['total_purchase_price']:,.0f}")
    print(f"Down Payment: ${results['down_payment']:,.0f}")
    print(f"Monthly Mortgage Payment: ${results['mortgage_payment']:,.0f}")
    print(f"Monthly HOA Fees: ${results['hoa_monthly']:,.0f}")
    print()
    print(f"Average Monthly Ownership Cost: ${results['avg_monthly_ownership_cost']:,.0f}")
    print(f"Average Monthly Rent Cost: ${results['avg_monthly_rent_cost']:,.0f}")
    print(f"Monthly Cash Flow Difference: ${results['monthly_cash_flow_difference']:,.0f}")
    print()
    print(f"Homeowner Net Worth: ${results['homeowner_net_worth']:,.0f}")
    print(f"Renter Net Worth: ${results['renter_net_worth']:,.0f}")
    print(f"Net Worth Difference: ${results['net_worth_difference']:,.0f}")
    print(f"Winner: {results['winner']}")
    
    # Run sensitivity analysis
    print("\n" + "="*50)
    print("RUNNING SENSITIVITY ANALYSIS...")
    print("="*50)
    
    sensitivity_analyzer = SensitivityAnalysis(buy_scenario, rent_scenario, assumptions)
    sensitivity_results = sensitivity_analyzer.comprehensive_analysis()
    sensitivity_analyzer.print_sensitivity_summary(sensitivity_results)
    sensitivity_analyzer.print_detailed_results(sensitivity_results)

if __name__ == "__main__":
    main() 