# Methodology for Rent vs Buy Calculator

## Methodology

This calculator performs a month-by-month simulation comparing the financial outcomes of buying versus renting over a specified time period. The analysis tracks net worth accumulation for both scenarios to determine which strategy yields better long-term financial results.

### Core Simulation Approach

**Monthly Cash Flow Analysis**: Each month, the calculator:
1. Calculates after-tax income (accounting for income growth over time)
2. Determines housing costs (mortgage payments vs rent, adjusted for inflation/appreciation)
3. Subtracts non-housing expenses (food, utilities, etc., adjusted for inflation)
4. Invests all excess cash flow into the stock market

monthly results are written to csv files for each scenario to be used for sanity checking.

**Investment Strategy**: Both the renter and homeowner invest their excess monthly cash flow into a diversified investment portfolio (assumed to be stock market with expected annual returns of ~9%).

### Key Advantages: Renter Scenario

**Larger Initial Investment Portfolio**: Renters start with their full net worth invested in the market, while homeowners must use a portion for the down payment. This gives renters an immediate advantage in investment capital.

**Higher Monthly Cash Flow**: Rent payments are typically lower than total homeownership costs (mortgage + property tax + maintenance + insurance + HOA), providing renters with more excess cash flow to invest each month.

**Superior Investment Returns**: The stock market historically outperforms real estate appreciation significantly (9% vs 4% in this model). With compound growth over time, this difference becomes substantial.

### Key Advantages: Homeowner Scenario

**Leveraged Real Estate Investment**: With a 20% down payment, homeowners make a 5:1 leveraged bet on home prices. For every dollar the home appreciates, they gain $5 in equity value. This leverage amplifies returns on the real estate portion of their portfolio.

**Forced Savings Through Equity Building**: Monthly mortgage payments include principal reduction, which builds equity over time. Unlike rent payments that provide no future value, mortgage payments create wealth accumulation.

**Tax Advantages**: Homeowners benefit from significant tax advantages:
- Up to $500,000 in capital gains from primary residence sale can be excluded from taxes (married filing jointly)
- This exclusion can result in substantial tax savings compared to taxable investment gains

### Market Efficiency Considerations

In an efficient market, these competing advantages typically balance out, preventing clear arbitrage opportunities. However, market inefficiencies can create periods where one strategy significantly outperforms the other due to:

- **Interest Rate Environment**: Low mortgage rates favor buying; high rates favor renting
- **Local Market Conditions**: Rent-to-price ratios vary significantly by geography and time
- **Tax Policy Changes**: Modifications to mortgage interest deductions or capital gains treatment
- **Market Timing**: Real estate and stock market cycles don't always align

The calculator helps quantify these trade-offs under specific assumptions, allowing users to model their particular situation and market conditions.

## Data Classes and Enums

### FilingStatus (Enum)
- `SINGLE`: Represents single tax filing status
- `MARRIED_FILING_JOINTLY`: Represents married filing jointly tax status

### BuyScenario (Dataclass)
Contains all parameters related to the home buying scenario:
- `purchase_price`: Home purchase price in dollars
- `down_payment_pct`: Down payment as percentage of purchase price
- `mortgage_rate`: Annual mortgage interest rate
- `amortization_years`: Loan term in years
- `property_tax_rate`: Annual property tax rate as percentage of home value
- `maintenance_cost_pct`: Annual maintenance cost as percentage of purchase price
- `home_insurance_monthly`: Monthly home insurance cost
- `hoa_monthly`: Monthly HOA fees
- `home_appreciation_rate`: Annual home value appreciation rate
- `selling_cost_pct`: Total cost to sell home as percentage of home value
- `primary_home_exclusion_dollars`: Capital gains exclusion amount for primary residence

### RentScenario (Dataclass)
Contains all parameters related to the renting scenario:
- `monthly_rent`: Monthly rent payment
- `renters_insurance_monthly`: Monthly renters insurance cost
- `rent_increase_rate`: Annual rate of rent increases

### Assumptions (Dataclass)
Contains general assumptions used in both scenarios:
- `income`: Annual household income
- `time_horizon_years`: Analysis period in years
- `investment_tax_enabled`: Boolean flag for whether investments are subject to capital gains tax
- `filing_status`: Tax filing status (single or married filing jointly)
- `inflation_rate`: Annual inflation rate
- `investment_return_rate`: Expected annual return on investment portfolio
- `income_growth_rate`: Annual household income growth rate
- `starting_net_worth`: Initial net worth
- `annual_non_housing_spending`: Annual spending on non-housing expenses

