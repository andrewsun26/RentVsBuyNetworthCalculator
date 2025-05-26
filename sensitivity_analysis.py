from typing import Dict, List
from RentvsBuy import RentVsBuyCalculator, BuyScenario, RentScenario, Assumptions

class SensitivityAnalysis:
    """Perform sensitivity analysis on rent vs buy calculations"""
    
    def __init__(self, base_buy_scenario: BuyScenario, base_rent_scenario: RentScenario, base_assumptions: Assumptions):
        self.base_buy = base_buy_scenario
        self.base_rent = base_rent_scenario
        self.base_assumptions = base_assumptions
        self.base_calculator = RentVsBuyCalculator(base_buy_scenario, base_rent_scenario, base_assumptions)
        self.base_results = self.base_calculator.run_analysis()
    
    def analyze_parameter(self, parameter_name: str, parameter_range: List[float], scenario_type: str = 'assumptions') -> Dict:
        """Analyze sensitivity to a single parameter
        
        Args:
            parameter_name: Name of the parameter to vary
            parameter_range: List of values to test
            scenario_type: 'buy', 'rent', or 'assumptions'
        """
        results = []
        
        for value in parameter_range:
            try:
                # Create modified scenarios
                buy_scenario = BuyScenario(**self.base_buy.__dict__)
                rent_scenario = RentScenario(**self.base_rent.__dict__)
                assumptions = Assumptions(**self.base_assumptions.__dict__)
                
                # Modify the specific parameter
                if scenario_type == 'buy':
                    setattr(buy_scenario, parameter_name, value)
                elif scenario_type == 'rent':
                    setattr(rent_scenario, parameter_name, value)
                else:  # assumptions
                    setattr(assumptions, parameter_name, value)
                
                # Run analysis
                calculator = RentVsBuyCalculator(buy_scenario, rent_scenario, assumptions)
                result = calculator.run_analysis()
                
                results.append({
                    'parameter_value': value,
                    'net_worth_difference': result['net_worth_difference'],
                    'winner': result['winner'],
                    'homeowner_net_worth': result['homeowner_net_worth'],
                    'renter_net_worth': result['renter_net_worth']
                })
            except ValueError as e:
                # Skip invalid combinations (e.g., starting net worth < down payment)
                continue
        
        return {
            'parameter_name': parameter_name,
            'scenario_type': scenario_type,
            'base_value': getattr(getattr(self, f'base_{scenario_type}'), parameter_name),
            'base_net_worth_difference': self.base_results['net_worth_difference'],
            'results': results
        }
    
    def comprehensive_analysis(self) -> Dict:
        """Run comprehensive sensitivity analysis on key parameters"""
        analyses = {}
        
        # Key parameters to analyze with their ranges
        parameters = {
            'assumptions': {
                'investment_return_rate': [0.04, 0.06, 0.07, 0.08, 0.09, 0.10, 0.12],
                'inflation_rate': [0.01, 0.02, 0.025, 0.03, 0.04],
                'time_horizon_years': [5, 7, 10, 15, 20, 25, 30],
                'starting_net_worth': [140_000, 200_000, 300_000, 500_000, 750_000]  # All above down payment
            },
            'buy': {
                'purchase_price': [500_000, 600_000, 700_000, 800_000, 900_000, 1_000_000],
                'down_payment_pct': [0.05, 0.10, 0.15, 0.20, 0.25, 0.30],
                'mortgage_rate': [0.03, 0.035, 0.04, 0.045, 0.05, 0.055, 0.06, 0.07],
                'home_appreciation_rate': [0.02, 0.03, 0.04, 0.0495, 0.05, 0.06, 0.07],
                'property_tax_rate': [0.005, 0.01, 0.015, 0.02, 0.025, 0.03],
                'hoa_monthly': [0, 200, 400, 550, 700, 1000]
            },
            'rent': {
                'monthly_rent': [1500, 2000, 2500, 3000, 3500, 4000, 4500]
            }
        }
        
        for scenario_type, params in parameters.items():
            for param_name, param_range in params.items():
                analysis_key = f"{scenario_type}_{param_name}"
                analyses[analysis_key] = self.analyze_parameter(param_name, param_range, scenario_type)
        
        return analyses
    
    def find_breakeven_points(self) -> Dict:
        """Find breakeven points for key parameters"""
        breakeven_points = {}
        
        # Find breakeven for investment return rate
        for rate in [i/1000 for i in range(30, 150, 5)]:  # 3% to 15% in 0.5% increments
            try:
                assumptions = Assumptions(**self.base_assumptions.__dict__)
                assumptions.investment_return_rate = rate
                calculator = RentVsBuyCalculator(self.base_buy, self.base_rent, assumptions)
                result = calculator.run_analysis()
                
                if abs(result['net_worth_difference']) < 10000:  # Within $10k
                    breakeven_points['investment_return_rate'] = rate
                    break
            except ValueError:
                continue
        
        # Find breakeven for home appreciation rate
        for rate in [i/1000 for i in range(10, 100, 5)]:  # 1% to 10% in 0.5% increments
            try:
                buy_scenario = BuyScenario(**self.base_buy.__dict__)
                buy_scenario.home_appreciation_rate = rate
                calculator = RentVsBuyCalculator(buy_scenario, self.base_rent, self.base_assumptions)
                result = calculator.run_analysis()
                
                if abs(result['net_worth_difference']) < 10000:  # Within $10k
                    breakeven_points['home_appreciation_rate'] = rate
                    break
            except ValueError:
                continue
        
        # Find breakeven for monthly rent
        for rent in range(1000, 5000, 100):
            try:
                rent_scenario = RentScenario(**self.base_rent.__dict__)
                rent_scenario.monthly_rent = rent
                calculator = RentVsBuyCalculator(self.base_buy, rent_scenario, self.base_assumptions)
                result = calculator.run_analysis()
                
                if abs(result['net_worth_difference']) < 10000:  # Within $10k
                    breakeven_points['monthly_rent'] = rent
                    break
            except ValueError:
                continue
        
        return breakeven_points
    
    def print_sensitivity_summary(self, analyses: Dict):
        """Print a summary of sensitivity analysis results"""
        print("\n=== SENSITIVITY ANALYSIS SUMMARY ===")
        print(f"Base Case Net Worth Difference: ${self.base_results['net_worth_difference']:,.0f}")
        print(f"Base Case Winner: {self.base_results['winner']}")
        print()
        
        # Find most sensitive parameters
        sensitivities = []
        for analysis_key, analysis in analyses.items():
            if len(analysis['results']) > 1:
                min_diff = min(r['net_worth_difference'] for r in analysis['results'])
                max_diff = max(r['net_worth_difference'] for r in analysis['results'])
                sensitivity = max_diff - min_diff
                sensitivities.append((analysis_key, sensitivity, analysis))
        
        # Sort by sensitivity (highest impact first)
        sensitivities.sort(key=lambda x: x[1], reverse=True)
        
        print("Most Sensitive Parameters (by net worth impact):")
        for i, (param_name, sensitivity, analysis) in enumerate(sensitivities[:10]):
            print(f"{i+1:2d}. {param_name.replace('_', ' ').title()}: ${sensitivity:,.0f} range")
            
            # Show winner changes
            winners = [r['winner'] for r in analysis['results']]
            if len(set(winners)) > 1:
                print(f"    Winner changes across range: {set(winners)}")
        
        print()
        
        # Find breakeven points
        breakeven_points = self.find_breakeven_points()
        if breakeven_points:
            print("Breakeven Points:")
            for param, value in breakeven_points.items():
                if isinstance(value, float):
                    if param.endswith('_rate'):
                        print(f"  {param.replace('_', ' ').title()}: {value:.1%}")
                    else:
                        print(f"  {param.replace('_', ' ').title()}: ${value:,.0f}")
                else:
                    print(f"  {param.replace('_', ' ').title()}: {value}")

    def print_detailed_results(self, sensitivity_results: Dict):
        """Print detailed results for most impactful parameters"""
        print("\n=== DETAILED SENSITIVITY RESULTS ===")
        
        # Investment return rate analysis
        if 'assumptions_investment_return_rate' in sensitivity_results:
            investment_analysis = sensitivity_results['assumptions_investment_return_rate']
            print(f"\nInvestment Return Rate Impact:")
            print(f"Base rate: {investment_analysis['base_value']:.1%}")
            for result in investment_analysis['results']:
                rate = result['parameter_value']
                diff = result['net_worth_difference']
                winner = result['winner']
                print(f"  {rate:.1%}: ${diff:,.0f} difference ({winner} wins)")
        
        # Home appreciation rate analysis
        if 'buy_home_appreciation_rate' in sensitivity_results:
            appreciation_analysis = sensitivity_results['buy_home_appreciation_rate']
            print(f"\nHome Appreciation Rate Impact:")
            print(f"Base rate: {appreciation_analysis['base_value']:.1%}")
            for result in appreciation_analysis['results']:
                rate = result['parameter_value']
                diff = result['net_worth_difference']
                winner = result['winner']
                print(f"  {rate:.1%}: ${diff:,.0f} difference ({winner} wins)")
        
        # Time horizon analysis
        if 'assumptions_time_horizon_years' in sensitivity_results:
            time_analysis = sensitivity_results['assumptions_time_horizon_years']
            print(f"\nTime Horizon Impact:")
            print(f"Base years: {time_analysis['base_value']}")
            for result in time_analysis['results']:
                years = result['parameter_value']
                diff = result['net_worth_difference']
                winner = result['winner']
                print(f"  {years} years: ${diff:,.0f} difference ({winner} wins)") 