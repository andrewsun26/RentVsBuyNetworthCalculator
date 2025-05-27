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
class RentOutScenario:
    current_property_value: float  # Current market value of the property
    monthly_rental_income: float  # Expected monthly rental income
    rental_income_growth_rate: float  # Annual growth rate of rental income
    property_management_fee_pct: float  # Property management fee as % of rental income
    vacancy_rate: float  # Expected vacancy rate (e.g., 0.05 for 5% vacancy)
    rental_property_tax_rate: float  # Annual property tax rate
    rental_maintenance_cost_pct: float  # Annual maintenance cost as % of property value
    rental_insurance_monthly: float  # Monthly landlord insurance cost
    rental_appreciation_rate: float  # Annual property appreciation rate

@dataclass
class SellScenario:
    current_property_value: float  # Current market value of the property
    selling_cost_pct: float  # Total cost to sell (realtor fees, closing costs, etc.)
    capital_gains_exclusion: float  # Capital gains exclusion if applicable
    original_purchase_price: float  # Original purchase price for capital gains calculation

@dataclass
class RentOutVsSellAssumptions:
    income: float  # Annual household income for tax calculations
    time_horizon_years: int  # Analysis period in years
    investment_tax_enabled: bool  # Whether investments are subject to capital gains tax
    filing_status: FilingStatus  # Tax filing status for capital gains brackets
    inflation_rate: float  # Annual inflation rate
    investment_return_rate: float  # Expected annual return on investment portfolio
    income_growth_rate: float  # Annual household income growth rate
    starting_net_worth: float  # Initial net worth (excluding the property in question)
    annual_non_housing_spending: float  # Annual spending on non-housing expenses
    new_monthly_rent: float  # Monthly rent for new place to live
    new_rent_increase_rate: float  # Annual rent increase rate for new place
    new_renters_insurance_monthly: float  # Monthly renters insurance for new place

