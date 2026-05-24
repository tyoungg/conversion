import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sys
import os

# Add the project root to sys.path so we can import from docs
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from docs.conversion import simulate_retirement

# Page Configuration
st.set_page_config(
    page_title="Retirement Tax Conversion Strategy Simulator",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for styling
st.markdown("""
<style>
    .main {
        background-color: #f8f9fa;
    }
    .stMetric {
        background-color: white;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
</style>
""", unsafe_allow_html=True)

# Disclaimer Modal logic
if 'disclaimer_accepted' not in st.session_state:
    st.session_state.disclaimer_accepted = False

if not st.session_state.disclaimer_accepted:
    st.title("💰 Retirement Tax Conversion Strategy Simulator")
    st.error("### Important Disclaimer")
    st.write("""
    This tool is provided for educational and informational purposes only. It does not constitute financial, investment, tax, or legal advice.

    The projections and outputs are based on assumptions and simplified models of complex rules (including tax law, Social Security, Medicare, and Required Minimum Distributions). Actual results may differ significantly.

    This tool does not account for your full financial situation and should not be relied upon to make financial decisions.

    By continuing, you acknowledge that you are solely responsible for your decisions and that the creator of this tool is not liable for any outcomes resulting from its use.

    Please consult a qualified financial, tax, or legal professional before making decisions.
    """)
    if st.button("I Understand"):
        st.session_state.disclaimer_accepted = True
        st.rerun()
    st.stop()

# Header
st.title("💰 Retirement Tax Conversion Strategy Simulator")
st.markdown("Compare withdrawal strategies to minimize taxes and optimize retirement income")

# Quick Start Guide
with st.expander("📖 Quick Start Guide"):
    st.write("""
    - **Withdrawal Rate:** Sets your **Gross Withdrawal Target** as a percentage of your initial total portfolio. This is the total amount pulled from your accounts before taxes.
    - **Enable Roth Conversions:** If checked, the tool fills the 22% (A) or 24% (B) brackets with conversions when income is below the limit. *Note: If this is ON, your taxes may remain high even with QCDs because the "saved" tax room is immediately filled with Roth conversions.*
    - **QCD Percentage:** For ages 70.5+, specifies the % of your Traditional IRA to donate to charity. **QCDs are taken first from your Withdrawal Target**, reducing the taxable portion of your withdrawal and lowering your taxes.
    - **Spouse Death Age:** Simulates the "Widow's Penalty" by switching to Single filing status and adjusted Social Security in that year.
    - **MAGI:** Modified Adjusted Gross Income. Used for Medicare premium (IRMAA) calculations. *Formula: (Taxable Trad W/D) + (Pension) + (Taxable SS).*
    - **Taxable Income:** This is your **Net Taxable Income** after subtracting the Standard Deduction and applying tiered Social Security taxation. *Formula: (MAGI) - (Deduction).*
    """)

# Helper functions
def format_usd(val):
    return f"${val:,.0f}"

def summarize_results(results):
    total_taxes = sum(r["Taxes"] for r in results)
    total_medicare = sum(r["Medicare Cost"] for r in results)
    total_conversions = sum(r["Roth Conversion"] for r in results)
    total_qcds = sum(r["QCD Amount"] for r in results)
    total_expenses = total_taxes + total_medicare
    ending_balance = results[-1]["Roth Balance"] + results[-1]["Traditional Balance"]
    return {
        "taxes": total_taxes,
        "medicare": total_medicare,
        "conversions": total_conversions,
        "expenses": total_expenses,
        "balance": ending_balance,
        "qcds": total_qcds
    }

# Sidebar - Input Parameters
with st.sidebar:
    st.header("📋 Plan Your Retirement")

    with st.expander("👤 Personal Data", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            start_age = st.number_input("Starting Age", value=65, min_value=50, max_value=100)
            end_age = st.number_input("Ending Age", value=91, min_value=65, max_value=120)
        with col2:
            filing_status = st.selectbox("Filing Status", ["married", "single"], index=0)
            if filing_status == "married":
                spouse_death_age = st.number_input("Spouse Death Age", value=79, min_value=50, max_value=120)
            else:
                spouse_death_age = 999 # Irrelevant for single

    with st.expander("💰 Portfolio", expanded=True):
        initial_roth = st.number_input("Initial Roth Balance ($)", value=1_500_000, step=10000, format="%d")
        initial_trad = st.number_input("Initial Traditional Balance ($)", value=2_000_000, step=10000, format="%d")
        growth_rate = st.number_input("Annual Growth Rate (%)", value=5.5, step=0.5) / 100
        withdrawal_rate = st.number_input("Annual Withdrawal Rate (%)", value=5.0, step=0.5) / 100

    with st.expander("🛡️ Social Security & Income", expanded=True):
        st.subheader("Person 1 (Primary)")
        ss_primary_fra = st.number_input("Monthly SS at FRA ($)", value=3000, step=100, key="ss1")
        birth_year_primary = st.number_input("Birth Year", value=1960, min_value=1930, max_value=2025, key="by1")
        claim_age_primary = st.number_input("Claiming Age", value=67, min_value=62, max_value=70, key="ca1")

        if filing_status == "married":
            st.divider()
            st.subheader("Person 2 (Spouse)")
            ss_spouse_fra = st.number_input("Monthly SS at FRA ($)", value=1500, step=100, key="ss2")
            birth_year_spouse = st.number_input("Birth Year", value=1962, min_value=1930, max_value=2025, key="by2")
            claim_age_spouse = st.number_input("Claiming Age", value=67, min_value=62, max_value=70, key="ca2")
        else:
            ss_spouse_fra = 0
            birth_year_spouse = 1960
            claim_age_spouse = 67

        st.divider()
        pension_income = st.number_input("Annual Pension Income ($)", value=30000, step=1000)

    with st.expander("⚙️ Strategy Settings", expanded=True):
        fixed_roth_withdrawal = st.number_input("Fixed Annual Roth Withdrawal ($)", value=0, step=1000)
        qcd_percentage = st.number_input("QCD Percentage (%)", value=0.0, step=0.1) / 100
        use_roth_buffer = st.checkbox("Use Roth as spending buffer", value=True)
        enable_roth_conversion = st.checkbox("Enable Roth Conversions", value=True)

    run_sim = st.button("Calculate Scenarios", type="primary", use_container_width=True)

# Simulation Execution
if run_sim or 'results_a' in st.session_state:
    params = {
        "start_age": start_age,
        "end_age": end_age,
        "spouse_death_age": spouse_death_age,
        "initial_roth_balance": initial_roth,
        "initial_trad_balance": initial_trad,
        "growth_rate": growth_rate,
        "pension_income": pension_income,
        "withdrawal_rate": withdrawal_rate,
        "fixed_roth_withdrawal": fixed_roth_withdrawal,
        "use_roth_buffer": use_roth_buffer,
        "qcd_percentage": qcd_percentage,
        "enable_roth_conversion": enable_roth_conversion,
        "filing_status": filing_status,
        "ss_primary_fra": ss_primary_fra,
        "birth_year_primary": birth_year_primary,
        "claim_age_primary": claim_age_primary,
        "ss_spouse_fra": ss_spouse_fra,
        "birth_year_spouse": birth_year_spouse,
        "claim_age_spouse": claim_age_spouse
    }

    if run_sim:
        st.session_state.results_a = simulate_retirement(**params, strategy="A")
        st.session_state.results_b = simulate_retirement(**params, strategy="B")

    results_a = st.session_state.results_a
    results_b = st.session_state.results_b

    summary_a = summarize_results(results_a)
    summary_b = summarize_results(results_b)

    # Main Tabs
    tab1, tab2, tab3 = st.tabs(["📊 Summary", "📈 Charts", "📄 Year-by-Year"])

    with tab1:
        st.subheader("⚖️ Scenario Comparison")

        col_a, col_b, col_diff = st.columns(3)

        with col_a:
            st.info("### Scenario A\nStop at 22% Bracket")
            st.metric("Total Taxes", format_usd(summary_a["taxes"]))
            st.metric("Total Medicare", format_usd(summary_a["medicare"]))
            st.metric("Total Conversions", format_usd(summary_a["conversions"]))
            st.metric("Total QCDs", format_usd(summary_a["qcds"]))
            st.metric("Ending Balance", format_usd(summary_a["balance"]))

        with col_b:
            st.success("### Scenario B\nStop at 24% Bracket")
            st.metric("Total Taxes", format_usd(summary_b["taxes"]))
            st.metric("Total Medicare", format_usd(summary_b["medicare"]))
            st.metric("Total Conversions", format_usd(summary_b["conversions"]))
            st.metric("Total QCDs", format_usd(summary_b["qcds"]))
            st.metric("Ending Balance", format_usd(summary_b["balance"]))

        with col_diff:
            st.warning("### Difference\n(A - B)")

            def metric_diff(label, val_a, val_b, inverse=False):
                diff = val_a - val_b
                # For expenses, lower is better. For balance/QCD, higher is better.
                is_good = (diff < 0) if not inverse else (diff > 0)
                if abs(diff) < 0.01:
                    st.metric(label, "$0")
                else:
                    color = "normal" if is_good else "inverse" # Streamlit metric delta colors are limited
                    st.metric(label, format_usd(diff), delta=f"{'Better' if is_good else 'Worse'}", delta_color=color)

            metric_diff("Tax Difference", summary_a["taxes"], summary_b["taxes"])
            metric_diff("Medicare Difference", summary_a["medicare"], summary_b["medicare"])
            metric_diff("Total Expense Difference", summary_a["expenses"], summary_b["expenses"])
            metric_diff("QCD Difference", summary_a["qcds"], summary_b["qcds"], inverse=True)
            metric_diff("Balance Difference", summary_a["balance"], summary_b["balance"], inverse=True)

    with tab2:
        st.subheader("📈 Portfolio Growth & Conversions")

        ages = [r["Age"] for r in results_a]
        balance_a = [r["Roth Balance"] + r["Traditional Balance"] for r in results_a]
        balance_b = [r["Roth Balance"] + r["Traditional Balance"] for r in results_b]
        conv_a = [r["Roth Conversion"] for r in results_a]
        conv_b = [r["Roth Conversion"] for r in results_b]

        fig = go.Figure()

        # Balance lines
        fig.add_trace(go.Scatter(x=ages, y=balance_a, name="Scenario A: Total Balance", line=dict(color='#4299e1', width=3)))
        fig.add_trace(go.Scatter(x=ages, y=balance_b, name="Scenario B: Total Balance", line=dict(color='#ed8936', width=3, dash='dash')))

        # Conversion bars
        fig.add_trace(go.Bar(x=ages, y=conv_a, name="Scenario A: Roth Conversion", marker_color='#48bb78', opacity=0.5, yaxis='y2'))
        fig.add_trace(go.Bar(x=ages, y=conv_b, name="Scenario B: Roth Conversion", marker_color='#38b2ac', opacity=0.5, yaxis='y2'))

        fig.update_layout(
            template="plotly_white",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            yaxis=dict(title="Total Balance ($)", side="left"),
            yaxis2=dict(title="Annual Conversion ($)", side="right", overlaying='y', showgrid=False),
            hovermode="x unified"
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab3:
        sel_scenario = st.radio("Select Scenario to view details:", ["Scenario A", "Scenario B"], horizontal=True)
        detailed_data = results_a if sel_scenario == "Scenario A" else results_b
        df = pd.DataFrame(detailed_data)

        # Formatting for the dataframe
        currency_cols = [
            "Social Security", "Pension", "Taxable Trad W/D", "Roth Withdrawal",
            "Roth Conversion", "Traditional Balance", "Roth Balance", "RMD Required",
            "QCD Amount", "RMD Penalty", "MAGI", "Taxable Income", "Taxes",
            "Medicare Cost", "Net Income", "Total Outflow"
        ]

        formatted_df = df.copy()
        for col in currency_cols:
            formatted_df[col] = formatted_df[col].apply(lambda x: f"${x:,.2f}")

        st.dataframe(formatted_df, use_container_width=True)

else:
    st.info("👈 Fill in your retirement details in the sidebar and click 'Calculate Scenarios' to see results")

# Footer
st.divider()
st.markdown("""
<div style='text-align: center; color: #666; font-size: 0.85em;'>
    This tool is for educational purposes only and does not provide financial, tax, or legal advice.
    Results are estimates based on assumptions and may not reflect actual outcomes. Use at your own risk.<br>
    If this tool has been useful to you and you’d like to say thanks, you can support it here:
    <a href="https://paypal.me/tsy19" target="_blank" style="color: #667eea; text-decoration: none; font-weight: 600;">https://paypal.me/tsy19</a>
</div>
""", unsafe_allow_html=True)
