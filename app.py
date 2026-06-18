import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import os
import time

# Import tools/resources directly from the FastMCP server module to simulate MCP tool execution
import server

# Page Config
st.set_page_config(
    page_title="Cognitive Risk Hub",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Premium Styling (Dark Theme & Glassmorphism Feel)
st.markdown("""
<style>
    .reportview-container {
        background: #0f172a;
    }
    .metric-card {
        background: rgba(30, 41, 59, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        backdrop-filter: blur(12px);
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        margin: 5px 0;
    }
    .metric-label {
        font-size: 0.875rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .agent-box {
        background: #090d16;
        border-left: 4px solid #0ea5e9;
        font-family: 'Courier New', Courier, monospace;
        padding: 15px;
        border-radius: 4px;
        color: #38bdf8;
        margin-bottom: 10px;
        height: 250px;
        overflow-y: auto;
    }
    .badge-green {
        background-color: #065f46;
        color: #34d399;
        padding: 4px 8px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# Load holdings via FastMCP resource holdings://default
def load_holdings():
    holdings_json = server.get_holdings()
    return pd.DataFrame(json.loads(holdings_json))

# Initialize session state variables
if "holdings_df" not in st.session_state:
    st.session_state.holdings_df = load_holdings()
if "active_scenario" not in st.session_state:
    st.session_state.active_scenario = None
if "agent_logs" not in st.session_state:
    st.session_state.agent_logs = []
if "stress_results" not in st.session_state:
    st.session_state.stress_results = None
if "inputs" not in st.session_state:
    st.session_state.inputs = {
        "market_shock": 0.0,
        "interest_rate_shock_bps": 0.0,
        "commodity_shock": 0.0,
        "panic_factor": 0.0
    }

# ----------------- SIDEBAR -----------------
with st.sidebar:
    st.image("https://img.icons8.com/nolan/128/shield.png", width=70)
    st.title("Cognitive Risk Hub")
    st.markdown("---")
    
    # MCP Connection Status
    st.subheader("🔌 Model Context Protocol")
    st.markdown("""
    **Server State:** <span class="badge-green">ONLINE</span>  
    **Framework:** FastMCP (Python)  
    **Host:** Localhost (stdio transport)
    """, unsafe_allow_html=True)
    
    st.markdown("### Exponentiated Resources")
    st.code("holdings://default", language="text")
    
    st.markdown("### Registered Tools")
    st.code("""
- fetch_financial_news()
- analyze_market_correlations()
- run_stress_test()
    """, language="text")
    
    st.markdown("---")
    st.subheader("📁 Custom Portfolio Data")
    
    # Template download
    template_df = pd.DataFrame([
        {
            "ticker": "MSFT", 
            "name": "Microsoft Corporation", 
            "asset_class": "Equities", 
            "sector": "Technology", 
            "value": 15000000.0, 
            "beta_market": 1.2, 
            "beta_interest": -0.3, 
            "beta_commodity": 0.0
        },
        {
            "ticker": "US10Y", 
            "name": "US 10-Year Bond", 
            "asset_class": "Fixed Income", 
            "sector": "Government", 
            "value": 25000000.0, 
            "beta_market": -0.1, 
            "beta_interest": -5.0, 
            "beta_commodity": 0.0
        }
    ])
    template_csv = template_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download CSV Template",
        data=template_csv,
        file_name="portfolio_template.csv",
        mime="text/csv",
        key="download_template_btn"
    )
    
    uploaded_file = st.file_uploader("Upload custom CSV:", type=["csv"])
    if uploaded_file is not None:
        try:
            custom_df = pd.read_csv(uploaded_file)
            
            # Clean and normalize column names
            custom_df.columns = [str(col).strip().lower().replace(" ", "_").replace("-", "_") for col in custom_df.columns]
            
            # Define synonyms map for flexible headers
            synonyms = {
                "ticker": ["ticker", "symbol", "code", "asset_id", "id", "ticker_symbol", "asset_code"],
                "name": ["name", "asset", "title", "description", "label", "security", "company"],
                "asset_class": ["asset_class", "assetclass", "assets", "type", "class", "category_class", "group"],
                "sector": ["sector", "industry", "segment", "area", "business"],
                "value": ["value", "amount", "balance", "valuation", "nav", "price", "size", "current_value", "market_value", "total"]
            }
            
            # Map column names based on synonyms
            rename_dict = {}
            for col in custom_df.columns:
                for target_col, synonyms_list in synonyms.items():
                    if col in synonyms_list:
                        rename_dict[col] = target_col
                        break
            
            custom_df = custom_df.rename(columns=rename_dict)
            
            # --- Bulletproof Column Fallbacks ---
            
            # 1. Ticker fallback
            if "ticker" not in custom_df.columns:
                string_cols = custom_df.select_dtypes(include=['object']).columns
                if len(string_cols) > 0:
                    custom_df["ticker"] = custom_df[string_cols[0]]
                else:
                    custom_df["ticker"] = [f"ASSET-{i+1}" for i in range(len(custom_df))]
            
            # 2. Name fallback
            if "name" not in custom_df.columns:
                custom_df["name"] = custom_df["ticker"]
                
            # 3. Value fallback
            if "value" not in custom_df.columns:
                num_cols = custom_df.select_dtypes(include=['number']).columns
                if len(num_cols) > 0:
                    custom_df["value"] = custom_df[num_cols[0]]
                else:
                    custom_df["value"] = 1000000.0 # Default constant
            
            # 4. Asset Class fallback
            if "asset_class" not in custom_df.columns:
                def guess_class(t):
                    t_low = str(t).lower()
                    if any(k in t_low for k in ["bond", "note", "treasury", "yield", "10y", "02y", "govt", "fixed"]):
                        return "Fixed Income"
                    elif any(k in t_low for k in ["cash", "usd", "eur", "gbp", "jpy"]):
                        return "Cash"
                    else:
                        return "Equities"
                custom_df["asset_class"] = custom_df["ticker"].apply(guess_class)
                
            # 5. Sector fallback
            if "sector" not in custom_df.columns:
                def guess_sector(row):
                    cls = row["asset_class"]
                    if cls == "Fixed Income":
                        return "Government"
                    elif cls == "Cash":
                        return "Cash"
                    else:
                        return "Technology"
                custom_df["sector"] = custom_df.apply(guess_sector, axis=1)
                
            # 6. Betas fallback
            for beta_col in ["beta_market", "beta_interest", "beta_commodity"]:
                if beta_col not in custom_df.columns:
                    if beta_col == "beta_market":
                        custom_df["beta_market"] = custom_df["asset_class"].apply(lambda x: 1.0 if x == "Equities" else 0.0)
                    elif beta_col == "beta_interest":
                        custom_df["beta_interest"] = custom_df["asset_class"].apply(lambda x: -3.0 if x == "Fixed Income" else 0.0)
                    elif beta_col == "beta_commodity":
                        custom_df["beta_commodity"] = custom_df["asset_class"].apply(lambda x: 1.2 if x == "Energy" else 0.0)
            
            # Final conversion and cleaning
            custom_df["value"] = pd.to_numeric(custom_df["value"], errors='coerce').fillna(1000000.0)
            for beta_col in ["beta_market", "beta_interest", "beta_commodity"]:
                custom_df[beta_col] = pd.to_numeric(custom_df[beta_col], errors='coerce').fillna(0.0)
                
            # Extract clean normalized dataframe
            clean_df = custom_df[["ticker", "name", "asset_class", "sector", "value", "beta_market", "beta_interest", "beta_commodity"]].copy()
            
            st.session_state.holdings_df = clean_df
            st.sidebar.success("Custom portfolio loaded successfully!")
        except Exception as e:
            st.error(f"Error parsing CSV: {e}")

    st.markdown("---")
    st.markdown("⚡ *AI Research Agent Status:* **Idle**")

# ----------------- MAIN LAYOUT -----------------
st.title("🛡️ AI-Driven Stress Testing & Risk Synthesis")
st.markdown("Autonomously aggregate correlations, generate stress parameters, and visualize enterprise capital impacts.")

# Create tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Portfolio Allocation", 
    "📰 News Synthesis Feed", 
    "📈 Stress Test Sandbox", 
    "📝 Executive CRO Memo"
])

# ----------------- TAB 1: PORTFOLIO ALLOCATION -----------------
with tab1:
    st.subheader("Baseline Portfolio Metrics")
    
    # Calculate baseline sums
    total_nav = st.session_state.holdings_df["value"].sum()
    equity_nav = st.session_state.holdings_df[st.session_state.holdings_df["asset_class"] == "Equities"]["value"].sum()
    bond_nav = st.session_state.holdings_df[st.session_state.holdings_df["asset_class"] == "Fixed Income"]["value"].sum()
    cash_nav = st.session_state.holdings_df[st.session_state.holdings_df["asset_class"] == "Cash"]["value"].sum()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Total Portfolio NAV</div>
            <div class="metric-value" style="color: #38bdf8;">${total_nav/1e6:.1f}M</div>
            <div class="metric-label">Base Valuation</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Equity Allocation</div>
            <div class="metric-value" style="color: #6366f1;">{equity_nav/total_nav*100:.1f}%</div>
            <div class="metric-label">${equity_nav/1e6:.1f}M Exposure</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Fixed Income Allocation</div>
            <div class="metric-value" style="color: #a855f7;">{bond_nav/total_nav*100:.1f}%</div>
            <div class="metric-label">${bond_nav/1e6:.1f}M Exposure</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Capital Adequacy Ratio (CAR)</div>
            <div class="metric-value" style="color: #34d399;">14.50%</div>
            <div class="metric-label">Reg. Minimum: 8.00%</div>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("### Portfolio Breakdown")
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        # Pie Chart Sector
        fig_sec = px.pie(
            st.session_state.holdings_df, 
            values='value', 
            names='sector', 
            title='Sector Allocation',
            color_discrete_sequence=px.colors.qualitative.Dark24,
            hole=0.4
        )
        fig_sec.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="#94a3b8")
        st.plotly_chart(fig_sec, use_container_width=True)
        
    with col_chart2:
        # Bar Chart Class
        fig_class = px.bar(
            st.session_state.holdings_df,
            x='asset_class',
            y='value',
            color='sector',
            title='Exposure by Asset Class and Sector',
            labels={'value': 'Value (USD)', 'asset_class': 'Asset Class'},
            color_discrete_sequence=px.colors.qualitative.Dark24
        )
        fig_class.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="#94a3b8")
        st.plotly_chart(fig_class, use_container_width=True)

    st.subheader("Asset Holdings Ledger")
    st.dataframe(
        st.session_state.holdings_df[["ticker", "name", "asset_class", "sector", "value", "beta_market", "beta_interest", "beta_commodity"]].rename(
            columns={"value": "Current Value (USD)", "beta_market": "Equity Beta", "beta_interest": "Interest Rate Beta", "beta_commodity": "Commodity Beta"}
        ),
        use_container_width=True
    )

# ----------------- TAB 2: NEWS SYNTHESIS FEED -----------------
with tab2:
    st.subheader("Live News & Custom Risk Synthesis")
    st.markdown("Select an incoming headline from the live feed or copy-paste your own news article to run the AI Research Agent.")
    
    col_news1, col_news2 = st.columns(2)
    
    with col_news1:
        st.markdown("### 📰 Option A: Select from Live Feed")
        news_data = json.loads(server.fetch_financial_news())
        
        if news_data and not isinstance(news_data, dict):
            selected_idx = st.selectbox(
                "Live News Headlines:",
                options=range(len(news_data)),
                format_func=lambda x: f"[{news_data[x]['category']}] {news_data[x]['headline']} ({news_data[x]['severity']} Severity)",
                key="live_news_selectbox"
            )
            selected_live_news = news_data[selected_idx]
            st.info(f"**Live Description:** {selected_live_news['description'] if selected_live_news['description'] else 'No description available.'}")
        else:
            st.warning("Could not fetch live headlines. Please use Option B below.")
            selected_live_news = None
            
    with col_news2:
        st.markdown("### ✏️ Option B: Paste Custom News / Source")
        custom_headline = st.text_area(
            "Paste news headline, article text, or source description:", 
            placeholder="Type or paste news here (e.g., 'Central Bank announces surprise interest rate hike of 150 basis points due to high inflation...')"
        )
        
        col_meta1, col_meta2 = st.columns(2)
        with col_meta1:
            custom_category = st.selectbox(
                "Assigned Risk Category:",
                options=["Auto-Detect", "Monetary Policy", "Geopolitical", "Liquidity", "Cyber", "Technology"],
                key="custom_news_category"
            )
        with col_meta2:
            custom_severity = st.selectbox(
                "Assigned Severity Level:",
                options=["Auto-Detect", "Low", "Medium", "High"],
                key="custom_news_severity"
            )

    # Ingestion Trigger Button
    st.markdown("---")
    if st.button("🧬 Analyze News & Synthesize Risk", type="primary", key="trigger_analysis_btn"):
        active_news = None
        
        # Check if the user pasted custom news
        if custom_headline.strip():
            headline_text = custom_headline.strip()
            
            # Auto-detect category
            if custom_category == "Auto-Detect":
                low_text = headline_text.lower()
                detected_cat = "Technology"
                if any(k in low_text for k in ["fed", "hike", "cut", "inflation", "cpi", "rate", "yield", "central bank", "powell", "monetary"]):
                    detected_cat = "Monetary Policy"
                elif any(k in low_text for k in ["war", "tariff", "border", "geopolitical", "sanction", "conflict", "china", "russia", "middle east"]):
                    detected_cat = "Geopolitical"
                elif any(k in low_text for k in ["liquidity", "run", "deposit", "withdrawal", "reserve", "default", "bankruptcy", "banking"]):
                    detected_cat = "Liquidity"
                elif any(k in low_text for k in ["cyber", "exploit", "hack", "ransomware", "breach", "outage", "security", "zero-day"]):
                    detected_cat = "Cyber"
            else:
                detected_cat = custom_category
                
            # Auto-detect severity
            if custom_severity == "Auto-Detect":
                low_text = headline_text.lower()
                detected_sev = "Low"
                if any(k in low_text for k in ["crash", "crisis", "collapse", "blockade", "surge", "plunge", "plummet", "escalates"]):
                    detected_sev = "High"
                elif any(k in low_text for k in ["warning", "drop", "rise", "jump", "fear", "delay"]):
                    detected_sev = "Medium"
            else:
                detected_sev = custom_severity
                
            active_news = {
                "id": "CUSTOM-001",
                "headline": headline_text[:80] + ("..." if len(headline_text) > 80 else ""),
                "source": "Custom User Input",
                "category": detected_cat,
                "severity": detected_sev,
                "description": headline_text
            }
        else:
            active_news = selected_live_news
            
        if active_news:
            st.session_state.active_scenario = active_news
            
            # Simulate Agent Thinking Process
            logs = []
            with st.spinner("Agent running correlation synthesis..."):
                logs.append("[INFO] Research Agent activated.")
                logs.append(f"[PROCESS] Ingesting news from: {active_news['source']}.")
                logs.append(f"[PROCESS] Headline: \"{active_news['headline']}\"")
                time.sleep(0.3)
                logs.append(f"[PROCESS] Classifying risk sector under category: {active_news['category']}.")
                
                # Call MCP tool: analyze_market_correlations
                corr_json = server.analyze_market_correlations(active_news["category"])
                corr_data = json.loads(corr_json)
                
                logs.append("[SUCCESS] Correlation mapping completed.")
                logs.append(f"[ANALYSIS] Vulnerable Sectors identified: {', '.join(corr_data['vulnerable_sectors'])}")
                logs.append(f"[ANALYSIS] Resilient Sectors identified: {', '.join(corr_data['resilient_sectors'])}")
                time.sleep(0.2)
                logs.append(f"[PARAMETER GENERATION] Proposing shocks: Market {corr_data['market_shock']*100:.1f}%, Rates {corr_data['interest_rate_shock_bps']:.0f} bps, Commodity {corr_data['commodity_shock']*100:.1f}%")
                
                # Update Sandbox parameters
                st.session_state.inputs["market_shock"] = corr_data["market_shock"]
                st.session_state.inputs["interest_rate_shock_bps"] = corr_data["interest_rate_shock_bps"]
                st.session_state.inputs["commodity_shock"] = corr_data["commodity_shock"]
                st.session_state.inputs["panic_factor"] = 0.60 if active_news["severity"] == "High" else (0.30 if active_news["severity"] == "Medium" else 0.10)
                
            st.session_state.agent_logs = logs
            st.success("Analysis complete! Parameter updates transferred to Sandbox.")
        else:
            st.error("No active news found. Please select a headline or paste your own custom news.")
            
    # Show Agent logs
    if st.session_state.agent_logs:
        st.markdown("### 🤖 Agent Cognitive Thought Process Log")
        log_content = "\n".join(st.session_state.agent_logs)
        st.markdown(f'<div class="agent-box">{log_content}</div>', unsafe_allow_html=True)
        
        # Simple SVG Knowledge Graph Visualization
        st.markdown("### 🕸️ Semantic Risk Propagation Graph")
        
        if st.session_state.active_scenario:
            category = st.session_state.active_scenario["category"]
            corr_data = json.loads(server.analyze_market_correlations(category))
            vuln_sec = corr_data["vulnerable_sectors"]
            res_sec = corr_data["resilient_sectors"]
            
            # Simple SVG layout representing a knowledge graph
            svg_code = f"""
            <svg width="100%" height="250" style="background:#090d16; border-radius: 8px;">
                <!-- Center Node (Trigger) -->
                <circle cx="150" cy="125" r="40" fill="#f43f5e" opacity="0.2"/>
                <circle cx="150" cy="125" r="30" fill="#ef4444"/>
                <text x="150" y="130" fill="white" font-weight="bold" font-family="sans-serif" font-size="12" text-anchor="middle">{category}</text>
                
                <!-- Line connections -->
                <line x1="180" y1="125" x2="350" y2="75" stroke="#ef4444" stroke-width="2" stroke-dasharray="5,5"/>
                <line x1="180" y1="125" x2="350" y2="175" stroke="#10b981" stroke-width="2"/>
                
                <!-- Vulnerable Node -->
                <circle cx="350" cy="75" r="35" fill="#f43f5e" opacity="0.2"/>
                <circle cx="350" cy="75" r="25" fill="#f43f5e"/>
                <text x="350" y="80" fill="white" font-family="sans-serif" font-size="10" text-anchor="middle">Vulnerable</text>
                <text x="350" y="130" fill="#94a3b8" font-family="sans-serif" font-size="10" text-anchor="middle">({vuln_sec[0] if vuln_sec else 'None'})</text>
                
                <!-- Resilient Node -->
                <circle cx="350" cy="175" r="35" fill="#10b981" opacity="0.2"/>
                <circle cx="350" cy="175" r="25" fill="#10b981"/>
                <text x="350" y="180" fill="white" font-family="sans-serif" font-size="10" text-anchor="middle">Resilient</text>
                <text x="350" y="230" fill="#94a3b8" font-family="sans-serif" font-size="10" text-anchor="middle">({res_sec[0] if res_sec else 'None'})</text>
                
                <!-- Risk propagation arrows -->
                <path d="M 230 110 L 250 100 L 245 115 Z" fill="#ef4444"/>
                <path d="M 230 140 L 250 150 L 245 135 Z" fill="#10b981"/>
            </svg>
            """
            st.markdown(svg_code, unsafe_allow_html=True)

# ----------------- TAB 3: STRESS TEST SANDBOX -----------------
with tab3:
    st.subheader("Configure Stress Testing Parameters")
    st.markdown("Fine-tune parameters manually or use synthesized inputs from the News Feed tab.")
    
    col_in1, col_in2, col_in3, col_in4 = st.columns(4)
    with col_in1:
        m_shock = st.slider(
            "Market Shock (Equity Decline %)", 
            min_value=-50, 
            max_value=10, 
            value=int(st.session_state.inputs["market_shock"] * 100),
            step=5
        ) / 100.0
    with col_in2:
        r_shock = st.slider(
            "Interest Rate Shock (bps)", 
            min_value=-100, 
            max_value=400, 
            value=int(st.session_state.inputs["interest_rate_shock_bps"]),
            step=25
        )
    with col_in3:
        c_shock = st.slider(
            "Commodity Shock (Oil % Change)", 
            min_value=-30, 
            max_value=100, 
            value=int(st.session_state.inputs["commodity_shock"] * 100),
            step=5
        ) / 100.0
    with col_in4:
        p_factor = st.slider(
            "Panic Factor (Liquidity Run Multiplier)", 
            min_value=0.0, 
            max_value=1.0, 
            value=float(st.session_state.inputs["panic_factor"]),
            step=0.1
        )
        
    if st.button("🚀 Execute AI Stress Test Calculations", type="primary"):
        # Call FastMCP tool: run_stress_test
        res_json = server.run_stress_test(
            market_shock=m_shock,
            interest_rate_shock_bps=r_shock,
            commodity_shock=c_shock,
            panic_factor=p_factor,
            custom_holdings=st.session_state.holdings_df.to_dict('records')
        )
        st.session_state.stress_results = json.loads(res_json)
        st.success("Stress testing scenario computed successfully!")
        
    if st.session_state.stress_results:
        res = st.session_state.stress_results
        metrics = res["metrics"]
        
        # Display Stressed Metrics
        st.markdown("### Stress Test Impact Summary")
        col_res1, col_res2, col_res3, col_res4 = st.columns(4)
        
        nav_delta = metrics["stressed_nav"] - metrics["baseline_nav"]
        nav_color = "#ef4444" if nav_delta < 0 else "#34d399"
        
        with col_res1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Stressed Portfolio NAV</div>
                <div class="metric-value" style="color: {nav_color};">${metrics['stressed_nav']/1e6:.1f}M</div>
                <div class="metric-label">Change: {metrics['nav_change_pct']}% (${nav_delta/1e6:.2f}M)</div>
            </div>
            """, unsafe_allow_html=True)
            
        car_color = "#ef4444" if metrics["stressed_car_pct"] < 8.0 else "#34d399"
        with col_res2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Stressed CAR (Capital Adequacy)</div>
                <div class="metric-value" style="color: {car_color};">{metrics['stressed_car_pct']:.2f}%</div>
                <div class="metric-label">Baseline: {metrics['baseline_car_pct']:.2f}% (Limit: 8%)</div>
            </div>
            """, unsafe_allow_html=True)
            
        lcr_color = "#ef4444" if metrics["stressed_lcr_pct"] < 100.0 else "#34d399"
        with col_res3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Stressed LCR (Liquidity)</div>
                <div class="metric-value" style="color: {lcr_color};">{metrics['stressed_lcr_pct']:.1f}%</div>
                <div class="metric-label">Baseline: {metrics['baseline_lcr_pct']:.1f}% (Limit: 100%)</div>
            </div>
            """, unsafe_allow_html=True)
            
        # Overall stress rating
        rating = "Low"
        rating_color = "#34d399"
        if metrics["nav_change_pct"] <= -10.0 or metrics["stressed_car_pct"] < 8.0 or metrics["stressed_lcr_pct"] < 100.0:
            rating = "CRITICAL LIMIT BREACH"
            rating_color = "#ef4444"
        elif metrics["nav_change_pct"] <= -5.0:
            rating = "Elevated Warning"
            rating_color = "#fbbf24"
            
        with col_res4:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Vulnerability Rating</div>
                <div class="metric-value" style="color: {rating_color}; font-size: 1.25rem; padding-top: 10px;">{rating}</div>
                <div class="metric-label">System Assessment</div>
            </div>
            """, unsafe_allow_html=True)

        # Plotly comparison
        st.markdown("### Baseline vs. Stressed Asset Value Comparison")
        df_res = pd.DataFrame(res["holdings"])
        
        fig_compare = go.Figure()
        fig_compare.add_trace(go.Bar(
            name='Baseline Value',
            x=df_res['ticker'], y=df_res['baseline_value'],
            marker_color='#3b82f6'
        ))
        fig_compare.add_trace(go.Bar(
            name='Stressed Value',
            x=df_res['ticker'], y=df_res['stressed_value'],
            marker_color='#ef4444'
        ))
        fig_compare.update_layout(
            barmode='group',
            paper_bgcolor='rgba(0,0,0,0)', 
            plot_bgcolor='rgba(0,0,0,0)', 
            font_color="#94a3b8",
            title="Individual Asset Valuation Depreciation"
        )
        st.plotly_chart(fig_compare, use_container_width=True)
        
        st.subheader("Granular Asset Shock Matrix")
        st.dataframe(
            df_res[["ticker", "name", "asset_class", "sector", "baseline_value", "stressed_value", "change_pct"]].rename(
                columns={
                    "baseline_value": "Baseline NAV (USD)",
                    "stressed_value": "Stressed NAV (USD)",
                    "change_pct": "Simulated Loss (%)"
                }
            ),
            use_container_width=True
        )

# ----------------- TAB 4: EXECUTIVE CRO MEMO -----------------
with tab4:
    st.subheader("Automated Executive Risk Memo Writer")
    st.markdown("Dynamic synthesis report created by the Research Agent based on stress parameters and findings.")
    
    if st.session_state.stress_results:
        metrics = st.session_state.stress_results["metrics"]
        headline = st.session_state.active_scenario["headline"] if st.session_state.active_scenario else "Manual Parameters Simulation"
        category = st.session_state.active_scenario["category"] if st.session_state.active_scenario else "Custom Shock"
        
        # Assess status
        car_status = "STABLE" if metrics['stressed_car_pct'] >= 8.0 else "⚠️ COMPLIANCE BREACH"
        lcr_status = "STABLE" if metrics['stressed_lcr_pct'] >= 100.0 else "⚠️ COMPLIANCE BREACH"
        
        memo_template = f"""# EXECUTIVE RISK MEMO: AI-DRIVEN SCENARIO STRESS TEST
