import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import minimize

# Function to fetch stock data
def get_stock_data(ticker):
    stock = yf.Ticker(ticker)
    return stock

# Function to calculate WACC
def calculate_wacc(equity_value, debt_value, cost_of_equity, cost_of_debt, tax_rate):
    total_value = equity_value + debt_value
    wacc = (equity_value / total_value) * cost_of_equity + (debt_value / total_value) * cost_of_debt * (1 - tax_rate)
    return wacc

# Function to calculate DCF
def calculate_dcf(fcf, growth_rate, wacc, terminal_growth_rate, num_years):
    discounted_fcf = []
    for i in range(num_years):
        discounted_fcf.append(fcf / ((1 + wacc) ** (i + 1)))
        fcf = fcf * (1 + growth_rate)
    
    terminal_value = (fcf * (1 + terminal_growth_rate)) / (wacc - terminal_growth_rate)
    discounted_terminal_value = terminal_value / ((1 + wacc) ** num_years)
    
    total_value = sum(discounted_fcf) + discounted_terminal_value
    return total_value, discounted_fcf, terminal_value

# Function to calculate alternative valuation using Price to Sales ratio
def calculate_ps_valuation(sales, industry_ps_ratio):
    return sales * industry_ps_ratio

# Streamlit interface
st.title('Stock Fair Value Calculator')

ticker = st.text_input('Enter stock ticker', 'AAPL')