class RentOutVsSellCalculator:
    def __init__(self, rent_out_scenario: RentOutScenario, sell_scenario: SellScenario, assumptions: RentOutVsSellAssumptions):
        self.rent_out = rent_out_scenario
        self.sell = sell_scenario
        self.assumptions = assumptions
        
        # Validate that both scenarios use the same property value
        if abs(self.rent_out.current_property_value - self.sell.current_property_value) > 1:
            raise ValueError("Rent out and sell scenarios must use the same current property value")
    
    def calc_property_capital_gains_tax(self, sale_price: float, original_purchase_price: float, exclusion: float) -> float:
        """Calculate capital gains tax on property sale with exclusion."""
        if not self.assumptions.investment_tax_enabled:
            return 0
            
        gains = sale_price - original_purchase_price
        taxable_gains = max(0, gains - exclusion)
        
        effective_rate = calc_long_term_cap_gains_tax_rate(taxable_gains, self.assumptions.filing_status)
        return taxable_gains * effective_rate
    
    def calculate_monthly_new_rent_costs(self, month: int) -> float:
        """Calculate monthly cost of renting new place to live"""
        years_elapsed = month // 12
        current_rent = self.assumptions.new_monthly_rent * (1 + self.assumptions.new_rent_increase_rate) ** years_elapsed
        
        inflation_factor = get_inflation_factor(month, self.assumptions.inflation_rate)
        current_insurance = self.assumptions.new_renters_insurance_monthly * inflation_factor
        
        return current_rent + current_insurance
    
    def calculate_monthly_rental_property_costs(self, month: int) -> float:
        """Calculate monthly costs of owning rental property"""
        years_elapsed = month // 12
        
        # Current property value with appreciation
        current_property_value = self.rent_out.current_property_value * (1 + self.rent_out.rental_appreciation_rate) ** years_elapsed
        
        # Property tax based on current value
        monthly_property_tax = (current_property_value * self.rent_out.rental_property_tax_rate) / 12
        
        # Maintenance cost based on current value
        monthly_maintenance = (current_property_value * self.rent_out.rental_maintenance_cost_pct) / 12
        
        # Apply inflation
        inflation_factor = get_inflation_factor(month, self.assumptions.inflation_rate)
        monthly_property_tax *= inflation_factor
        monthly_maintenance *= inflation_factor
        rental_insurance = self.rent_out.rental_insurance_monthly * inflation_factor
        
        return monthly_property_tax + monthly_maintenance + rental_insurance
    
    def calculate_monthly_rental_income(self, month: int) -> float:
        """Calculate net monthly rental income after expenses"""
        years_elapsed = month // 12
        
        # Gross rental income with growth
        gross_rental_income = self.rent_out.monthly_rental_income * (1 + self.rent_out.rental_income_growth_rate) ** years_elapsed
        
        # Account for vacancy
        effective_rental_income = gross_rental_income * (1 - self.rent_out.vacancy_rate)
        
        # Property management fees
        management_fees = effective_rental_income * self.rent_out.property_management_fee_pct
        
        # Property costs
        property_costs = self.calculate_monthly_rental_property_costs(month)
        
        # Net rental income
        net_rental_income = effective_rental_income - management_fees - property_costs
        
        return net_rental_income
    
    def calc_rent_out_net_worth(self) -> Tuple[List[Dict], float, float]:
        """Calculate net worth when renting out the property"""
        initial_portfolio = self.assumptions.starting_net_worth
        monthly_return = calc_monthly_investment_return_rate(self.assumptions.investment_return_rate)
        base_monthly_non_housing_spending = self.assumptions.annual_non_housing_spending / 12
        
        portfolio_values = [initial_portfolio]
        results = []
        
        for month in range(self.assumptions.time_horizon_years * 12):
            years_elapsed = month // 12
            
            # Income calculations
            monthly_gross_income = calc_monthly_gross_income(month, self.assumptions.income, self.assumptions.income_growth_rate)
            monthly_after_tax_income = calc_monthly_after_tax_income(month, self.assumptions.income, self.assumptions.income_growth_rate)
            
            # Current property value
            current_property_value = self.rent_out.current_property_value * (1 + self.rent_out.rental_appreciation_rate) ** years_elapsed
            
            # Rental income and costs
            net_rental_income = self.calculate_monthly_rental_income(month)
            new_rent_costs = self.calculate_monthly_new_rent_costs(month)
            
            # Apply inflation to non-housing spending
            inflation_factor = get_inflation_factor(month, self.assumptions.inflation_rate)
            monthly_non_housing_spending = base_monthly_non_housing_spending * inflation_factor
            
            # Total monthly cash flow
            total_monthly_income = monthly_after_tax_income + net_rental_income
            total_monthly_costs = new_rent_costs + monthly_non_housing_spending
            excess_cash_flow = total_monthly_income - total_monthly_costs
            
            # Portfolio growth
            prev_portfolio = portfolio_values[-1]
            new_portfolio = prev_portfolio * (1 + monthly_return) + excess_cash_flow
            portfolio_values.append(new_portfolio)
            
            # For final month, apply capital gains tax
            if month == self.assumptions.time_horizon_years * 12 - 1:
                portfolio_capital_gains_tax = calc_capital_gains_tax(
                    new_portfolio, initial_portfolio, self.assumptions.investment_tax_enabled, self.assumptions.filing_status
                )
                portfolio_value = new_portfolio - portfolio_capital_gains_tax
                property_value = current_property_value  # Keep property, no selling costs
                property_capital_gains_tax = 0
            else:
                portfolio_value = new_portfolio
                property_value = current_property_value
                portfolio_capital_gains_tax = 0
                property_capital_gains_tax = 0
            
            total_net_worth = portfolio_value + property_value
            
            results.append({
                'month': month,
                'year': years_elapsed,
                'portfolio_value': portfolio_value,
                'property_value': property_value,
                'total_net_worth': total_net_worth,
                'gross_income': monthly_gross_income,
                'after_tax_income': monthly_after_tax_income,
                'net_rental_income': net_rental_income,
                'new_rent_costs': new_rent_costs,
                'non_housing_cost': monthly_non_housing_spending,
                'excess_cash_flow': excess_cash_flow
            })
        
        return results, portfolio_capital_gains_tax, property_capital_gains_tax
    
    def calc_sell_net_worth(self) -> Tuple[List[Dict], float, float]:
        """Calculate net worth when selling the property"""
        # Calculate proceeds from sale
        sale_price = self.sell.current_property_value
        selling_costs = sale_price * self.sell.selling_cost_pct
        property_capital_gains_tax = self.calc_property_capital_gains_tax(
            sale_price, self.sell.original_purchase_price, self.sell.capital_gains_exclusion
        )
        net_proceeds = sale_price - selling_costs - property_capital_gains_tax
        
        initial_portfolio = self.assumptions.starting_net_worth + net_proceeds
        monthly_return = calc_monthly_investment_return_rate(self.assumptions.investment_return_rate)
        base_monthly_non_housing_spending = self.assumptions.annual_non_housing_spending / 12
        
        portfolio_values = [initial_portfolio]
        results = []
        
        for month in range(self.assumptions.time_horizon_years * 12):
            years_elapsed = month // 12
            
            # Income calculations
            monthly_gross_income = calc_monthly_gross_income(month, self.assumptions.income, self.assumptions.income_growth_rate)
            monthly_after_tax_income = calc_monthly_after_tax_income(month, self.assumptions.income, self.assumptions.income_growth_rate)
            
            # Costs (only new rent, no property ownership costs)
            new_rent_costs = self.calculate_monthly_new_rent_costs(month)
            
            # Apply inflation to non-housing spending
            inflation_factor = get_inflation_factor(month, self.assumptions.inflation_rate)
            monthly_non_housing_spending = base_monthly_non_housing_spending * inflation_factor
            
            # Total monthly cash flow
            total_monthly_costs = new_rent_costs + monthly_non_housing_spending
            excess_cash_flow = monthly_after_tax_income - total_monthly_costs
            
            # Portfolio growth
            prev_portfolio = portfolio_values[-1]
            new_portfolio = prev_portfolio * (1 + monthly_return) + excess_cash_flow
            portfolio_values.append(new_portfolio)
            
            # For final month, apply capital gains tax
            if month == self.assumptions.time_horizon_years * 12 - 1:
                portfolio_capital_gains_tax = calc_capital_gains_tax(
                    new_portfolio, initial_portfolio, self.assumptions.investment_tax_enabled, self.assumptions.filing_status
                )
                portfolio_value = new_portfolio - portfolio_capital_gains_tax
            else:
                portfolio_value = new_portfolio
                portfolio_capital_gains_tax = 0
            
            total_net_worth = portfolio_value  # No property value since we sold it
            
            results.append({
                'month': month,
                'year': years_elapsed,
                'portfolio_value': portfolio_value,
                'total_net_worth': total_net_worth,
                'gross_income': monthly_gross_income,
                'after_tax_income': monthly_after_tax_income,
                'new_rent_costs': new_rent_costs,
                'non_housing_cost': monthly_non_housing_spending,
                'excess_cash_flow': excess_cash_flow
            })
        
        return results, portfolio_capital_gains_tax, property_capital_gains_tax
    
    def run_analysis(self) -> Dict:
        """Run complete rent out vs sell analysis"""
        rent_out_data, rent_out_portfolio_tax, rent_out_property_tax = self.calc_rent_out_net_worth()
        sell_data, sell_portfolio_tax, sell_property_tax = self.calc_sell_net_worth()
        
        # Calculate month-by-month comparison
        monthly_comparison = []
        
        for month in range(len(rent_out_data)):
            rent_out_total = rent_out_data[month]['total_net_worth']
            sell_total = sell_data[month]['total_net_worth']
            
            monthly_comparison.append({
                'month': month,
                'rent_out': {
                    'portfolio_value': rent_out_data[month]['portfolio_value'],
                    'property_value': rent_out_data[month]['property_value'],
                    'total_net_worth': rent_out_total
                },
                'sell': {
                    'portfolio_value': sell_data[month]['portfolio_value'],
                    'total_net_worth': sell_total
                },
                'net_worth_difference': rent_out_total - sell_total,
                'winner': 'Rent Out' if rent_out_total > sell_total else 'Sell'
            })
        
        # Summary statistics
        final_month = monthly_comparison[-1]
        
        return {
            'monthly_comparison': monthly_comparison,
            'summary': {
                'time_horizon_years': self.assumptions.time_horizon_years,
                'final_rent_out_net_worth': final_month['rent_out']['total_net_worth'],
                'final_sell_net_worth': final_month['sell']['total_net_worth'],
                'final_net_worth_difference': final_month['net_worth_difference'],
                'final_winner': final_month['winner'],
                'rent_out_portfolio_capital_gains_tax': rent_out_portfolio_tax,
                'rent_out_property_capital_gains_tax': rent_out_property_tax,
                'sell_portfolio_capital_gains_tax': sell_portfolio_tax,
                'sell_property_capital_gains_tax': sell_property_tax,
                'rent_out_breakdown': {
                    'final_portfolio_value': final_month['rent_out']['portfolio_value'],
                    'final_property_value': final_month['rent_out']['property_value']
                },
                'sell_breakdown': {
                    'final_portfolio_value': final_month['sell']['portfolio_value']
                }
            }
        }
    
    def print_results(self, results):
        print("=== RENT OUT VS SELL ANALYSIS ===")
        print()
        
        print("=== RENT OUT SCENARIO ===")
        print(f"Current Property Value:      ${self.rent_out.current_property_value:,.0f}")
        print(f"Monthly Rental Income:       ${self.rent_out.monthly_rental_income:,.0f}")
        print(f"Rental Income Growth Rate:   {self.rent_out.rental_income_growth_rate:.2%}")
        print(f"Property Management Fee:     {self.rent_out.property_management_fee_pct:.1%}")
        print(f"Vacancy Rate:                {self.rent_out.vacancy_rate:.1%}")
        print(f"Property Tax Rate:           {self.rent_out.rental_property_tax_rate:.2%}")
        print(f"Maintenance Cost:            {self.rent_out.rental_maintenance_cost_pct:.2%}")
        print(f"Landlord Insurance:          ${self.rent_out.rental_insurance_monthly:,.0f}/month")
        print(f"Property Appreciation Rate:  {self.rent_out.rental_appreciation_rate:.2%}")
        print()
        
        print("=== SELL SCENARIO ===")
        print(f"Current Property Value:      ${self.sell.current_property_value:,.0f}")
        print(f"Selling Cost:                {self.sell.selling_cost_pct:.1%}")
        print(f"Capital Gains Exclusion:     ${self.sell.capital_gains_exclusion:,.0f}")
        print(f"Original Purchase Price:     ${self.sell.original_purchase_price:,.0f}")
        print()
        
        print("=== ASSUMPTIONS ===")
        print(f"Annual Income:               ${self.assumptions.income:,.0f}")
        print(f"Annual Non-Housing Spending: ${self.assumptions.annual_non_housing_spending:,.0f}")
        print(f"New Monthly Rent:            ${self.assumptions.new_monthly_rent:,.0f}")
        print(f"New Rent Increase Rate:      {self.assumptions.new_rent_increase_rate:.2%}")
        print(f"Time Horizon:                {self.assumptions.time_horizon_years} years")
        print(f"Investment Tax Enabled:      {self.assumptions.investment_tax_enabled}")
        print(f"Filing Status:               {self.assumptions.filing_status}")
        print(f"Inflation Rate:              {self.assumptions.inflation_rate:.2%}")
        print(f"Investment Return Rate:      {self.assumptions.investment_return_rate:.1%}")
        print(f"Income Growth Rate:          {self.assumptions.income_growth_rate:.1%}")
        print(f"Starting Net Worth:          ${self.assumptions.starting_net_worth:,.0f}")
        print()
        
        # Print results
        summary = results['summary']
        print("=== RESULTS ===")
        print(f"Final Winner:                {summary['final_winner']}")
        print(f"Rent Out Net Worth:          ${summary['final_rent_out_net_worth']:,.0f}")
        print(f"Sell Net Worth:              ${summary['final_sell_net_worth']:,.0f}")
        print(f"Net Worth Difference:        ${summary['final_net_worth_difference']:,.0f}")
        
        # Calculate percentage difference
        if summary['final_sell_net_worth'] != 0:
            percentage_diff = (summary['final_net_worth_difference'] / summary['final_sell_net_worth']) * 100
            print(f"Net Worth Difference (%):    {percentage_diff:+.1f}%")
        
        print()
        
        print("=== RENT OUT BREAKDOWN ===")
        print(f"Final Portfolio Value:       ${summary['rent_out_breakdown']['final_portfolio_value']:,.0f}")
        print(f"Final Property Value:        ${summary['rent_out_breakdown']['final_property_value']:,.0f}")
        print(f"Total Net Worth:             ${summary['final_rent_out_net_worth']:,.0f}")
        print(f"Portfolio Capital Gains Tax: ${summary['rent_out_portfolio_capital_gains_tax']:,.0f}")
        print()
        
        print("=== SELL BREAKDOWN ===")
        print(f"Final Portfolio Value:       ${summary['sell_breakdown']['final_portfolio_value']:,.0f}")
        print(f"Total Net Worth:             ${summary['final_sell_net_worth']:,.0f}")
        print(f"Portfolio Capital Gains Tax: ${summary['sell_portfolio_capital_gains_tax']:,.0f}")
        print(f"Property Capital Gains Tax:  ${summary['sell_property_capital_gains_tax']:,.0f}")
        print()
        
        print(f"Analysis complete for {summary['time_horizon_years']} year time horizon")

