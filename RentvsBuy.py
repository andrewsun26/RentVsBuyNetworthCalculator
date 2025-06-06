from dataclasses import dataclass
from typing import Dict, List, Tuple
import csv
from Helper import (
    FilingStatus, get_inflation_factor, calc_income_tax_rate, calc_long_term_cap_gains_tax_rate,
    calc_after_tax_income, calc_monthly_after_tax_income, calc_monthly_gross_income,
    calc_monthly_investment_return_rate, calc_portfolio_gain, calc_capital_gains_tax,
    calc_home_capital_gains_tax
)

@dataclass
class BuyScenario:
    purchase_price: float
    down_payment_pct: float
    mortgage_rate: float  # Annual
    amortization_years: int
    property_tax_rate: float  # Annual
    maintenance_cost_pct: float  # Annual
    home_insurance_monthly: float
    hoa_monthly: float  # Monthly HOA fees
    home_appreciation_rate: float  # Annual
    selling_cost_pct: float  # Total cost to sell home (realtor fees, closing costs, etc.)
    primary_home_exclusion_dollars: float  # Capital gains exclusion for primary residence

@dataclass
class RentScenario:
    monthly_rent: float
    renters_insurance_monthly: float
    rent_increase_rate: float  # Annual rate of rent increases

@dataclass
class Assumptions:
    income: float  # Annual household income for tax calculations
    time_horizon_years: int  # Analysis period in years
    investment_tax_enabled: bool  # Whether renter's investments are subject to capital gains tax
    filing_status: FilingStatus  # Tax filing status for capital gains brackets
    inflation_rate: float  # Annual inflation rate affecting costs and rents
    investment_return_rate: float  # Expected annual return on renter's investment portfolio
    income_growth_rate: float  # Annual household income growth rate
    starting_net_worth: float  # Initial net worth for both scenarios
    annual_non_housing_spending: float  # Annual spending on non-housing expenses

