import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# -----------------------------
# RETIREMENT SIMULATION LOGIC
# -----------------------------

# SOCIAL SECURITY LOGIC
def get_fra(birth_year):
    """Returns Full Retirement Age (FRA) in years and months based on birth year."""
    if birth_year <= 1937:
        return 65, 0
    if birth_year == 1938:
        return 65, 2
    if birth_year == 1939:
        return 65, 4
    if birth_year == 1940:
        return 65, 6
    if birth_year == 1941:
        return 65, 8
    if birth_year == 1942:
        return 65, 10
    if 1943 <= birth_year <= 1954:
        return 66, 0
    if birth_year == 1955:
        return 66, 2
    if birth_year == 1956:
        return 66, 4
    if birth_year == 1957:
        return 66, 6
    if birth_year == 1958:
        return 66, 8
    if birth_year == 1959:
        return 66, 10
    return 67, 0

def calculate_adjusted_ss(monthly_fra_benefit, claim_age, birth_year):
    """Calculates the adjusted monthly Social Security benefit based on claiming age."""
    fra_years, fra_months = get_fra(birth_year)
    fra_total_months = fra_years * 12 + fra_months
    claim_total_months = int(claim_age * 12)

    diff_months = claim_total_months - fra_total_months

    if diff_months == 0:
        return monthly_fra_benefit

    if diff_months > 0:
        months_to_70 = min(diff_months, (70 * 12) - fra_total_months)
        return monthly_fra_benefit * (1 + (months_to_70 * (2/3 / 100)))
    else:
        months_early = abs(diff_months)
        reduction = 0
        if months_early <= 36:
            reduction = months_early * (5/9 / 100)
        else:
            reduction = (36 * (5/9 / 100)) + ((months_early - 36) * (5/12 / 100))
        return monthly_fra_benefit * (1 - reduction)

# TAX FUNCTIONS
def calculate_tax(taxable_income, brackets):
    tax = 0
    for lower, upper, rate in brackets:
        if taxable_income > lower:
            taxed_amount = min(taxable_income, upper) - lower
            tax += taxed_amount * rate
        else:
            break
    return tax

def calculate_taxable_ss(withdrawal_trad, other_income, ss_income, filing_status):
    if ss_income <= 0:
        return 0
    provisional = withdrawal_trad + other_income + 0.5 * ss_income
    if filing_status == "married":
        t1, t2 = 32000, 44000
        max_50_pct_tier = 6000
    else:
        t1, t2 = 25000, 34000
        max_50_pct_tier = 4500
    if provisional <= t1:
        return 0
    tier1_amt = min(provisional, t2) - t1
    taxable_50 = 0.5 * tier1_amt
    tier2_amt = max(0, provisional - t2)
    taxable_85 = 0.85 * tier2_amt
    combined_tiered = taxable_85 + min(taxable_50, 0.5 * ss_income, max_50_pct_tier)
    return min(combined_tiered, 0.85 * ss_income)

# MEDICARE + RMD
def calculate_medicare_premium(magi, filing_status, age_primary, age_spouse=None):
    if filing_status == "married":
        brackets = [218000, 274000, 342000, 410000, 750000]
    else:
        brackets = [109000, 137000, 171000, 205000, 500000]
    b_premiums = [202.90, 284.10, 405.80, 527.50, 649.20, 680.90]
    d_surcharges = [0.00, 14.50, 37.50, 60.40, 83.30, 91.00]
    d_base = 40.00
    idx = 5
    for i, limit in enumerate(brackets):
        is_last_bracket = (i == len(brackets) - 1)
        if (magi < limit if is_last_bracket else magi <= limit):
            idx = i
            break
    monthly_per_person = b_premiums[idx] + d_surcharges[idx] + d_base
    total_annual = 0
    if age_primary >= 65:
        total_annual += monthly_per_person * 12
    if filing_status == "married" and age_spouse is not None:
        if age_spouse >= 65:
            total_annual += monthly_per_person * 12
    return total_annual

