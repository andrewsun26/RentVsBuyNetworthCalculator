import csv
from typing import List, Dict
from Helper import calc_monthly_investment_return_rate
from RentvsBuy import BuyScenario, RentScenario, Assumptions, RentVsBuyCalculator

def read_homeowner_csv() -> List[Dict]:
    """Read the homeowner monthly analysis CSV file"""
    data = []
    with open('homeowner_monthly_analysis.csv', 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # Convert string values to float
            converted_row = {}
            for key, value in row.items():
                try:
                    converted_row[key] = float(value)
                except ValueError:
                    converted_row[key] = value
            data.append(converted_row)
    return data

class RentVsBuyTester:
    """Test class for validating RentVsBuy calculations using provided scenarios and assumptions"""
    
    def __init__(self, buy_scenario: BuyScenario, rent_scenario: RentScenario, assumptions: Assumptions):
        self.buy = buy_scenario
        self.rent = rent_scenario
        self.assumptions = assumptions
        self.calculator = RentVsBuyCalculator(buy_scenario, rent_scenario, assumptions)
    
    def calculate_mortgage_equity_percentage(self, remaining_balance: float) -> float:
        """Calculate what percentage of mortgage payment goes to equity (principal)"""
        if remaining_balance <= 0:
            return 0.0
        
        # Calculate monthly payment
        principal = self.buy.purchase_price * (1 - self.buy.down_payment_pct)
        monthly_rate = self.buy.mortgage_rate / 12
        num_payments = self.buy.amortization_years * 12
        
        if monthly_rate == 0:
            monthly_payment = principal / num_payments
        else:
            monthly_payment = principal * (monthly_rate * (1 + monthly_rate) ** num_payments) / \
                             ((1 + monthly_rate) ** num_payments - 1)
        
        # Calculate interest portion of current payment
        interest_payment = remaining_balance * monthly_rate
        
        # Principal portion is the equity portion
        principal_payment = monthly_payment - interest_payment
        
        # Return equity percentage
        return principal_payment / monthly_payment if monthly_payment > 0 else 0.0

    def test_homeowner_calculations(self):
        """Test homeowner calculations from CSV data using the provided assumptions"""
        data = read_homeowner_csv()
        
        monthly_investment_return = calc_monthly_investment_return_rate(self.assumptions.investment_return_rate)
        
        print(f"Testing {len(data)} months of homeowner data...")
        
        for i, row in enumerate(data):
            month = int(row['month'])
            
            # Skip first month (no previous data to compare)
            if month == 0:
                continue
                
            prev_row = data[i-1]
            
            # Test 1: Home equity increase calculation
            home_equity_increase = row['home_equity'] - prev_row['home_equity']
            cost_mortgage = row['cost_mortgage']
            
            # Calculate remaining balance for equity percentage calculation
            # Home equity = home_valuation - remaining_balance
            # So remaining_balance = home_valuation - home_equity
            remaining_balance = row['home_valuation'] - row['home_equity']
            prev_remaining_balance = prev_row['home_valuation'] - prev_row['home_equity']
            
            # Calculate equity percentage of mortgage payment
            equity_percentage = self.calculate_mortgage_equity_percentage(prev_remaining_balance)
            
            expected_equity_from_mortgage = cost_mortgage * equity_percentage
            
            # Also account for home appreciation
            home_appreciation = row['home_valuation'] - prev_row['home_valuation']
            expected_total_equity_increase = expected_equity_from_mortgage + home_appreciation
            
            # Allow for small rounding differences
            equity_diff = abs(home_equity_increase - expected_total_equity_increase)
            assert equity_diff < 1.0, (
                f"Month {month}: Home equity increase mismatch. "
                f"Expected: {expected_total_equity_increase:.2f}, "
                f"Actual: {home_equity_increase:.2f}, "
                f"Difference: {equity_diff:.2f}"
            )
            
            # Test 2: Net worth increase calculation
            networth_increase = row['networth'] - prev_row['networth']
            
            # Calculate expected net worth increase
            after_tax_income = row['after_tax_income']
            total_housing_costs = (row['cost_mortgage'] + row['monthly_property_tax'] + 
                                 row['monthly_maintenance'] + row['home_insurance'] + 
                                 row['hoa_fees'])
            non_housing_cost = row['non_housing_cost']
            
            # Portfolio growth from previous month
            prev_portfolio = prev_row['portfolio_value']
            portfolio_investment_gain = prev_portfolio * monthly_investment_return
            
            # Cash flow available for investment
            excess_cash_flow = after_tax_income - total_housing_costs - non_housing_cost
            
            # Expected net worth increase = portfolio gain + excess cash flow + home equity increase
            expected_networth_increase = (portfolio_investment_gain + excess_cash_flow + 
                                        home_equity_increase)
            
            # Allow for small rounding differences
            networth_diff = abs(networth_increase - expected_networth_increase)
            assert networth_diff < 2.0, (
                f"Month {month}: Net worth increase mismatch. "
                f"Expected: {expected_networth_increase:.2f}, "
                f"Actual: {networth_increase:.2f}, "
                f"Difference: {networth_diff:.2f}, "
                f"Components - Portfolio gain: {portfolio_investment_gain:.2f}, "
                f"Excess cash: {excess_cash_flow:.2f}, "
                f"Equity increase: {home_equity_increase:.2f}"
            )
            
            # Additional verification: Portfolio value calculation
            expected_portfolio = prev_portfolio + portfolio_investment_gain + excess_cash_flow
            portfolio_diff = abs(row['portfolio_value'] - expected_portfolio)
            
            # For the final month, account for capital gains tax
            if month == len(data) - 1:
                # Final month has capital gains tax applied, so we expect a difference
                pass
            else:
                assert portfolio_diff < 1.0, (
                    f"Month {month}: Portfolio value mismatch. "
                    f"Expected: {expected_portfolio:.2f}, "
                    f"Actual: {row['portfolio_value']:.2f}, "
                    f"Difference: {portfolio_diff:.2f}"
                )
        
        print("All homeowner calculations verified successfully!")

    def test_portfolio_gain_calculation(self):
        """Test that portfolio gain matches expected investment return using the provided assumptions"""
        data = read_homeowner_csv()
        monthly_return = calc_monthly_investment_return_rate(self.assumptions.investment_return_rate)
        
        for i, row in enumerate(data):
            month = int(row['month'])
            
            # Skip first month (no previous portfolio to gain from)
            if month == 0:
                assert row['portfolio_gain'] == 0, f"Month 0 should have 0 portfolio gain"
                continue
                
            prev_row = data[i-1]
            expected_gain = prev_row['portfolio_value'] * monthly_return
            actual_gain = row['portfolio_gain']
            
            # Allow for small rounding differences
            gain_diff = abs(actual_gain - expected_gain)
            assert gain_diff < 0.1, (
                f"Month {month}: Portfolio gain mismatch. "
                f"Expected: {expected_gain:.2f}, "
                f"Actual: {actual_gain:.2f}, "
                f"Previous portfolio: {prev_row['portfolio_value']:.2f}"
            )

    def test_mortgage_payment_calculation(self):
        """Test that the mortgage payment calculation matches expected values"""
        expected_payment = self.calculator.calculate_mortgage_payment()
        
        # Verify against manual calculation
        principal = self.buy.purchase_price * (1 - self.buy.down_payment_pct)
        monthly_rate = self.buy.mortgage_rate / 12
        num_payments = self.buy.amortization_years * 12
        
        if monthly_rate == 0:
            manual_payment = principal / num_payments
        else:
            manual_payment = principal * (monthly_rate * (1 + monthly_rate) ** num_payments) / \
                           ((1 + monthly_rate) ** num_payments - 1)
        
        assert abs(expected_payment - manual_payment) < 0.01, (
            f"Mortgage payment calculation mismatch. "
            f"Calculator: {expected_payment:.2f}, "
            f"Manual: {manual_payment:.2f}"
        )
        
        print(f"Mortgage payment calculation verified: ${expected_payment:.2f}/month")

    def run_all_tests(self):
        """Run all tests using the provided scenarios and assumptions"""
        print("=== RUNNING RENT VS BUY TESTS ===")
        print(f"Purchase Price: ${self.buy.purchase_price:,.0f}")
        print(f"Mortgage Rate: {self.buy.mortgage_rate:.2%}")
        print(f"Investment Return: {self.assumptions.investment_return_rate:.1%}")
        print(f"Time Horizon: {self.assumptions.time_horizon_years} years")
        print()
        
        self.test_mortgage_payment_calculation()
        self.test_homeowner_calculations()
        self.test_portfolio_gain_calculation()
        
        print("All tests passed successfully!")

# Legacy functions for backward compatibility
def calculate_mortgage_equity_percentage(mortgage_rate: float, amortization_years: int, 
                                       remaining_balance: float, purchase_price: float) -> float:
    """Legacy function - use RentVsBuyTester.calculate_mortgage_equity_percentage instead"""
    # Create a temporary buy scenario for the calculation
    buy_scenario = BuyScenario(
        purchase_price=purchase_price,
        down_payment_pct=0.2,
        mortgage_rate=mortgage_rate,
        amortization_years=amortization_years,
        property_tax_rate=0.0085,
        maintenance_cost_pct=0.005,
        home_insurance_monthly=0,
        hoa_monthly=0,
        home_appreciation_rate=0.02,
        selling_cost_pct=0.06,
        primary_home_exclusion_dollars=500_000
    )
    
    rent_scenario = RentScenario(
        monthly_rent=2000,
        renters_insurance_monthly=0,
        rent_increase_rate=0.03
    )
    
    assumptions = Assumptions(
        income=700_000,
        annual_non_housing_spending=73_000,
        time_horizon_years=10,
        investment_tax_enabled=True,
        filing_status=None,
        inflation_rate=0.025,
        investment_return_rate=0.09,
        income_growth_rate=0.05,
        starting_net_worth=700_000
    )
    
    tester = RentVsBuyTester(buy_scenario, rent_scenario, assumptions)
    return tester.calculate_mortgage_equity_percentage(remaining_balance)

def test_homeowner_calculations():
    """Legacy function - use RentVsBuyTester.test_homeowner_calculations instead"""
    # Use the same example scenario from RentvsBuy.py
    from RentvsBuy import FilingStatus
    
    buy_scenario = BuyScenario(
        purchase_price=700_000,
        down_payment_pct=0.2,
        mortgage_rate=0.0425,
        amortization_years=30,
        property_tax_rate=0.0085,
        maintenance_cost_pct=0.005,
        home_insurance_monthly=0,
        hoa_monthly=550,
        home_appreciation_rate=0.02,
        selling_cost_pct=0.06,
        primary_home_exclusion_dollars=500_000
    )
    
    rent_scenario = RentScenario(
        monthly_rent=2000,
        renters_insurance_monthly=0,
        rent_increase_rate=0.03
    )
    
    assumptions = Assumptions(
        income=700_000,
        annual_non_housing_spending=73_000,
        time_horizon_years=10,
        investment_tax_enabled=True,
        filing_status=FilingStatus.MARRIED_FILING_JOINTLY,
        inflation_rate=0.025,
        investment_return_rate=0.09,
        income_growth_rate=0.05,
        starting_net_worth=700_000
    )
    
    tester = RentVsBuyTester(buy_scenario, rent_scenario, assumptions)
    tester.test_homeowner_calculations()

def test_portfolio_gain_calculation():
    """Legacy function - use RentVsBuyTester.test_portfolio_gain_calculation instead"""
    from RentvsBuy import FilingStatus
    
    buy_scenario = BuyScenario(
        purchase_price=700_000,
        down_payment_pct=0.2,
        mortgage_rate=0.0425,
        amortization_years=30,
        property_tax_rate=0.0085,
        maintenance_cost_pct=0.005,
        home_insurance_monthly=0,
        hoa_monthly=550,
        home_appreciation_rate=0.02,
        selling_cost_pct=0.06,
        primary_home_exclusion_dollars=500_000
    )
    
    rent_scenario = RentScenario(
        monthly_rent=2000,
        renters_insurance_monthly=0,
        rent_increase_rate=0.03
    )
    
    assumptions = Assumptions(
        income=700_000,
        annual_non_housing_spending=73_000,
        time_horizon_years=10,
        investment_tax_enabled=True,
        filing_status=FilingStatus.MARRIED_FILING_JOINTLY,
        inflation_rate=0.025,
        investment_return_rate=0.09,
        income_growth_rate=0.05,
        starting_net_worth=700_000
    )
    
    tester = RentVsBuyTester(buy_scenario, rent_scenario, assumptions)
    tester.test_portfolio_gain_calculation()

if __name__ == "__main__":
    # Import the example scenarios from RentvsBuy.py
    from RentvsBuy import FilingStatus
    
    # Use the same example scenario from RentvsBuy.py
    buy_scenario = BuyScenario(
        purchase_price=700_000,
        down_payment_pct=0.2,
        mortgage_rate=0.0425,
        amortization_years=30,
        property_tax_rate=0.0085,
        maintenance_cost_pct=0.005,
        home_insurance_monthly=0,
        hoa_monthly=550,
        home_appreciation_rate=0.02,
        selling_cost_pct=0.06,
        primary_home_exclusion_dollars=500_000
    )
    
    rent_scenario = RentScenario(
        monthly_rent=2000,
        renters_insurance_monthly=0,
        rent_increase_rate=0.03
    )
    
    assumptions = Assumptions(
        income=700_000,
        annual_non_housing_spending=73_000,
        time_horizon_years=10,
        investment_tax_enabled=True,
        filing_status=FilingStatus.MARRIED_FILING_JOINTLY,
        inflation_rate=0.025,
        investment_return_rate=0.09,
        income_growth_rate=0.05,
        starting_net_worth=700_000
    )
    
    # Create and run the tester
    tester = RentVsBuyTester(buy_scenario, rent_scenario, assumptions)
    tester.run_all_tests() 