class RentVsBuyCalculator:
    def __init__(self, buy_scenario: BuyScenario, rent_scenario: RentScenario, assumptions: Assumptions):
        self.buy = buy_scenario
        self.rent = rent_scenario
        self.assumptions = assumptions
        
        # Validate that starting net worth is sufficient for down payment
        down_payment = self.buy.purchase_price * self.buy.down_payment_pct
        if self.assumptions.starting_net_worth < down_payment:
            raise ValueError(f"Starting net worth (${self.assumptions.starting_net_worth:,.0f}) is insufficient for down payment (${down_payment:,.0f})")
        
    def calculate_mortgage_payment(self) -> float:
        """Calculate monthly mortgage payment (P&I only)"""
        principal = self.buy.purchase_price * (1 - self.buy.down_payment_pct)
        monthly_rate = self.buy.mortgage_rate / 12
        num_payments = self.buy.amortization_years * 12
        
        if monthly_rate == 0:
            return principal / num_payments
        
        return principal * (monthly_rate * (1 + monthly_rate) ** num_payments) / \
               ((1 + monthly_rate) ** num_payments - 1)
    
    def generate_amortization_schedule(self) -> List[float]:
        """Generate monthly remaining balances for the mortgage"""
        principal = self.buy.purchase_price * (1 - self.buy.down_payment_pct)
        monthly_payment = self.calculate_mortgage_payment()
        monthly_rate = self.buy.mortgage_rate / 12
        
        balances = []
        remaining_balance = principal
        
        for month in range(self.assumptions.time_horizon_years * 12):
            interest_payment = remaining_balance * monthly_rate
            principal_payment = monthly_payment - interest_payment
            remaining_balance -= principal_payment
            
            balances.append(max(0, remaining_balance))
            
            if remaining_balance <= 0:
                break
                
        return balances
    
    def calculate_monthly_ownership_costs(self, month: int) -> float:
        """Calculate total monthly costs of ownership"""
        mortgage_payment = self.calculate_mortgage_payment()
        
        # Calculate current home value based on appreciation
        # Home value after appreciation (annual compounding)
        years_elapsed = month // 12
        current_home_value = self.buy.purchase_price * (1 + self.buy.home_appreciation_rate) ** years_elapsed
        
        # Property tax based on current home value
        monthly_property_tax = (current_home_value * self.buy.property_tax_rate) / 12
        monthly_maintenance = (self.buy.purchase_price * self.buy.maintenance_cost_pct) / 12
        
        # Adjust for inflation
        inflation_factor = get_inflation_factor(month, self.assumptions.inflation_rate)
        monthly_property_tax *= inflation_factor
        monthly_maintenance *= inflation_factor
        home_insurance = self.buy.home_insurance_monthly * inflation_factor
        hoa_fees = self.buy.hoa_monthly * inflation_factor
        
        return mortgage_payment + monthly_property_tax + monthly_maintenance + home_insurance + hoa_fees
    
    def calculate_monthly_rent_costs(self, month: int) -> float:
        """Calculate total monthly costs of renting"""
        # Rent increases annually
        years_elapsed = month // 12
        current_rent = self.rent.monthly_rent * (1 + self.rent.rent_increase_rate) ** years_elapsed
        
        # Insurance increases with inflation
        inflation_factor = get_inflation_factor(month, self.assumptions.inflation_rate)
        current_insurance = self.rent.renters_insurance_monthly * inflation_factor
        
        return current_rent + current_insurance
    
    def calc_portfolio_per_month(self, initial_portfolio: float, monthly_costs_func) -> List[float]:
        """
        Unified method to calculate investment portfolio growth over time.
        
        Args:
            initial_portfolio: Starting portfolio value
            monthly_costs_func: Function to calculate monthly costs (rent or ownership)
        
        Returns:
            List of portfolio values at each month
        """
        portfolio_values = [initial_portfolio]
        monthly_return = calc_monthly_investment_return_rate(self.assumptions.investment_return_rate)
        base_monthly_non_housing_spending = self.assumptions.annual_non_housing_spending / 12
        
        for month in range(self.assumptions.time_horizon_years * 12):
            # Calculate monthly after-tax income using helper method
            current_monthly_income = calc_monthly_after_tax_income(month, self.assumptions.income, self.assumptions.income_growth_rate)
            
            # Calculate monthly costs using the provided function
            monthly_costs = monthly_costs_func(month)
            
            # Apply inflation to non-housing spending
            inflation_factor = get_inflation_factor(month, self.assumptions.inflation_rate)
            monthly_non_housing_spending = base_monthly_non_housing_spending * inflation_factor
            
            # Calculate excess cash flow (income minus housing costs minus non-housing spending)
            excess_cash_flow = current_monthly_income - monthly_costs - monthly_non_housing_spending
            
            # Previous portfolio value grows and we add excess cash flow
            prev_value = portfolio_values[-1]
            new_value = prev_value * (1 + monthly_return) + excess_cash_flow
            portfolio_values.append(new_value)
            
        return portfolio_values
    
    def calc_homeowner_net_worth(self) -> Tuple[List[Dict], float, float]:
        """Calculate homeowner's net worth at each month over the time horizon
        
        Returns:
            Tuple of (monthly_data, portfolio_capital_gains_tax, home_capital_gains_tax)
            where monthly_data contains all details needed for CSV generation
        """
        amortization = self.generate_amortization_schedule()
        down_payment = self.buy.purchase_price * self.buy.down_payment_pct
        initial_portfolio = self.assumptions.starting_net_worth - down_payment
        
        # Get investment portfolio values over time
        portfolio_values = self.calc_portfolio_per_month(initial_portfolio, self.calculate_monthly_ownership_costs)
        
        results = []
        
        for month in range(len(portfolio_values)):
            years_elapsed = month // 12
            
            # Income calculations
            monthly_gross_income = calc_monthly_gross_income(month, self.assumptions.income, self.assumptions.income_growth_rate)
            monthly_after_tax_income = calc_monthly_after_tax_income(month, self.assumptions.income, self.assumptions.income_growth_rate)
            
            # Home value after appreciation (annual compounding)
            current_home_value = self.buy.purchase_price * (1 + self.buy.home_appreciation_rate) ** years_elapsed
            
            # Cost breakdown
            mortgage_payment = self.calculate_mortgage_payment()
            monthly_property_tax = (current_home_value * self.buy.property_tax_rate) / 12
            monthly_maintenance = (self.buy.purchase_price * self.buy.maintenance_cost_pct) / 12
            
            inflation_factor = get_inflation_factor(month, self.assumptions.inflation_rate)
            monthly_property_tax *= inflation_factor
            monthly_maintenance *= inflation_factor
            home_insurance = self.buy.home_insurance_monthly * inflation_factor
            hoa_fees = self.buy.hoa_monthly * inflation_factor
            monthly_non_housing_cost = self.assumptions.annual_non_housing_spending / 12 * inflation_factor
            
            # Portfolio gain (investment return only)
            portfolio_gain = calc_portfolio_gain(month, portfolio_values, self.assumptions.investment_return_rate)
            
            # Remaining mortgage balance
            if month == 0:
                remaining_balance = self.buy.purchase_price * (1 - self.buy.down_payment_pct)
            elif month - 1 < len(amortization):
                remaining_balance = amortization[month - 1]
            else:
                remaining_balance = 0
            # Home equity 
            home_equity = current_home_value - remaining_balance
            
            # For the final month, apply selling costs and capital gains tax
            if month == len(portfolio_values) - 1:
                # Apply selling costs to home
                selling_costs = current_home_value * self.buy.selling_cost_pct
                
                # Apply capital gains tax on home sale
                home_capital_gains_tax = calc_home_capital_gains_tax(
                    current_home_value, self.buy.purchase_price, self.buy.primary_home_exclusion_dollars,
                    self.assumptions.investment_tax_enabled, self.assumptions.filing_status
                )
                
                # Net home equity after selling costs and capital gains tax
                home_equity = current_home_value - remaining_balance - selling_costs - home_capital_gains_tax
                
                # Apply capital gains tax to investment portfolio if enabled
                portfolio_capital_gains_tax = calc_capital_gains_tax(
                    portfolio_values[-1], initial_portfolio, self.assumptions.investment_tax_enabled, self.assumptions.filing_status
                )
                portfolio_value = portfolio_values[-1] - portfolio_capital_gains_tax
            else:
                # No selling costs or capital gains tax for intermediate months
                portfolio_value = portfolio_values[month]
            
            total_net_worth = portfolio_value + home_equity
            
            results.append({
                'month': month,
                'year': years_elapsed,
                'portfolio_value': portfolio_value,
                'home_equity': home_equity,
                'home_valuation': current_home_value,
                'total_net_worth': total_net_worth,
                'portfolio_gain': portfolio_gain,
                'gross_income': monthly_gross_income,
                'after_tax_income': monthly_after_tax_income,
                'cost_mortgage': mortgage_payment,
                'monthly_property_tax': monthly_property_tax,
                'monthly_maintenance': monthly_maintenance,
                'home_insurance': home_insurance,
                'hoa_fees': hoa_fees,
                'non_housing_cost': monthly_non_housing_cost
            })
        
        return results, portfolio_capital_gains_tax, home_capital_gains_tax
    
    def calc_renter_net_worth(self) -> Tuple[List[Dict], float]:
        """Calculate renter's net worth from investment portfolio
        
        Returns:
            Tuple of (monthly_data, capital_gains_tax)
            where monthly_data contains all details needed for CSV generation
        """
        initial_portfolio = self.assumptions.starting_net_worth
        portfolio_values = self.calc_portfolio_per_month(initial_portfolio, self.calculate_monthly_rent_costs)
        
        results = []
        
        for month in range(len(portfolio_values)):
            years_elapsed = month // 12
            
            # Income calculations
            monthly_gross_income = calc_monthly_gross_income(month, self.assumptions.income, self.assumptions.income_growth_rate)
            monthly_after_tax_income = calc_monthly_after_tax_income(month, self.assumptions.income, self.assumptions.income_growth_rate)
            
            # Cost breakdown
            years_elapsed_for_rent = month // 12
            # Apply rent increase rate annually
            current_rent = self.rent.monthly_rent * (1 + self.rent.rent_increase_rate) ** years_elapsed_for_rent
            inflation_factor = get_inflation_factor(month, self.assumptions.inflation_rate)
            current_insurance = self.rent.renters_insurance_monthly * inflation_factor
            monthly_non_housing_cost = self.assumptions.annual_non_housing_spending / 12 * inflation_factor
            
            # Portfolio gain (investment return only)
            portfolio_gain = calc_portfolio_gain(month, portfolio_values, self.assumptions.investment_return_rate)
            
            # Apply capital gains tax only to the final value
            if month == len(portfolio_values) - 1:
                final_portfolio = portfolio_values[month]
                taxes_owed = calc_capital_gains_tax(
                    final_portfolio, initial_portfolio, self.assumptions.investment_tax_enabled, self.assumptions.filing_status
                )
                portfolio_value = final_portfolio - taxes_owed
            else:
                portfolio_value = portfolio_values[month]
            
            results.append({
                'month': month,
                'year': years_elapsed,
                'portfolio_value': portfolio_value,
                'total_net_worth': portfolio_value,
                'portfolio_gain': portfolio_gain,
                'gross_income': monthly_gross_income,
                'after_tax_income': monthly_after_tax_income,
                'cost_rent': current_rent,
                'cost_insurance': current_insurance,
                'non_housing_cost': monthly_non_housing_cost
            })
        
        return results, taxes_owed

    def run_analysis(self) -> Dict:
        """Run complete rent vs buy analysis"""
        # Get month-by-month data for both scenarios
        homeowner_data, portfolio_capital_gains_tax, home_capital_gains_tax = self.calc_homeowner_net_worth()
        renter_portfolio_values, renter_final_taxes = self.calc_renter_net_worth()
        
        # Calculate month-by-month comparison
        monthly_comparison = []
        
        for month in range(len(homeowner_data)):
            homeowner_total = homeowner_data[month]['portfolio_value'] + homeowner_data[month]['home_equity']
            renter_total = renter_portfolio_values[month]['portfolio_value']
            
            monthly_comparison.append({
                'month': month,
                'homeowner': {
                    'portfolio_value': homeowner_data[month]['portfolio_value'],
                    'home_equity': homeowner_data[month]['home_equity'],
                    'total_net_worth': homeowner_total
                },
                'renter': {
                    'portfolio_value': renter_portfolio_values[month]['portfolio_value'],
                    'total_net_worth': renter_total
                },
                'net_worth_difference': homeowner_total - renter_total,
                'winner': 'Homeowner' if homeowner_total > renter_total else 'Renter'
            })
        
        # Summary statistics
        final_month = monthly_comparison[-1]
        
        return {
            'monthly_comparison': monthly_comparison,
            'summary': {
                'time_horizon_years': self.assumptions.time_horizon_years,
                'final_homeowner_net_worth': final_month['homeowner']['total_net_worth'],
                'final_renter_net_worth': final_month['renter']['total_net_worth'],
                'final_net_worth_difference': final_month['net_worth_difference'],
                'final_winner': final_month['winner'],
                'renter_capital_gains_tax_paid': renter_final_taxes,
                'homeowner_capital_gains_tax_portfolio': portfolio_capital_gains_tax,
                'homeowner_capital_gains_tax_home': home_capital_gains_tax,
                'homeowner_breakdown': {
                    'final_portfolio_value': final_month['homeowner']['portfolio_value'],
                    'final_home_equity': final_month['homeowner']['home_equity'],
                    'final_home_valuation': homeowner_data[-1]['home_valuation']
                }
            }
        }

    def print_results(self, results):
        print("=== RENT VS BUY ANALYSIS ===")
        print()
        
        print("=== BUY SCENARIO ===")
        print(f"Purchase Price:              ${self.buy.purchase_price:,.0f}")
        print(f"Down Payment:               {self.buy.down_payment_pct:.1%} (${self.buy.purchase_price * self.buy.down_payment_pct:,.0f})")
        print(f"Mortgage Rate:              {self.buy.mortgage_rate:.2%}")
        print(f"Amortization:               {self.buy.amortization_years} years")
        print(f"Property Tax Rate:          {self.buy.property_tax_rate:.2%}")
        print(f"Maintenance Cost:           {self.buy.maintenance_cost_pct:.2%}")
        print(f"Home Insurance:             ${self.buy.home_insurance_monthly:,.0f}/month")
        print(f"HOA Fees:                   ${self.buy.hoa_monthly:,.0f}/month")
        print(f"Home Appreciation Rate:     {self.buy.home_appreciation_rate:.2%}")
        print(f"Selling Cost:               {self.buy.selling_cost_pct:.1%}")
        print(f"Primary Home Exclusion:     ${self.buy.primary_home_exclusion_dollars:,.0f}")
        print()
        
        print("=== RENT SCENARIO ===")
        print(f"Monthly Rent:               ${self.rent.monthly_rent:,.0f}")
        print(f"Renters Insurance:          ${self.rent.renters_insurance_monthly:,.0f}/month")
        print(f"Rent Increase Rate:         {self.rent.rent_increase_rate:.2%}")
        print()
        
        print("=== ASSUMPTIONS ===")
        print(f"Annual Income:              ${self.assumptions.income:,.0f}")
        print(f"Annual Non-Housing Spending: ${self.assumptions.annual_non_housing_spending:,.0f}")
        print(f"Time Horizon:               {self.assumptions.time_horizon_years} years")
        print(f"Investment Tax Enabled:     {self.assumptions.investment_tax_enabled}")
        print(f"Filing Status:              {self.assumptions.filing_status}")
        print(f"Inflation Rate:             {self.assumptions.inflation_rate:.2%}")
        print(f"Investment Return Rate:     {self.assumptions.investment_return_rate:.1%}")
        print(f"Income Growth Rate:         {self.assumptions.income_growth_rate:.1%}")
        print(f"Starting Net Worth:         ${self.assumptions.starting_net_worth:,.0f}")
        print()
        
        # Print results
        summary = results['summary']
        print("=== RESULTS ===")
        print(f"Final Winner:               {summary['final_winner']}")
        print(f"Homeowner Net Worth:        ${summary['final_homeowner_net_worth']:,.0f}")
        print(f"Renter Net Worth:           ${summary['final_renter_net_worth']:,.0f}")
        print(f"Net Worth Difference:       ${summary['final_net_worth_difference']:,.0f}")
        
        # Calculate percentage difference
        if summary['final_renter_net_worth'] != 0:
            percentage_diff = (summary['final_net_worth_difference'] / summary['final_renter_net_worth']) * 100
            print(f"Net Worth Difference (%):   {percentage_diff:+.1f}%")
        
        print()
        
        print("=== HOMEOWNER BREAKDOWN ===")
        print(f"Final Portfolio Value:      ${summary['homeowner_breakdown']['final_portfolio_value']:,.0f}")
        print(f"Final Home Equity:          ${summary['homeowner_breakdown']['final_home_equity']:,.0f}")
        print(f"Final Home Valuation:        ${summary['homeowner_breakdown']['final_home_valuation']:,.0f}")
        print(f"Total Net Worth:            ${summary['final_homeowner_net_worth']:,.0f}")
        print(f"Capital Gains Tax on Portfolio: ${summary['homeowner_capital_gains_tax_portfolio']:,.0f}")
        print(f"Capital Gains Tax on Home Sale: ${summary['homeowner_capital_gains_tax_home']:,.0f}")
        print()
        
        print("=== RENTER BREAKDOWN ===")
        print(f"Final Portfolio Value (Total Net Worth):      ${summary['final_renter_net_worth']:,.0f}")
        print(f"Capital Gains on Portfolio:     ${summary['renter_capital_gains_tax_paid']:,.0f}")
        print()
        
        # Write detailed monthly data to separate CSV files
        import csv
        
        # Get comprehensive data from core methods (no recomputation needed)
        homeowner_data, _, _ = self.calc_homeowner_net_worth()
        renter_data, _ = self.calc_renter_net_worth()
        
        # Write Homeowner CSV
        with open('homeowner_monthly_analysis.csv', 'w', newline='') as csvfile:
            fieldnames = [
                'month', 'year', 'networth', 'gross_income', 'after_tax_income', 'portfolio_value', 'portfolio_gain', 
                'home_equity', 'home_valuation', 'cost_mortgage', 'monthly_property_tax', 'monthly_maintenance', 
                'home_insurance', 'hoa_fees', 'non_housing_cost'
            ]
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for data in homeowner_data:
                writer.writerow({
                    'month': data['month'],
                    'year': round(data['year'], 2),
                    'networth': round(data['total_net_worth'], 2),
                    'gross_income': round(data['gross_income'], 2),
                    'after_tax_income': round(data['after_tax_income'], 2),
                    'portfolio_value': round(data['portfolio_value'], 2),
                    'portfolio_gain': round(data['portfolio_gain'], 2),
                    'home_equity': round(data['home_equity'], 2),
                    'home_valuation': round(data['home_valuation'], 2),
                    'cost_mortgage': round(data['cost_mortgage'], 2),
                    'monthly_property_tax': round(data['monthly_property_tax'], 2),
                    'monthly_maintenance': round(data['monthly_maintenance'], 2),
                    'home_insurance': round(data['home_insurance'], 2),
                    'hoa_fees': round(data['hoa_fees'], 2),
                    'non_housing_cost': round(data['non_housing_cost'], 2)
                })
        
        # Write Renter CSV
        with open('renter_monthly_analysis.csv', 'w', newline='') as csvfile:
            fieldnames = [
                'month', 'year', 'networth', 'gross_income', 'after_tax_income', 'portfolio_value', 'portfolio_gain', 
                'cost_rent', 'cost_insurance', 'non_housing_cost'
            ]
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for data in renter_data:
                writer.writerow({
                    'month': data['month'],
                    'year': data['year'],
                    'networth': round(data['total_net_worth'], 2),
                    'gross_income': round(data['gross_income'], 2),
                    'after_tax_income': round(data['after_tax_income'], 2),
                    'portfolio_value': round(data['portfolio_value'], 2),
                    'portfolio_gain': round(data['portfolio_gain'], 2),
                    'cost_rent': round(data['cost_rent'], 2),
                    'cost_insurance': round(data['cost_insurance'], 2),
                    'non_housing_cost': round(data['non_housing_cost'], 2)
                })
        
        print(f"Homeowner analysis written to: homeowner_monthly_analysis.csv")
        print(f"Renter analysis written to: renter_monthly_analysis.csv")
        print(f"Total months analyzed: {len(results['monthly_comparison'])}")

