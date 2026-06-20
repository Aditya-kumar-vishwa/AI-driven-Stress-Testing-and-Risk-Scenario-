import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import os
import time
from dotenv import load_dotenv
import streamlit.components.v1 as components

# Load environment variables
load_dotenv()

# Import tools/resources directly from the FastMCP server module
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
        height: 280px;
        overflow-y: auto;
        font-size: 0.9rem;
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

# Render Vis.js network graph
def render_interactive_graph(category, vuln_sectors, res_sectors, holdings_df):
    nodes = []
    edges = []
    
    # Root news trigger node
    nodes.append({
        "id": "root", 
        "label": f"Risk Trigger:\n{category}", 
        "color": "#ef4444", 
        "shape": "dot", 
        "size": 25, 
        "font": {"color": "#ffffff", "size": 13, "bold": True}
    })
    
    # Vulnerable sectors
    for i, sec in enumerate(vuln_sectors):
        node_id = f"vuln_sec_{i}"
        nodes.append({
            "id": node_id, 
            "label": f"Vulnerable:\n{sec}", 
            "color": "#f43f5e", 
            "shape": "dot", 
            "size": 18, 
            "font": {"color": "#ffffff", "size": 11}
        })
        edges.append({"from": "root", "to": node_id, "color": "#f43f5e", "width": 3, "dashes": True})
        
        # Link corresponding tickers in this sector
        tickers = holdings_df[holdings_df["sector"] == sec]["ticker"].tolist()
        for tk in tickers:
            tk_id = f"tk_{tk}"
            nodes.append({
                "id": tk_id, 
                "label": f"Asset: {tk}", 
                "color": "#fda4af", 
                "shape": "box", 
                "font": {"color": "#000000", "size": 10}
            })
            edges.append({"from": node_id, "to": tk_id, "color": "#fda4af", "width": 1.5})
            
    # Resilient sectors
    for i, sec in enumerate(res_sectors):
        node_id = f"res_sec_{i}"
        nodes.append({
            "id": node_id, 
            "label": f"Resilient:\n{sec}", 
            "color": "#10b981", 
            "shape": "dot", 
            "size": 18, 
            "font": {"color": "#ffffff", "size": 11}
        })
        edges.append({"from": "root", "to": node_id, "color": "#10b981", "width": 3})
        
        # Link corresponding tickers in this sector
        tickers = holdings_df[holdings_df["sector"] == sec]["ticker"].tolist()
        for tk in tickers:
            tk_id = f"tk_{tk}"
            nodes.append({
                "id": tk_id, 
                "label": f"Asset: {tk}", 
                "color": "#6ee7b7", 
                "shape": "box", 
                "font": {"color": "#000000", "size": 10}
            })
            edges.append({"from": node_id, "to": tk_id, "color": "#6ee7b7", "width": 1.5})
            
    # Other portfolio holdings not in the main vuln/res categories
    all_main_secs = set(vuln_sectors + res_sectors)
    other_holdings = holdings_df[~holdings_df["sector"].isin(all_main_secs)]
    if not other_holdings.empty:
        other_node_id = "other_sec"
        nodes.append({
            "id": other_node_id, 
            "label": "Other Portfolios", 
            "color": "#6b7280", 
            "shape": "dot", 
            "size": 14, 
            "font": {"color": "#ffffff", "size": 10}
        })
        edges.append({"from": "root", "to": other_node_id, "color": "#6b7280", "width": 1.5})
        
        for _, row in other_holdings.iterrows():
            tk = row["ticker"]
            tk_id = f"tk_{tk}"
            nodes.append({
                "id": tk_id, 
                "label": f"Asset: {tk}\n({row['sector']})", 
                "color": "#e5e7eb", 
                "shape": "box", 
                "font": {"color": "#000000", "size": 9}
            })
            edges.append({"from": other_node_id, "to": tk_id, "color": "#d1d5db", "width": 1.0})
            
    nodes_json = json.dumps(nodes)
    edges_json = json.dumps(edges)
    
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
        <style type="text/css">
            html, body {{
                margin: 0;
                padding: 0;
                width: 100%;
                height: 100%;
                overflow: hidden;
                background-color: #090d16;
            }}
            #network {{
                width: 100%;
                height: 100%;
            }}
        </style>
    </head>
    <body>
        <div id="network"></div>
        <script type="text/javascript">
            var container = document.getElementById('network');
            var data = {{
                nodes: new vis.DataSet({nodes_json}),
                edges: new vis.DataSet({edges_json})
            }};
            var options = {{
                nodes: {{
                    font: {{ face: 'Arial', size: 12 }},
                    borderWidth: 1.5,
                    shadow: true
                }},
                edges: {{
                    smooth: {{ type: 'continuous', roundness: 0.5 }},
                    shadow: true
                }},
                physics: {{
                    stabilization: {{ iterations: 100 }},
                    barnesHut: {{
                        gravitationalConstant: -2000,
                        centralGravity: 0.3,
                        springLength: 95,
                        springConstant: 0.04
                    }}
                }}
            }};
            var network = new vis.Network(container, data, options);
        </script>
    </body>
    </html>
    """
    return html_code

# Initialize session state variables
if "holdings_df" not in st.session_state:
    st.session_state.holdings_df = load_holdings()
if "active_scenario" not in st.session_state:
    st.session_state.active_scenario = None
if "agent_logs" not in st.session_state:
    st.session_state.agent_logs = []
if "stress_results" not in st.session_state:
    st.session_state.stress_results = None
if "mc_results" not in st.session_state:
    st.session_state.mc_results = None
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
- fetch_live_quotes()
- fetch_financial_news()
- analyze_market_correlations()
- run_stress_test()
- run_monte_carlo_simulation()
- analyze_news_with_gemini()
    """, language="text")
    
    st.markdown("---")
    st.subheader("📊 Portfolio Connection")
    st.markdown("""
    * **Indian Stock Market (NSE)**: Connected Live  
    * **Global Market (US)**: Connected Live  
    * **Currency standard**: Indian Rupees (₹ / INR)  
    * **USD/INR conversion**: Dynamic Live Feed
    """)
    
    if st.button("🔄 Refresh Live Stock Prices", type="secondary"):
        st.session_state.holdings_df = load_holdings()
        st.success("Refreshed live quotes successfully!")

    st.markdown("---")
    st.markdown("⚡ *AI Research Agent Status:* **Idle**")