# Example usage
if __name__ == "__main__":
    rent_out_scenario = RentOutScenario(
        current_property_value=800_000,
        monthly_rental_income=4_000,
        rental_income_growth_rate=0.03,
        property_management_fee_pct=0.08,  # 8% of rental income
        vacancy_rate=0.05,  # 5% vacancy
        rental_property_tax_rate=0.0085,
        rental_maintenance_cost_pct=0.01,  # 1% of property value annually
        rental_insurance_monthly=200,
        rental_appreciation_rate=0.04
    )
    
    sell_scenario = SellScenario(
        current_property_value=800_000,
        selling_cost_pct=0.06,
        capital_gains_exclusion=500_000,  # $500K for married filing jointly
        original_purchase_price=600_000
    )
    
    assumptions = RentOutVsSellAssumptions(
        income=350_000,
        time_horizon_years=10,
        investment_tax_enabled=True,
        filing_status=FilingStatus.MARRIED_FILING_JOINTLY,
        inflation_rate=0.025,
        investment_return_rate=0.09,
        income_growth_rate=0.05,
        starting_net_worth=200_000,
        annual_non_housing_spending=73_000,
        new_monthly_rent=3_500,
        new_rent_increase_rate=0.03,
        new_renters_insurance_monthly=25
    )
    
    calculator = RentOutVsSellCalculator(rent_out_scenario, sell_scenario, assumptions)
    results = calculator.run_analysis()
    calculator.print_results(results) 