# Example usage
if __name__ == "__main__":
    # Example Seattle scenario
    buy_scenario = BuyScenario(
        purchase_price=700_000,
        down_payment_pct=0.2,
        mortgage_rate=0.0425,
        amortization_years=30,
        property_tax_rate=0.0085,  # King County average (0.85% annually)
        maintenance_cost_pct=0.005, # .5% of purchase price annually
        home_insurance_monthly=0,  # Typical Seattle home insurance
        hoa_monthly=550,  # Typical Seattle condo HOA
        home_appreciation_rate=0.02,  # Historical Seattle average
        selling_cost_pct=0.06, # selling agent fee
        primary_home_exclusion_dollars=500_000  # $500K exclusion for married filing jointly
    )
    
    rent_scenario = RentScenario(
        monthly_rent=2000,
        renters_insurance_monthly=0,  # Typical renters insurance
        rent_increase_rate=0.03  # equal to inflation rate
    )
    
    assumptions = Assumptions(
        income=700_000, # household income
        annual_non_housing_spending=73_000,  # all non-housing expenses (food, utilities, etc.)
        time_horizon_years=10, # how long to run the simulation
        investment_tax_enabled=True, # whether to include capital gains tax on investments and home sales
        filing_status=FilingStatus.MARRIED_FILING_JOINTLY,
        inflation_rate=0.025,
        investment_return_rate=0.09, # assumed return on investment if all invested in the stock market
        income_growth_rate=0.05, # assumed growth in gross household income
        starting_net_worth=700_000, # includes down payment in Buy Scenario
    )
    
    calculator = RentVsBuyCalculator(buy_scenario, rent_scenario, assumptions)
    results = calculator.run_analysis()
    calculator.print_results(results)
    
    
    