# ----------------- MAIN LAYOUT -----------------
st.title("🛡️ AI-Driven Stress Testing & Risk Scenario Synthesis")
st.markdown("Autonomously aggregate correlations, fetch live Indian & Global stock feeds, and visualize enterprise capital impacts in INR (₹).")

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
            <div class="metric-value" style="color: #38bdf8;">₹{total_nav/1e7:.2f} Cr</div>
            <div class="metric-label">Base Valuation (₹{total_nav/1e6:.1f}M)</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Equity Allocation</div>
            <div class="metric-value" style="color: #6366f1;">{equity_nav/total_nav*100:.1f}%</div>
            <div class="metric-label">₹{equity_nav/1e7:.2f} Cr Exposure</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Fixed Income Allocation</div>
            <div class="metric-value" style="color: #a855f7;">{bond_nav/total_nav*100:.1f}%</div>
            <div class="metric-label">₹{bond_nav/1e7:.2f} Cr Exposure</div>
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
            x='ticker',
            y='value',
            color='sector',
            title='Exposure by Stock and Sector (INR)',
            labels={'value': 'Value (INR)', 'ticker': 'Ticker'},
            color_discrete_sequence=px.colors.qualitative.Dark24
        )
        fig_class.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="#94a3b8")
        st.plotly_chart(fig_class, use_container_width=True)

    st.subheader("Live Asset Holdings Ledger")
    st.dataframe(
        st.session_state.holdings_df[["ticker", "name", "sector", "shares", "currency", "live_price", "value", "beta_market", "beta_interest", "beta_commodity"]].rename(
            columns={
                "shares": "Shares Owned",
                "currency": "Native Currency",
                "live_price": "Live Price (Native)",
                "value": "Current Value (INR)", 
                "beta_market": "Equity Beta", 
                "beta_interest": "Interest Rate Beta", 
                "beta_commodity": "Commodity Beta"
            }
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
            placeholder="Type or paste news here (e.g., 'Reserve Bank of India announces surprise interest rate hike of 150 basis points due to service sector inflation...')"
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
                if any(k in low_text for k in ["fed", "hike", "cut", "inflation", "cpi", "rate", "yield", "central bank", "powell", "monetary", "rbi"]):
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
            with st.spinner("Activating Cognitive Multi-Agent Orchestration Subnet..."):
                logs.append("⚡ [SYSTEM] Activating multi-agent risk coordination subnet...")
                logs.append("🌐 [Agent 1: Macro-Economist (Dr. Sarah Sen)] - STATUS: ACTIVE")
                logs.append(f"🌐 [Macro-Economist]: Ingesting risk news context: \"{active_news.get('headline', '')}\"")
                time.sleep(0.5)
                
                # Check if API Key is set
                gemini_active = False
                try:
                    # Call Gemini tool from server
                    news_desc = active_news.get("description") or active_news.get("headline") or ""
                    gemini_result_json = server.analyze_news_with_gemini(news_desc)
                    gemini_data = json.loads(gemini_result_json)
                    
                    if "error" not in gemini_data:
                        gemini_active = True
                        logs.append("🌐 [Macro-Economist]: Gemini reasoning node returned valid risk taxonomy.")
                        logs.append(f"🌐 [Macro-Economist]: Identified Shock Category: '{gemini_data.get('category')}' with {gemini_data.get('severity')} severity.")
                        logs.append(f"🌐 [Macro-Economist]: LLM Correlation Reasoning: '{gemini_data.get('reasoning')}'")
                        
                        # Set outputs
                        market_shock_val = float(gemini_data.get("market_shock", 0.0))
                        rate_shock_val = float(gemini_data.get("interest_rate_shock_bps", 0.0))
                        commodity_shock_val = float(gemini_data.get("commodity_shock", 0.0))
                        panic_factor_val = 0.60 if gemini_data.get("severity") == "High" else (0.30 if gemini_data.get("severity") == "Medium" else 0.10)
                        
                        vuln_sectors_list = gemini_data.get("vulnerable_sectors", [])
                        res_sectors_list = gemini_data.get("resilient_sectors", [])
                        active_category = gemini_data.get("category", "Technology")
                    else:
                        logs.append(f"⚠️ [Macro-Economist] Warning: Gemini API returned warning: {gemini_data['error']}. Falling back to correlation mapping.")
                except Exception as e:
                    logs.append(f"⚠️ [Macro-Economist] Warning: Gemini API failed: {str(e)}. Falling back to correlation mapping.")
                
                if not gemini_active:
                    active_category = active_news.get("category", "Technology")
                    logs.append(f"🌐 [Macro-Economist]: Running static risk taxonomy fallback for category: '{active_category}'.")
                    corr_json = server.analyze_market_correlations(active_category)
                    corr_data = json.loads(corr_json)
                    
                    market_shock_val = corr_data.get("market_shock", 0.0)
                    rate_shock_val = corr_data.get("interest_rate_shock_bps", 0.0)
                    commodity_shock_val = corr_data.get("commodity_shock", 0.0)
                    panic_factor_val = 0.60 if active_news.get("severity") == "High" else (0.30 if active_news.get("severity") == "Medium" else 0.10)
                    
                    vuln_sectors_list = corr_data.get("vulnerable_sectors", [])
                    res_sectors_list = corr_data.get("resilient_sectors", [])
                
                time.sleep(0.5)
                logs.append("📊 [Agent 2: Quantitative Analyst (QuantBot v4.1)] - STATUS: ACTIVE")
                logs.append("📊 [QuantBot]: Ingesting risk factors from Macro Economist Agent.")
                logs.append(f"📊 [QuantBot]: Base Shocks -> Market: {market_shock_val*100:.1f}%, Rate: {rate_shock_val:.0f} bps, Commodity: {commodity_shock_val*100:.1f}%.")
                
                # Fetch live quotes
                logs.append("📊 [QuantBot]: Querying Yahoo Finance API feeds to update portfolio NAV baseline...")
                for _, row in st.session_state.holdings_df.iterrows():
                    logs.append(f"   - {row['ticker']} Live Price: {row['live_price']} {row['currency']} | Value: ₹{row['value']/1e7:.2f} Cr")
                
                time.sleep(0.5)
                logs.append("🛡️ [Agent 3: Chief Risk Officer (Marcus Sterling)] - STATUS: ACTIVE")
                logs.append("🛡️ [CRO Marcus]: Evaluating systemic risk correlation graph nodes.")
                logs.append(f"🛡️ [CRO Marcus]: Vulnerable sectors flagged: {', '.join(vuln_sectors_list)}")
                logs.append(f"🛡️ [CRO Marcus]: Resilient sectors flagged: {', '.join(res_sectors_list)}")
                logs.append("🛡️ [CRO Marcus]: Transferring shock parameter vectors to sandbox.")
                
                # Automatically run calculations so they don't have to be executed manually
                logs.append("🛡️ [CRO Marcus]: Running automatic stress test and Monte Carlo simulation...")
                try:
                    res_json = server.run_stress_test(
                        market_shock=market_shock_val,
                        interest_rate_shock_bps=rate_shock_val,
                        commodity_shock=commodity_shock_val,
                        panic_factor=panic_factor_val,
                        custom_holdings=st.session_state.holdings_df.to_dict('records')
                    )
                    st.session_state.stress_results = json.loads(res_json)
                    
                    mc_json = server.run_monte_carlo_simulation(
                        market_shock=market_shock_val,
                        interest_rate_shock_bps=rate_shock_val,
                        commodity_shock=commodity_shock_val,
                        panic_factor=panic_factor_val,
                        custom_holdings=st.session_state.holdings_df.to_dict('records'),
                        num_simulations=1000
                    )
                    st.session_state.mc_results = json.loads(mc_json)
                    logs.append("🛡️ [CRO Marcus]: Calculations completed. Results saved to Sandbox.")
                except Exception as ex:
                    logs.append(f"⚠️ [CRO Marcus] Error running automatic stress testing: {str(ex)}")
                
                # Save outputs in session state
                st.session_state.inputs["market_shock"] = market_shock_val
                st.session_state.inputs["interest_rate_shock_bps"] = rate_shock_val
                st.session_state.inputs["commodity_shock"] = commodity_shock_val
                st.session_state.inputs["panic_factor"] = panic_factor_val
                
                st.session_state.active_scenario["category"] = active_category
                st.session_state.active_scenario["severity"] = active_news.get("severity", "Low") if not gemini_active else gemini_data.get("severity", "Low")
                
                st.session_state.active_corr_data = {
                    "vulnerable_sectors": vuln_sectors_list,
                    "resilient_sectors": res_sectors_list
                }
                
            st.session_state.agent_logs = logs
            st.success("Analysis complete! Parameter updates transferred to Sandbox.")
        else:
            st.error("No active news found. Please select a headline or paste your own custom news.")
            
    # Show Agent logs
    if st.session_state.agent_logs:
        st.markdown("### 🤖 Agent Cognitive Thought Process Log")
        log_content = "\n".join(st.session_state.agent_logs)
        st.markdown(f'<div class="agent-box">{log_content}</div>', unsafe_allow_html=True)
        
        # Vis.js Interactive Knowledge Graph Visualization
        st.markdown("### 🕸️ Interactive Semantic Risk Propagation Graph")
        st.markdown("*Drag nodes to explore correlations, use scroll wheel to zoom.*")
        
        if st.session_state.active_scenario:
            category = st.session_state.active_scenario.get("category", "Technology")
            if "active_corr_data" in st.session_state and st.session_state.active_corr_data:
                vuln_sec = st.session_state.active_corr_data.get("vulnerable_sectors", [])
                res_sec = st.session_state.active_corr_data.get("resilient_sectors", [])
            else:
                corr_json = server.analyze_market_correlations(category)
                corr_data = json.loads(corr_json)
                vuln_sec = corr_data.get("vulnerable_sectors", [])
                res_sec = corr_data.get("resilient_sectors", [])
            
            # Generate and embed the HTML Vis.js graph
            graph_html = render_interactive_graph(category, vuln_sec, res_sec, st.session_state.holdings_df)
            components.html(graph_html, height=360)

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
            step=5,
            key="sandbox_market_shock_slider"
        ) / 100.0
    with col_in2:
        r_shock = st.slider(
            "Interest Rate Shock (bps)", 
            min_value=-100, 
            max_value=400, 
            value=int(st.session_state.inputs["interest_rate_shock_bps"]),
            step=25,
            key="sandbox_rate_shock_slider"
        )
    with col_in3:
        c_shock = st.slider(
            "Commodity Shock (Oil % Change)", 
            min_value=-30, 
            max_value=100, 
            value=int(st.session_state.inputs["commodity_shock"] * 100),
            step=5,
            key="sandbox_commodity_shock_slider"
        ) / 100.0
    with col_in4:
        p_factor = st.slider(
            "Panic Factor (Liquidity Run Multiplier)", 
            min_value=0.0, 
            max_value=1.0, 
            value=float(st.session_state.inputs["panic_factor"]),
            step=0.1,
            key="sandbox_panic_factor_slider"
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
        
        # Call FastMCP tool: run_monte_carlo_simulation
        mc_json = server.run_monte_carlo_simulation(
            market_shock=m_shock,
            interest_rate_shock_bps=r_shock,
            commodity_shock=c_shock,
            panic_factor=p_factor,
            custom_holdings=st.session_state.holdings_df.to_dict('records'),
            num_simulations=1000
        )
        st.session_state.mc_results = json.loads(mc_json)
        st.success("Stress testing and Monte Carlo simulations computed successfully!")
        
    if st.session_state.stress_results:
        res = st.session_state.stress_results
        metrics = res["metrics"]
        
        # Display Stressed Metrics
        st.markdown("### Stress Test Impact Summary")
        col_res1, col_res2, col_res3, col_res4, col_res5 = st.columns(5)
        
        nav_delta = metrics["stressed_nav"] - metrics["baseline_nav"]
        nav_color = "#ef4444" if nav_delta < 0 else "#34d399"
        
        with col_res1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Stressed Portfolio NAV</div>
                <div class="metric-value" style="color: {nav_color};">₹{metrics['stressed_nav']/1e7:.2f} Cr</div>
                <div class="metric-label">Change: {metrics['nav_change_pct']}%</div>
            </div>
            """, unsafe_allow_html=True)
            
        car_color = "#ef4444" if metrics["stressed_car_pct"] < 8.0 else "#34d399"
        with col_res2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Stressed CAR (Capital Adequacy)</div>
                <div class="metric-value" style="color: {car_color};">{metrics['stressed_car_pct']:.2f}%</div>
                <div class="metric-label">Baseline: {metrics['baseline_car_pct']:.2f}%</div>
            </div>
            """, unsafe_allow_html=True)
            
        lcr_color = "#ef4444" if metrics["stressed_lcr_pct"] < 100.0 else "#34d399"
        with col_res3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Stressed LCR (Liquidity)</div>
                <div class="metric-value" style="color: {lcr_color};">{metrics['stressed_lcr_pct']:.1f}%</div>
                <div class="metric-label">Baseline: {metrics['baseline_lcr_pct']:.1f}%</div>
            </div>
            """, unsafe_allow_html=True)
            
        # 99% Value at Risk (VaR)
        with col_res4:
            var_val = st.session_state.mc_results["var_99"] if st.session_state.mc_results else 0.0
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">99% Value at Risk (VaR)</div>
                <div class="metric-value" style="color: #f43f5e;">₹{var_val/1e7:.2f} Cr</div>
                <div class="metric-label">Simulated Max Loss</div>
            </div>
            """, unsafe_allow_html=True)
            
        # Overall stress rating
        rating = "Low"
        rating_color = "#34d399"
        if metrics["nav_change_pct"] <= -10.0 or metrics["stressed_car_pct"] < 8.0 or metrics["stressed_lcr_pct"] < 100.0:
            rating = "CRITICAL LIMIT"
            rating_color = "#ef4444"
        elif metrics["nav_change_pct"] <= -5.0:
            rating = "Warning"
            rating_color = "#fbbf24"
            
        with col_res5:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Vulnerability Rating</div>
                <div class="metric-value" style="color: {rating_color}; font-size: 1.25rem; padding-top: 10px;">{rating}</div>
                <div class="metric-label">Assessment</div>
            </div>
            """, unsafe_allow_html=True)

        # Plotly comparison
        st.markdown("### Baseline vs. Stressed Asset Value Comparison (INR)")
        df_res = pd.DataFrame(res["holdings"])
        
        fig_compare = go.Figure()
        fig_compare.add_trace(go.Bar(
            name='Baseline Value (INR)',
            x=df_res['ticker'], y=df_res['baseline_value'],
            marker_color='#3b82f6'
        ))
        fig_compare.add_trace(go.Bar(
            name='Stressed Value (INR)',
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
        
        # Monte Carlo Simulation Outcome Histogram Plot
        if st.session_state.mc_results:
            st.markdown("### 📊 Monte Carlo Simulation: Portfolio NAV Distribution")
            sim_vals = [v / 1e7 for v in st.session_state.mc_results["sim_values"]] # Convert to Crores
            baseline_nav_cr = st.session_state.mc_results["baseline_nav"] / 1e7
            var_99_cr = st.session_state.mc_results["var_99"] / 1e7
            stressed_nav_cr = metrics["stressed_nav"] / 1e7
            
            df_sim = pd.DataFrame({"Simulated NAV (₹ Cr)": sim_vals})
            fig_hist = px.histogram(
                df_sim, 
                x="Simulated NAV (₹ Cr)",
                title="Portfolio NAV Outcome Distribution (1,000 Iterations)",
                color_discrete_sequence=['#1e293b']
            )
            
            # Add vertical lines
            fig_hist.add_vline(x=baseline_nav_cr, line_width=2, line_dash="solid", line_color="#3b82f6", 
                                annotation_text="Baseline NAV", annotation_position="top left")
            fig_hist.add_vline(x=stressed_nav_cr, line_width=2, line_dash="dash", line_color="#fbbf24", 
                                annotation_text="Stressed NAV", annotation_position="top right")
            fig_hist.add_vline(x=baseline_nav_cr - var_99_cr, line_width=2, line_dash="dot", line_color="#ef4444", 
                                annotation_text="99% VaR Threshold", annotation_position="bottom left")
            
            fig_hist.update_layout(
                paper_bgcolor='rgba(0,0,0,0)', 
                plot_bgcolor='rgba(0,0,0,0)', 
                font_color="#94a3b8",
                bargap=0.05
            )
            st.plotly_chart(fig_hist, use_container_width=True)

        st.subheader("Granular Asset Shock Matrix")
        st.dataframe(
            df_res[["ticker", "name", "baseline_value", "stressed_value", "change_pct"]].rename(
                columns={
                    "baseline_value": "Baseline NAV (INR)",
                    "stressed_value": "Stressed NAV (INR)",
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
        headline = st.session_state.active_scenario.get("headline", "Manual Parameters Simulation") if st.session_state.active_scenario else "Manual Parameters Simulation"
        category = st.session_state.active_scenario.get("category", "Custom Shock") if st.session_state.active_scenario else "Custom Shock"
        
        # Assess status
        car_status = "STABLE" if metrics['stressed_car_pct'] >= 8.0 else "⚠️ COMPLIANCE BREACH"
        lcr_status = "STABLE" if metrics['stressed_lcr_pct'] >= 100.0 else "⚠️ COMPLIANCE BREACH"
        
        # Get VaR
        var_val = st.session_state.mc_results["var_99"] if st.session_state.mc_results else 0.0
        
        memo_template = f"""# EXECUTIVE RISK MEMO: AI-DRIVEN SCENARIO STRESS TEST
