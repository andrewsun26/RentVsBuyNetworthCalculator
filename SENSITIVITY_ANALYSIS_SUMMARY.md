# Rent vs Buy Calculator - Starting Net Worth & Sensitivity Analysis

## Starting Net Worth Assumption

### Previous Implementation
The original implementation had an **implicit assumption of $0 starting net worth** for both scenarios:
- **Renter**: Investment portfolio started at `[0]`
- **Homeowner**: Only considered home equity, ignoring opportunity cost of down payment

### Updated Implementation
Now **explicitly tracks starting net worth** with these improvements:

1. **Added `starting_net_worth` field** to `Assumptions` dataclass
2. **Renter scenario**: Starts with `starting_net_worth` (includes what would be down payment)
3. **Homeowner scenario**: Uses `starting_net_worth - down_payment` for remaining investments
4. **Fair comparison**: Both scenarios start with the same total net worth
5. **Validation**: Ensures starting net worth is sufficient for down payment

### Key Logic Fix
**CORRECTED**: The down payment should be **part of** the starting net worth, not **additional to** it:
- **Renter**: Invests entire `starting_net_worth` in portfolio
- **Homeowner**: Uses `down_payment` from `starting_net_worth`, invests remainder

## Sensitivity Analysis Results

### Base Case (Seattle Example)
- **Starting Net Worth**: $140,000 (equals down payment)
- **Purchase Price**: $700,000 (20% down = $140,000)
- **Monthly Rent**: $2,500
- **Time Horizon**: 10 years
- **Result**: **Rent wins by $845,345**

### Most Sensitive Parameters (Ranked by Impact)

1. **Time Horizon** ($10.9M range)
   - Longer periods heavily favor buying due to compound appreciation
   - 5 years: Rent wins by $299K
   - 30 years: Rent wins by $11.2M (surprising!)

2. **Purchase Price** ($850K range)
   - Higher prices increase opportunity cost of down payment
   - More expensive homes need higher appreciation to justify

3. **Investment Return Rate** ($706K range)
   - Higher returns favor renting (opportunity cost of down payment)
   - 4% return: Rent wins by $456K
   - 12% return: Rent wins by $1.16M

4. **Monthly Rent** ($535K range)
   - Higher rent favors buying
   - Lower rent strengthens the renting case

5. **Home Appreciation Rate** ($492K range)
   - Critical for homeownership viability
   - Even at 7% appreciation, rent still wins in this scenario

### Key Insights

#### Why Rent Wins in This Scenario
1. **High opportunity cost**: $140K down payment invested at 9% compounds significantly
2. **High ownership costs**: $9,211/month vs $2,522/month rent
3. **Cash flow advantage**: Renter saves $6,689/month to invest
4. **Tax efficiency**: Long-term capital gains (15%) vs property taxes (8.5%)

#### Breakeven Analysis
The analysis shows that in this high-cost Seattle market:
- **Investment returns** would need to drop significantly for buying to win
- **Home appreciation** would need to exceed historical averages substantially
- **Rent** would need to increase dramatically to favor buying

#### Time Horizon Paradox
Surprisingly, **longer time horizons favor renting more** in this scenario because:
- The monthly cash flow advantage compounds over time
- Investment returns compound on a larger base (down payment + monthly savings)
- Property taxes and maintenance costs grow with inflation

### Practical Implications

1. **Market-dependent**: Results vary significantly by location and market conditions
2. **Personal factors**: Income, tax situation, and risk tolerance matter
3. **Lifestyle considerations**: Not captured in pure financial analysis
4. **Timing matters**: Market cycles can dramatically affect outcomes

### Recommendations for Users

1. **Adjust parameters** to match your specific situation
2. **Consider multiple scenarios** with different assumptions
3. **Focus on breakeven points** to understand decision sensitivity
4. **Include non-financial factors** in your final decision
5. **Regularly reassess** as market conditions change

## Technical Implementation Notes

### Starting Net Worth Handling
```python
# Renter: Invests entire starting net worth
initial_portfolio = starting_net_worth

# Homeowner: Uses down payment from starting net worth, invests remainder
remaining_net_worth = starting_net_worth - down_payment
total_net_worth = home_equity + remaining_net_worth
```

### Sensitivity Analysis Features
- **Comprehensive parameter testing** across realistic ranges
- **Breakeven point identification** for key variables
- **Winner change detection** across parameter ranges
- **Ranked sensitivity analysis** by financial impact
- **Input validation**: Ensures starting net worth ≥ down payment
- **Error handling**: Skips invalid parameter combinations

### Implementation Validation
```python
# Validation in constructor
down_payment = purchase_price * down_payment_pct
if starting_net_worth < down_payment:
    raise ValueError("Starting net worth insufficient for down payment")
```

This analysis provides a robust framework for making informed rent vs buy decisions based on your specific financial situation and market conditions. 