def calculate_rmd(balance, age, rmd_start_age=73):
    if age < rmd_start_age or balance <= 0:
        return 0
    divisors = {
        73: 26.5, 74: 25.5, 75: 24.6, 76: 23.7, 77: 22.9,
        78: 22.0, 79: 21.1, 80: 20.2, 81: 19.4, 82: 18.5,
        83: 17.7, 84: 16.8, 85: 16.0, 86: 15.2, 87: 14.4,
        88: 13.7, 89: 12.9, 90: 12.2, 91: 11.5, 92: 10.8,
        93: 10.1, 94: 9.5, 95: 8.9, 96: 8.4, 97: 7.8,
        98: 7.3, 99: 6.8, 100: 6.4
    }
    divisor = divisors.get(age, divisors[max(divisors.keys())] if age > 100 else 10)
    return balance / divisor

# SIMULATION ENGINE
def simulate_retirement(
    start_age, end_age, spouse_death_age, initial_roth_balance, initial_trad_balance,
    growth_rate, pension_income, withdrawal_rate, strategy="B", include_rmd=True,
    include_medicare=True, fixed_roth_withdrawal=0, use_roth_buffer=True,
    enable_roth_conversion=True, qcd_percentage=0, filing_status="married",
    ss_primary_fra=3000, birth_year_primary=1960, claim_age_primary=67,
    ss_spouse_fra=1500, birth_year_spouse=1962, claim_age_spouse=67, **kwargs
):
    married_brackets = [
        (0, 23850, 0.10), (23850, 96950, 0.12), (96950, 206700, 0.22),
        (206700, 394600, 0.24), (394600, 501050, 0.32), (501050, 751600, 0.35),
        (751600, float('inf'), 0.37)
    ]
    single_brackets = [
        (0, 11925, 0.10), (11925, 48475, 0.12), (48475, 103350, 0.22),
        (103350, 197300, 0.24), (197300, 250525, 0.32), (250525, 626350, 0.35),
        (626350, float('inf'), 0.37)
    ]
    results = []
    roth = initial_roth_balance
    trad = initial_trad_balance
    prev_trad = initial_trad_balance
    gross_withdrawal_target = (initial_trad_balance + initial_roth_balance) * withdrawal_rate
    benefit_primary = calculate_adjusted_ss(ss_primary_fra, claim_age_primary, birth_year_primary)

    if filing_status == "married":
        benefit_spouse_own = calculate_adjusted_ss(ss_spouse_fra, claim_age_spouse, birth_year_spouse)
        potential_spousal = ss_primary_fra * 0.5
        spouse_fra_y, spouse_fra_m = get_fra(birth_year_spouse)
        spouse_fra_total = spouse_fra_y * 12 + spouse_fra_m
        spouse_claim_total = claim_age_spouse * 12
        if spouse_claim_total < spouse_fra_total:
            months_early = spouse_fra_total - spouse_claim_total
            if months_early <= 36: red = months_early * (25/36 / 100)
            else: red = (36 * (25/36 / 100)) + ((months_early - 36) * (5/12 / 100))
            potential_spousal *= (1 - red)
        benefit_spouse = max(benefit_spouse_own, potential_spousal)
    else:
        benefit_spouse = 0

    current_birth_year = 2025 - start_age
    rmd_start_age = 75 if current_birth_year >= 1960 else 73

    for age in range(start_age, end_age + 1):
        is_married_now = (filing_status == "married" and age <= spouse_death_age)
        current_status = "married" if is_married_now else "single"
        spouse_age = age - (birth_year_spouse - birth_year_primary) if filing_status == "married" else None
        current_ss = 0
        if age >= claim_age_primary: current_ss += benefit_primary * 12
        if filing_status == "married":
            if is_married_now:
                if spouse_age >= claim_age_spouse: current_ss += benefit_spouse * 12
            else: current_ss = max(benefit_primary, benefit_spouse) * 12
        ss = current_ss
        brackets = married_brackets if is_married_now else single_brackets
        if is_married_now: deduction = 30000 + (3200 if age >= 65 else 0)
        else: deduction = 15000 + (2000 if age >= 65 else 0)
        bracket_limit = brackets[2][1] if strategy == "A" else brackets[3][1]
        roth *= (1 + growth_rate)
        trad *= (1 + growth_rate)
        qcd_amount = 0
        if age >= 70:
            qcd_limit = 216000 if current_status == "married" else 108000
            qcd_amount = min(trad, qcd_limit, trad * qcd_percentage)
            trad -= qcd_amount
        rmd = calculate_rmd(prev_trad, age, rmd_start_age) if include_rmd else 0
        rmd_taxable_requirement = max(0, rmd - qcd_amount)
        rmd_taken = min(trad, rmd_taxable_requirement)
        trad -= rmd_taken

        def get_tax_data(test_trad_total):
            t_ss = calculate_taxable_ss(test_trad_total, pension_income, ss, current_status)
            t_inc = max(0, test_trad_total + pension_income + t_ss - deduction)
            t_tax = calculate_tax(t_inc, brackets)
            t_magi = test_trad_total + pension_income + t_ss
            t_med = calculate_medicare_premium(t_magi, current_status, age, spouse_age) if include_medicare else 0
            return t_inc, t_tax, t_med, t_magi

        remaining_target = max(0, gross_withdrawal_target - qcd_amount - rmd_taken)
        trad_for_target = min(trad, remaining_target)
        trad -= trad_for_target
        current_trad_wd = rmd_taken + trad_for_target
        remaining_target = max(0, gross_withdrawal_target - qcd_amount - current_trad_wd)
        roth_wd = min(roth, fixed_roth_withdrawal + (remaining_target if use_roth_buffer else 0))
        roth -= roth_wd
        roth_conv = 0
        best_surplus = 0
        if enable_roth_conversion:
            low, high = 0, trad
            for _ in range(40):
                mid = (low + high) / 2
                t_inc, _, _, _ = get_tax_data(current_trad_wd + mid)
                if t_inc <= bracket_limit - 1:
                    best_surplus = mid
                    low = mid
                else: high = mid
            if best_surplus > 0:
                _, taxes_now, med_now, _ = get_tax_data(current_trad_wd + best_surplus)
                _, taxes_base, med_base, _ = get_tax_data(current_trad_wd)
                shortfall_now = max(0, rmd - (current_trad_wd + best_surplus + qcd_amount))
                penalty_now = shortfall_now * 0.25
                shortfall_base = max(0, rmd - (current_trad_wd + qcd_amount))
                penalty_base = shortfall_base * 0.25
                net_now = (current_trad_wd + best_surplus + ss + pension_income + roth_wd) - (taxes_now + med_now + penalty_now)
                net_base = (current_trad_wd + ss + pension_income + roth_wd) - (taxes_base + med_base + penalty_base)
                if net_now > net_base:
                    roth_conv = net_now - net_base
                    trad -= best_surplus
                    roth += roth_conv
        total_withdrawn_this_year = current_trad_wd + (best_surplus if roth_conv > 0 else 0)
        taxable_income, taxes, medicare, magi = get_tax_data(total_withdrawn_this_year)
        shortfall = max(0, rmd - (total_withdrawn_this_year + qcd_amount))
        penalty = shortfall * 0.25
        net_income = (total_withdrawn_this_year + ss + pension_income + roth_wd) - (taxes + medicare + penalty + roth_conv)
        prev_trad = trad
        results.append({
            "Age": age, "Filing Status": current_status, "Social Security": ss,
            "Pension": pension_income, "Taxable Trad W/D": total_withdrawn_this_year,
            "Roth Withdrawal": roth_wd, "Roth Conversion": roth_conv,
            "QCD Amount": qcd_amount, "Traditional Balance": trad, "Roth Balance": roth,
            "RMD Required": rmd, "RMD Penalty": penalty, "Taxable Income": taxable_income,
            "MAGI": magi, "Taxes": taxes, "Medicare Cost": medicare, "Net Income": net_income,
            "Total Outflow": total_withdrawn_this_year + roth_wd + qcd_amount
        })
    return results

