from typing import Dict, List, Tuple
from enum import Enum

class FilingStatus(Enum):
    SINGLE = "single"
    MARRIED_FILING_JOINTLY = "married_filing_jointly"

def get_inflation_factor(month: int, inflation_rate: float) -> float:
    """Calculate inflation factor for a given month"""
    years_elapsed = month // 12
    return (1 + inflation_rate) ** years_elapsed

def calc_income_tax_rate(income: float) -> float:
    """
    Get effective income tax rate approximation (federal + FICA).
    
    Args:
        income: Annual gross income
        
    Returns:
        Effective tax rate as decimal (e.g., 0.28 for 28%)
    """
    if income <= 100_000:
        return 0.22  # ~22% effective rate for lower-middle income
    elif income <= 300_000:
        return 0.28  # ~28% effective rate for upper-middle income  
    else:
        return 0.32  # ~32% effective rate for high income

def calc_long_term_cap_gains_tax_rate(gains: float, filing_status: FilingStatus) -> float:
    """
    Get long-term capital gains tax rate based on gains amount and filing status.
    
    Args:
        gains: Capital gains amount
        filing_status: Tax filing status
        
    Returns:
        Capital gains tax rate as decimal (e.g., 0.15 for 15%)
    """
    if filing_status == FilingStatus.SINGLE:
        if gains <= 50_000:
            return 0.0   # 0% bracket
        elif gains <= 500_000:
            return 0.15  # 15% bracket
        else:
            return 0.20  # 20% bracket
    else:  # MARRIED_FILING_JOINTLY
        if gains <= 100_000:
            return 0.0   # 0% bracket
        elif gains <= 600_000:
            return 0.15  # 15% bracket
        else:
            return 0.20  # 20% bracket

def calc_after_tax_income(gross_annual_income: float) -> float:
    """Calculate after-tax income using effective tax rate approximation."""
    effective_rate = calc_income_tax_rate(gross_annual_income)
    return gross_annual_income * (1 - effective_rate)

def calc_monthly_after_tax_income(month: int, base_income: float, income_growth_rate: float) -> float:
    """Calculate monthly after-tax income for a given month, accounting for income growth."""
    monthly_gross_income = calc_monthly_gross_income(month, base_income, income_growth_rate)
    annual_gross_income = monthly_gross_income * 12
    annual_after_tax_income = calc_after_tax_income(annual_gross_income)
    return annual_after_tax_income / 12

def calc_monthly_gross_income(month: int, base_income: float, income_growth_rate: float) -> float:
    """Calculate monthly gross income for a given month, accounting for income growth."""
    years_elapsed = month // 12
    annual_gross_income = base_income * (1 + income_growth_rate) ** years_elapsed
    return annual_gross_income / 12

def calc_monthly_investment_return_rate(annual_return_rate: float) -> float:
    """Calculate monthly investment return rate that compounds to the annual rate."""
    return (1 + annual_return_rate) ** (1/12) - 1

def calc_portfolio_gain(month: int, portfolio_values: List[float], annual_return_rate: float) -> float:
    """Calculate portfolio gain for a given month.
    
    Args:
        month: Current month (0-indexed)
        portfolio_values: List of portfolio values up to current month
        annual_return_rate: Annual investment return rate
        
    Returns:
        Portfolio gain for the month (investment return only)
    """
    if month == 0:
        return 0
    else:
        monthly_return = calc_monthly_investment_return_rate(annual_return_rate)
        return portfolio_values[month - 1] * monthly_return

def calc_capital_gains_tax(final_value: float, initial_value: float, investment_tax_enabled: bool, filing_status: FilingStatus) -> float:
    """Calculate capital gains tax using effective rate approximation."""
    if not investment_tax_enabled:
        return 0
        
    gains = final_value - initial_value
    if gains <= 0:
        return 0
        
    effective_rate = calc_long_term_cap_gains_tax_rate(gains, filing_status)
    return gains * effective_rate

def calc_home_capital_gains_tax(final_home_value: float, initial_home_value: float, 
                               primary_home_exclusion: float, investment_tax_enabled: bool, 
                               filing_status: FilingStatus) -> float:
    """Calculate capital gains tax on home sale with primary residence exclusion."""
    if not investment_tax_enabled:
        return 0
        
    gains = final_home_value - initial_home_value
    taxable_gains = max(0, gains - primary_home_exclusion)
    
    effective_rate = calc_long_term_cap_gains_tax_rate(taxable_gains, filing_status)
    return taxable_gains * effective_rate 