if ticker:
    stock = get_stock_data(ticker)
    info = stock.info
    
    st.header(f"{info.get('shortName', 'N/A')} ({ticker})")
    
    # Display key metrics
    st.subheader('Key Metrics')
    metrics = {
        'Previous Close': info.get('previousClose', 'N/A'),
        'Market Cap': info.get('marketCap', 'N/A'),
        'PE Ratio': info.get('trailingPE', 'N/A'),
        'Forward PE Ratio': info.get('forwardPE', 'N/A'),
        'PEG Ratio': info.get('pegRatio', 'N/A'),
        'Price to Sales Ratio': info.get('priceToSalesTrailing12Months', 'N/A'),
        'Price to Book Ratio': info.get('priceToBook', 'N/A'),
        'Dividend Yield': info.get('dividendYield', 'N/A'),
    }
    st.table(pd.DataFrame(metrics.items(), columns=['Metric', 'Value']))
    
    # Check if both PE ratio and FCF are negative
    pe_ratio = info.get('trailingPE', None)
    fcf = info.get('freeCashflow', None)
    negative_pe_and_fcf = (pe_ratio is not None and pe_ratio < 0) and (fcf is not None and fcf < 0)
    
    if negative_pe_and_fcf:
        st.subheader('Alternative Valuation Using Price to Sales Ratio')
        sales = info.get('totalRevenue', 0)
        industry_ps_ratio = st.number_input('Enter the industry Price to Sales (P/S) ratio', value=1.5)
        ps_valuation = calculate_ps_valuation(sales, industry_ps_ratio)
        fair_value_per_share = ps_valuation / info.get('sharesOutstanding', 1)
        st.write(f'**Fair Value of the Company (P/S Method):** ${ps_valuation / 1e9:,.2f} Billion')
        st.write(f'**Fair Value per Share (P/S Method):** ${fair_value_per_share:.2f}')

        st.header('Explanation of the Price to Sales (P/S) Ratio Valuation')
        st.markdown("""
        **Price to Sales (P/S) Ratio Valuation:**
        - **Purpose:** The P/S ratio valuation method is used when traditional metrics like PE ratio and FCF are not applicable, often in cases where a company is not yet profitable or has negative cash flows.
        - **How It Works:**
            1. **Total Revenue:** Start with the company's total revenue.
            2. **Industry P/S Ratio:** Use the average P/S ratio for the industry in which the company operates.
            3. **Valuation:** Multiply the company's total revenue by the industry P/S ratio to estimate the company's fair value.
        - **Formula:** 
            \[
            \text{Fair Value} = \text{Total Revenue} \times \text{Industry P/S Ratio}
            \]
        - **Example:** If a company has $10 billion in total revenue and the average industry P/S ratio is 1.5, the estimated fair value of the company would be $15 billion.
        """)

    else:
        # Fetch historical data for growth rates
        hist = stock.history(period="5y")
        revenue_growth = (hist['Close'].pct_change().mean()) * 100
        profit_margin = info.get('profitMargins', np.nan) * 100
        fcf_margin = (info.get('freeCashflow', np.nan) / info.get('totalRevenue', np.nan)) * 100 if info.get('freeCashflow') and info.get('totalRevenue') else np.nan
        
        # Historic metrics table
        st.subheader('Historical Metrics')
        hist_metrics = {
            'Revenue Growth (5y Avg)': revenue_growth,
            'Profit Margin': profit_margin,
            'Free Cash Flow Margin': fcf_margin,
        }
        st.table(pd.DataFrame(hist_metrics.items(), columns=['Metric', 'Value (%)']))
        
        # Analyst expectations
        st.subheader('Analyst Expectations')
        st.write(f"1y Target Est: ${info.get('targetMeanPrice', 'N/A'):.2f}")
        st.write(f"Recommendation: {info.get('recommendationKey', 'N/A').capitalize()}")
        
        # Stock chart
        st.subheader('Stock Price Chart')
        st.line_chart(hist['Close'])

        # User input for DCF assumptions
        st.subheader('DCF Assumptions')
        initial_fcf = st.number_input('Initial annual free cash flow (Billions $)', value=info.get('freeCashflow', 0) / 1000000000)
        growth_rate = st.number_input('Annual growth rate (%)', value=5.0) / 100
        terminal_growth_rate = st.number_input('Terminal growth rate (%)', value=2.0) / 100
        num_years = st.number_input('Number of years', value=5)
        tax_rate = st.number_input('Corporate tax rate (%)', value=21.0) / 100
        equity_value = st.number_input('Market value of equity (Billions $)', value=info.get('marketCap', 0) / 1000000000)
        debt_value = st.number_input('Market value of debt (Billions $)', value=info.get('totalDebt', 0) / 1000000000)
        cost_of_equity = st.number_input('Cost of equity (%)', value=8.0) / 100
        cost_of_debt = st.number_input('Cost of debt (%)', value=5.0) / 100
        initial_fcf = initial_fcf * 1000000000
        debt_value = debt_value * 1000000000
        equity_value = equity_value * 1000000000

        # Calculate WACC
        wacc = calculate_wacc(equity_value, debt_value, cost_of_equity, cost_of_debt, tax_rate)
        st.write(f'Weighted Average Cost of Capital (WACC): {wacc:.2%}')

        # Calculate DCF
        total_value, discounted_fcf, terminal_value = calculate_dcf(initial_fcf, growth_rate, wacc, terminal_growth_rate, num_years)
        
        # Calculate quarterly FCF
        quarterly_fcf = [initial_fcf / 4 * (1 + growth_rate / 4) ** i for i in range(num_years * 4)]
        
        st.write(f'Fair Value of the Company: Billion ${total_value / 1000000000:,.2f}')
        fair_value_per_share = total_value / info.get('sharesOutstanding', 1)
        st.write(f'**Fair Value per Share:** ${fair_value_per_share:.2f}')
        myInt = 1000000000
        discounted_fcf1 = [x / myInt for x in discounted_fcf]
        discounted_fcf1 = [round(e, 2) for e in discounted_fcf1]
        terminal_value1 = terminal_value / 1000000000
        terminal_value1 = "{:.2f}".format(terminal_value1)
        quarterly_fcf1 = [x / myInt for x in quarterly_fcf]
        st.write('Discounted Free Cash Flows:', discounted_fcf1, " Billion $")
        st.write('Terminal Value:', terminal_value1, " Billion $")

        # Plot quarterly FCF
        fig, ax = plt.subplots()
        quarters = [f'Q{i + 1}' for i in range(len(quarterly_fcf))]
        ax.plot(quarters, quarterly_fcf, marker='o')
        ax.set_title('Quarterly Free Cash Flows')
        ax.set_xlabel('Quarter')
        ax.set_ylabel('Free Cash Flow ($)')
        st.pyplot(fig)
        # Explanation section
        st.header('Explanation of the DCF Calculation')
        st.markdown("""
        **1. Estimate Future Free Cash Flows (FCF):**
        - Start with the initial FCF.
        - Project FCF for each year using the growth rate.
        **2. Calculate Terminal Value:**
        - Terminal Value is the value of all future FCFs beyond the projection period.
        - Terminal Value = (FCF * (1 + Terminal Growth Rate)) / (WACC - Terminal Growth Rate)
        **3. Discount FCF and Terminal Value:**
        - Use WACC to discount FCF and Terminal Value to present value.
        - Total Value = Sum of discounted FCFs + Discounted Terminal Value
        """)

        st.header('Explanation of WACC Calculation')
        st.markdown("""
        **Weighted Average Cost of Capital (WACC) Calculation:**
        - WACC = E/V * Re + D/V * Rd * (1 - Tc)
        - **E**: Market value of equity
        - **V**: Total market value (equity + debt)
        - **Re**: Cost of equity
        - **D**: Market value of debt
        - **Rd**: Cost of debt
        - **Tc**: Corporate tax rate
        """)

        st.header('User Inputs Guide')
        st.markdown("""
        **How to Calculate the Inputs:**
        - **Market Value of Equity**: Current share price * Number of outstanding shares.
        - **Market Value of Debt**: Total debt listed on the balance sheet.
        - **Cost of Equity**: Estimate using CAPM (Capital Asset Pricing Model).
        - **Cost of Debt**: Average interest rate on company's debt.
        - **Corporate Tax Rate**: Effective tax rate from the company's financial statements.
        - **Initial FCF**: Last year's free cash flow from the cash flow statement.
        - **Growth Rate**: Expected annual growth rate in FCF.
        - **Terminal Growth Rate**: Expected long-term growth rate of FCF.
        - **Number of Years**: Number of years to project FCF.
        """)

# End of the Streamlit app