**To:** Board of Directors & Risk Committee  
**From:** Cognitive Risk Hub Agent Subnet (Dr. Sarah Sen, QuantBot, Marcus Sterling)  
**Date:** {time.strftime("%B %d, %Y")}  
**Status:** Confidential - Internal Risk Review  

---

### 1. TRIGGER SCENARIO OVERVIEW
The multi-agent research subnet has synthesized parameters simulating:
* **Trigger Event:** {headline}
* **Shock Category:** {category}
* **Applied Shocks:** Market Shock: {m_shock*100:.1f}%, Rate Shock: {r_shock:.0f} bps, Commodity Shock: {c_shock*100:.1f}%, Panic factor: {p_factor*100:.0f}%

### 2. FINANCIAL IMPACT SUMMARY (INR)
* **Baseline Portfolio NAV:** ₹{metrics['baseline_nav']/1e7:.2f} Cr (₹{metrics['baseline_nav']/1e6:.1f}M)  
* **Stressed Portfolio NAV:** ₹{metrics['stressed_nav']/1e7:.2f} Cr (₹{metrics['stressed_nav']/1e6:.1f}M)  
* **Estimated Portfolio Capital Loss:** ₹{abs(metrics['stressed_nav'] - metrics['baseline_nav'])/1e7:.2f} Cr ({metrics['nav_change_pct']}%)  
* **99% Value at Risk (VaR):** ₹{var_val/1e7:.2f} Cr (Monte Carlo simulated maximum potential loss at 99% confidence level)

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