# -----------------------------
# STREAMLIT UI
# -----------------------------

# Page Configuration - MUST BE FIRST
st.set_page_config(
    page_title="Retirement Tax Conversion Strategy Simulator",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: white; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
</style>
""", unsafe_allow_html=True)

# Disclaimer logic
if 'disclaimer_accepted' not in st.session_state:
    st.session_state.disclaimer_accepted = False

if not st.session_state.disclaimer_accepted:
    st.title("💰 Retirement Tax Conversion Strategy Simulator")
    st.error("### Important Disclaimer")
    st.write("""
    This tool is provided for educational and informational purposes only. It does not constitute financial, investment, tax, or legal advice.
    The projections and outputs are based on assumptions and simplified models of complex rules. Actual results may differ significantly.
    By continuing, you acknowledge that you are solely responsible for your decisions and that the creator of this tool is not liable for any outcomes resulting from its use.
    """)
    if st.button("I Understand"):
        st.session_state.disclaimer_accepted = True
        st.rerun()
    st.stop()

# App Header
st.title("💰 Retirement Tax Conversion Strategy Simulator")
st.markdown("Compare withdrawal strategies to minimize taxes and optimize retirement income")

with st.expander("📖 Quick Start Guide"):
    st.write("""
    - **Withdrawal Rate:** Sets your **Gross Withdrawal Target** as a percentage of your initial total portfolio.
    - **Enable Roth Conversions:** If checked, fills tax brackets with conversions when income is below the limit.
    - **QCD Percentage:** specifies the % of Traditional IRA to donate to charity (70.5+).
    - **Spouse Death Age:** Models the "Widow's Penalty" by switching to Single filing status.
    """)

# Helper functions
def format_usd(val): return f"${val:,.0f}"
def summarize_results(results):
    total_taxes = sum(r["Taxes"] for r in results)
    total_medicare = sum(r["Medicare Cost"] for r in results)
    total_conversions = sum(r["Roth Conversion"] for r in results)
    total_qcds = sum(r["QCD Amount"] for r in results)
    total_expenses = total_taxes + total_medicare
    ending_balance = results[-1]["Roth Balance"] + results[-1]["Traditional Balance"]
    return {"taxes": total_taxes, "medicare": total_medicare, "conversions": total_conversions,
            "expenses": total_expenses, "balance": ending_balance, "qcds": total_qcds}

# Sidebar inputs
with st.sidebar:
    st.header("📋 Plan Your Retirement")
    with st.expander("👤 Personal Data", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            start_age = st.number_input("Starting Age", value=65, min_value=50, max_value=100)
            end_age = st.number_input("Ending Age", value=91, min_value=65, max_value=120)
        with col2:
            filing_status = st.selectbox("Filing Status", ["married", "single"], index=0)
            spouse_death_age = st.number_input("Spouse Death Age", value=79, min_value=50, max_value=120) if filing_status == "married" else 999
    with st.expander("💰 Portfolio", expanded=True):
        initial_roth = st.number_input("Initial Roth Balance ($)", value=1_500_000, step=10000)
        initial_trad = st.number_input("Initial Traditional Balance ($)", value=2_000_000, step=10000)
        growth_rate = st.number_input("Annual Growth Rate (%)", value=5.5, step=0.5) / 100
        withdrawal_rate = st.number_input("Annual Withdrawal Rate (%)", value=5.0, step=0.5) / 100
    with st.expander("🛡️ SS & Income", expanded=True):
        ss_primary_fra = st.number_input("Monthly SS at FRA ($)", value=3000, step=100)
        birth_year_primary = st.number_input("Birth Year", value=1960, min_value=1930, max_value=2025)
        claim_age_primary = st.number_input("Claiming Age", value=67, min_value=62, max_value=70)
        if filing_status == "married":
            st.divider()
            ss_spouse_fra = st.number_input("Spouse Monthly SS ($)", value=1500, step=100)
            birth_year_spouse = st.number_input("Spouse Birth Year", value=1962, min_value=1930, max_value=2025)
            claim_age_spouse = st.number_input("Spouse Claim Age", value=67, min_value=62, max_value=70)
        else:
            ss_spouse_fra, birth_year_spouse, claim_age_spouse = 0, 1960, 67
        st.divider()
        pension_income = st.number_input("Annual Pension ($)", value=30000, step=1000)
    with st.expander("⚙️ Strategy Settings", expanded=True):
        fixed_roth_withdrawal = st.number_input("Fixed Roth W/D ($)", value=0, step=1000)
        qcd_percentage = st.number_input("QCD %", value=0.0, step=0.1) / 100
        use_roth_buffer = st.checkbox("Use Roth as buffer", value=True)
        enable_roth_conversion = st.checkbox("Enable Roth Conversions", value=True)
    run_sim = st.button("Calculate Scenarios", type="primary", use_container_width=True)

# Main logic
if run_sim or 'results_a' in st.session_state:
    try:
        params = {"start_age": start_age, "end_age": end_age, "spouse_death_age": spouse_death_age,
                  "initial_roth_balance": initial_roth, "initial_trad_balance": initial_trad,
                  "growth_rate": growth_rate, "pension_income": pension_income, "withdrawal_rate": withdrawal_rate,
                  "fixed_roth_withdrawal": fixed_roth_withdrawal, "use_roth_buffer": use_roth_buffer,
                  "qcd_percentage": qcd_percentage, "enable_roth_conversion": enable_roth_conversion,
                  "filing_status": filing_status, "ss_primary_fra": ss_primary_fra,
                  "birth_year_primary": birth_year_primary, "claim_age_primary": claim_age_primary,
                  "ss_spouse_fra": ss_spouse_fra, "birth_year_spouse": birth_year_spouse,
                  "claim_age_spouse": claim_age_spouse}
        if run_sim:
            st.session_state.results_a = simulate_retirement(**params, strategy="A")
            st.session_state.results_b = simulate_retirement(**params, strategy="B")
        results_a, results_b = st.session_state.results_a, st.session_state.results_b
        summary_a, summary_b = summarize_results(results_a), summarize_results(results_b)

        tab1, tab2, tab3 = st.tabs(["📊 Summary", "📈 Charts", "📄 Details"])
        with tab1:
            st.subheader("⚖️ Scenario Comparison")
            col_a, col_b, col_diff = st.columns(3)
            with col_a:
                st.info("### Scenario A\nStop at 22%")
                for k, v in summary_a.items(): st.metric(k.capitalize(), format_usd(v))
            with col_b:
                st.success("### Scenario B\nStop at 24%")
                for k, v in summary_b.items(): st.metric(k.capitalize(), format_usd(v))
            with col_diff:
                st.warning("### Difference\n(A - B)")
                for k in summary_a.keys():
                    diff = summary_a[k] - summary_b[k]
                    is_good = (diff < 0) if k in ["taxes", "medicare", "expenses"] else (diff > 0)
                    st.metric(k.capitalize(), format_usd(diff), delta="Better" if is_good else "Worse", delta_color="normal" if is_good else "inverse")
        with tab2:
            st.subheader("📈 Growth & Conversions")
            fig = go.Figure()
            ages = [r["Age"] for r in results_a]
            fig.add_trace(go.Scatter(x=ages, y=[r["Roth Balance"]+r["Traditional Balance"] for r in results_a], name="A: Balance", line=dict(color='#4299e1', width=3)))
            fig.add_trace(go.Scatter(x=ages, y=[r["Roth Balance"]+r["Traditional Balance"] for r in results_b], name="B: Balance", line=dict(color='#ed8936', width=3, dash='dash')))
            fig.add_trace(go.Bar(x=ages, y=[r["Roth Conversion"] for r in results_a], name="A: Conversion", marker_color='#48bb78', opacity=0.5, yaxis='y2'))
            fig.add_trace(go.Bar(x=ages, y=[r["Roth Conversion"] for r in results_b], name="B: Conversion", marker_color='#38b2ac', opacity=0.5, yaxis='y2'))
            fig.update_layout(template="plotly_white", legend=dict(orientation="h", y=1.05), yaxis=dict(title="Balance"), yaxis2=dict(title="Conversion", side="right", overlaying='y', showgrid=False), hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)
        with tab3:
            sel = st.radio("Select Scenario:", ["A", "B"], horizontal=True)
            df = pd.DataFrame(results_a if sel=="A" else results_b)
            for c in df.columns:
                if c not in ["Age", "Filing Status"]: df[c] = df[c].apply(lambda x: f"${x:,.2f}")
            st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.error(f"Error in simulation: {str(e)}")
else:
    st.info("👈 Fill in details and click 'Calculate Scenarios'")

# Footer
st.divider()
st.markdown("<div style='text-align: center; color: #666; font-size: 0.85em;'>Disclaimer: Educational use only. Support: <a href='https://paypal.me/tsy19'>paypal.me/tsy19</a></div>", unsafe_allow_html=True)