**To:** Board of Directors & Risk Committee  
**From:** Cognitive Risk Hub Agent  
**Date:** {time.strftime("%B %d, %Y")}  
**Status:** Confidential - Internal Risk Review  

---

### 1. TRIGGER SCENARIO OVERVIEW
The research agent has synthesized parameters simulating:
* **Trigger Event:** {headline}
* **Shock Category:** {category}
* **Applied Shocks:** Market Shock: {m_shock*100:.1f}%, Rate Shock: {r_shock:.0f} bps, Commodity Shock: {c_shock*100:.1f}%, Panic factor: {p_factor*100:.0f}%

### 2. FINANCIAL IMPACT SUMMARY
* **Baseline Portfolio NAV:** ${metrics['baseline_nav']/1e6:.2f}M  
* **Stressed Portfolio NAV:** ${metrics['stressed_nav']/1e6:.2f}M  
* **Estimated Portfolio Capital Loss:** ${abs(metrics['stressed_nav'] - metrics['baseline_nav'])/1e6:.2f}M ({metrics['nav_change_pct']}%)  

### 3. REGULATORY CAPITAL & LIQUIDITY IMPACTS
* **Tier 1 Capital Adequacy Ratio (CAR):**
  * Baseline: {metrics['baseline_car_pct']:.2f}% | Stressed: {metrics['stressed_car_pct']:.2f}%  
  * Regulatory Compliance Status: **{car_status}**
* **Liquidity Coverage Ratio (LCR):**
  * Baseline: {metrics['baseline_lcr_pct']:.1f}% | Stressed: {metrics['stressed_lcr_pct']:.1f}%  
  * Regulatory Compliance Status: **{lcr_status}**

### 4. RECOMMENDATIONS & HEDGING ACTIONS
1. **Reduce Portfolio Duration:** The fixed income portfolio experienced depreciation under high-rate shock conditions. Propose short-duration shifting.
2. **Execute Equity Protections:** Equity holdings (specifically Tech/Consumer) were heavily impacted by the market downturn. Recommend purchasing out-of-the-money put options on key indexes.
3. **Liquidity Facility Activation:** Since LCR dropped to {metrics['stressed_lcr_pct']:.1f}%, prepare activation of secondary central bank discount window capabilities to hedge against deposit drain.
"""
        # Editable Memo Box
        edited_memo = st.text_area(
            "Draft Memo (Edit as needed):", 
            value=memo_template, 
            height=400
        )
        
        st.markdown("### Rendered Document Preview")
        st.markdown(edited_memo)
    else:
        st.warning("No stress test results found. Please configure and run a simulation in the 'Stress Test Sandbox' tab to generate a memo.")