## RentVsBuyCalculator Class

### `__init__(self, buy_scenario, rent_scenario, assumptions)`
- Stores the three input objects as instance variables
- Calculates the required down payment amount
- Raises a ValueError if starting net worth is less than the required down payment
- Does not perform any other validation

### `get_inflation_factor(self, month)`
- Takes a month number (0-based) as input
- Calculates how many complete years have elapsed by dividing month by 12
- Returns `(1 + inflation_rate) ^ years_elapsed`
- Used to adjust costs for inflation over time

### `calc_income_tax_rate(self, income)`
- Takes annual gross income as input
- Returns hardcoded effective tax rates based on income brackets:
  - Income ≤ $100,000: returns 0.22 (22%)
  - Income ≤ $300,000: returns 0.28 (28%)
  - Income > $300,000: returns 0.32 (32%)
- These rates include federal income tax and FICA taxes

### `calc_long_term_cap_gains_tax_rate(self, gains)`
- Takes capital gains amount as input
- Returns tax rates based on filing status and gains amount:
  - **Single filers:**
    - Gains ≤ $50,000: 0% tax rate
    - Gains ≤ $500,000: 15% tax rate
    - Gains > $500,000: 20% tax rate
  - **Married filing jointly:**
    - Gains ≤ $100,000: 0% tax rate
    - Gains ≤ $600,000: 15% tax rate
    - Gains > $600,000: 20% tax rate

### `calc_after_tax_income(self, gross_annual_income)`
- Takes gross annual income as input
- Calls `calc_income_tax_rate()` to get the effective tax rate
- Returns `gross_income * (1 - tax_rate)`

### `calc_capital_gains_tax(self, final_value, initial_value)`
- Returns 0 if `investment_tax_enabled` is False
- Calculates gains as `final_value - initial_value`
- Returns 0 if gains are ≤ 0
- Calls `calc_long_term_cap_gains_tax_rate()` to get the tax rate
- Returns `gains * tax_rate`

### `calc_home_capital_gains_tax(self, final_home_value, initial_home_value)`
- Returns 0 if `investment_tax_enabled` is False
- Calculates gains as `final_home_value - initial_home_value`
- Subtracts the primary home exclusion amount from gains
- Uses `max(0, gains - exclusion)` to ensure taxable gains aren't negative
- Calls `calc_long_term_cap_gains_tax_rate()` to get the tax rate
- Returns `taxable_gains * tax_rate`

### `calculate_mortgage_payment()`
- Calculates the loan principal as `purchase_price * (1 - down_payment_pct)`
- Converts annual rate to monthly rate by dividing by 12
- Calculates total number of payments as `amortization_years * 12`
- If monthly rate is 0, returns `principal / num_payments`
- Otherwise uses the standard mortgage payment formula to return monthly P&I payment

### `generate_amortization_schedule()`
- Calculates initial loan principal and monthly payment
- Creates an empty list to store remaining balances
- Iterates through each month of the time horizon
- For each month:
  - Calculates interest payment as `remaining_balance * monthly_rate`
  - Calculates principal payment as `monthly_payment - interest_payment`
  - Reduces remaining balance by principal payment
  - Appends `max(0, remaining_balance)` to the list
  - Breaks the loop if remaining balance reaches 0
- Returns the list of monthly remaining balances

### `calculate_monthly_ownership_costs(self, month)`
- Gets the fixed monthly mortgage payment
- Calculates current home value using annual appreciation: `purchase_price * (1 + appreciation_rate) ^ years_elapsed`
- Calculates monthly property tax as `(current_home_value * property_tax_rate) / 12`
- Calculates monthly maintenance as `(purchase_price * maintenance_cost_pct) / 12`
- Applies inflation factor to property tax, maintenance, insurance, and HOA fees
- Returns the sum of: mortgage payment + property tax + maintenance + insurance + HOA fees

### `calculate_monthly_rent_costs(self, month)`
- Calculates current rent using annual increases: `monthly_rent * (1 + rent_increase_rate) ^ years_elapsed`
- Applies inflation factor to renters insurance
- Returns the sum of current rent and current insurance

### `calc_portfolio_per_month(self, initial_portfolio, monthly_costs_func)`
- Takes an initial portfolio value and a function that calculates monthly costs
- Creates a list starting with the initial portfolio value
- Converts annual investment return to monthly return by dividing by 12
- For each month in the time horizon:
  - Calculates current annual income with growth: `income * (1 + income_growth_rate) ^ years_elapsed`
  - Converts to after-tax monthly income
  - Calls the provided monthly costs function to get housing costs
  - Applies inflation to non-housing spending
  - Calculates excess cash flow as: `monthly_income - housing_costs - non_housing_spending`
  - Grows previous portfolio value by monthly return and adds excess cash flow
  - Appends new portfolio value to the list
- Returns the complete list of monthly portfolio values

### `calc_homeowner_net_worth()`
- Generates the mortgage amortization schedule
- Calculates down payment and initial portfolio value
- Gets portfolio values over time using `calc_portfolio_per_month()`
- Creates an empty results list
- For each month:
  - Calculates current income (gross and after-tax)
  - Calculates current home value with appreciation
  - Breaks down monthly costs (mortgage, property tax, maintenance, insurance, HOA)
  - Applies inflation to relevant costs
  - Calculates portfolio gain as previous month's portfolio value times monthly return
  - Determines remaining mortgage balance from amortization schedule
  - Calculates home equity as `current_home_value - remaining_balance`
  - Stores current home valuation for tracking purposes
  - For the final month only:
    - Applies selling costs and home capital gains tax
    - Applies portfolio capital gains tax
    - Adjusts home equity and portfolio value accordingly
  - Calculates total net worth as `portfolio_value + home_equity`
  - Appends detailed monthly data to results list including: month, year, portfolio_value, home_equity, home_valuation, total_net_worth, portfolio_gain, income data, and all cost breakdowns
- Returns tuple of (monthly_data_list, portfolio_capital_gains_tax, home_capital_gains_tax)

### `calc_renter_net_worth()`
- Sets initial portfolio to full starting net worth (no down payment needed)
- Gets portfolio values over time using `calc_portfolio_per_month()`
- Creates an empty results list
- For each month:
  - Calculates current income (gross and after-tax)
  - Calculates current rent with annual increases
  - Applies inflation to renters insurance and non-housing spending
  - Calculates portfolio gain as previous month's portfolio value times monthly return
  - For the final month only:
    - Calculates and applies capital gains tax to portfolio
    - Adjusts portfolio value accordingly
  - Sets total net worth equal to portfolio value (no home equity)
  - Appends detailed monthly data to results list including: month, year, portfolio_value, total_net_worth, portfolio_gain, income data, and cost breakdowns
- Returns tuple of (monthly_data_list, final_capital_gains_tax)

### `run_analysis()`
- Calls `calc_homeowner_net_worth()` and `calc_renter_net_worth()` to get detailed monthly data
- Creates a monthly comparison list by iterating through all months
- For each month:
  - Extracts homeowner total net worth (portfolio + home equity)
  - Extracts renter total net worth (portfolio only)
  - Calculates net worth difference
  - Determines winner based on higher net worth
  - Stores comparison data in a dictionary
- Creates a summary dictionary with final month results and tax information
- Includes final home valuation in the homeowner breakdown summary
- Returns a dictionary containing both monthly comparisons and summary statistics

### `print_results(self, results)`
- Prints formatted scenario parameters (buy scenario, rent scenario, assumptions)
- Prints summary results including final winner and net worth breakdown
- Displays final home valuation alongside portfolio value and home equity in homeowner breakdown
- Calls `calc_homeowner_net_worth()` and `calc_renter_net_worth()` again to get detailed data
- Writes homeowner data to 'homeowner_monthly_analysis.csv' with columns: month, year, networth, gross_income, after_tax_income, portfolio_value, portfolio_gain, home_equity, home_valuation, cost_mortgage, monthly_property_tax, monthly_maintenance, home_insurance, hoa_fees, non_housing_cost
- Writes renter data to 'renter_monthly_analysis.csv' with columns: month, year, networth, gross_income, after_tax_income, portfolio_value, portfolio_gain, cost_rent, cost_insurance, non_housing_cost
- Rounds all numerical values to 2 decimal places in the CSV output
- Prints confirmation messages about CSV file creation

## Main Execution Block

When run as a script, the code:
- Creates a `BuyScenario` with Seattle-area parameters (700K home, 20% down, etc.)
- Creates a `RentScenario` with $2500/month rent
- Creates `Assumptions` with $350K income, 10-year horizon, and other parameters
- Instantiates a `RentVsBuyCalculator` with these scenarios
- Runs the analysis and prints results
- Generates CSV files with monthly breakdowns

## Output Files

The application generates two CSV files:
- `homeowner_monthly_analysis.csv`: Monthly breakdown for the buying scenario
- `renter_monthly_analysis.csv`: Monthly breakdown for the renting scenario

Both files contain month-by-month financial data including net worth, income, costs, and portfolio performance. 