# AI-driven-Stress-Testing-and-Risk-Scenario-
 Cognitive Risk Hub: Final Project Report
1. Executive Summary
The Cognitive Risk Hub is a next-generation, real-time risk intelligence and portfolio stress testing platform. Modern financial markets move at extreme speeds—driven by instant digital bank runs, algorithmic trading feedback loops, and sudden geopolitical updates. Traditional risk management systems are slow, manual, and rely on periodic (e.g., quarterly) evaluations.

The Cognitive Risk Hub transforms this paradigm by combining Generative AI (for unstructured news synthesis) with Quantitative Mathematics (1,000-run Monte Carlo simulations & 99% Value at Risk) and interactive visualizations (dynamic Vis.js graph network). It automatically ingests market headlines, extracts shock values, pulls live global asset values in Indian Rupees (INR), runs stress testing models, and auto-drafts a Board-Ready Executive Memo—all in under 5 seconds.

2. Platform Architecture & Data Flow
The platform relies on a decoupled, modular design linking the data sources, reasoning agents, and quantitative simulators:

Mermaid diagram


3. Core Features Implemented
🌐 Feature 1: Live Multi-Market Valuation (in INR)
Real-time Price Feeds: Connects directly to Yahoo Finance to fetch current stock prices for Indian markets (NSE: RELIANCE.NS, TCS.NS, HDFCBANK.NS, INFY.NS, ICICIBANK.NS) and US markets (NASDAQ: AAPL, MSFT).
Live Forex Conversions: Integrates the live USD/INR exchange rate (USDINR=X) to convert foreign currency assets into Indian Rupees (INR / ₹) in real time.
Sensitivity Ledger: Maps each holding with its respective Market Equity Beta, Interest Rate Beta, and Commodity Beta.
🧠 Feature 2: Gemini AI News Synthesis & Multi-Agent Debate
Gemini Ingestion Node: Ingests copy-pasted articles or live headlines and utilizes Google Gemini 2.5 Flash to automatically detect the risk category (e.g., Geopolitical, Monetary Policy), severity level, and specific numeric shock values.
Multi-Agent Simulation: Runs a simulated debate in the UI log between:
🌐 Macro-Economist (Dr. Sarah Sen): Maps correlation logic.
📊 Quantitative Analyst (QuantBot): Updates stock prices and runs the simulation.
🛡️ Chief Risk Officer (Marcus Sterling): Confirms capital metrics and regulatory rules.
🕸️ Feature 3: Interactive Vis.js Risk Contagion Graph
Interactive Network Canvas: Bypasses heavy backend graphical rendering (like pyvis or networkx) and embeds a high-performance, zoomable, and draggable Vis.js graph in the browser.
Traceable Connections: Links the News Trigger to vulnerable/resilient sectors, which branch directly down to individual portfolio holdings.



📊 Feature 4: Automated Monte Carlo Simulation & 99% Value at Risk (VaR)
Instant Calculations: Running a news ingestion automatically runs backend stress tests and a 1,000-scenario Monte Carlo simulation using randomized normal distribution volatilities.
99% VaR: Computes the 99th percentile maximum potential loss of the portfolio.
Plotly Visualizations: Displays:
A comparison bar chart showing Baseline vs. Stressed valuations per asset.
A distribution histogram of simulated Net Asset Values (NAVs) with vertical line annotations for the baseline, stressed, and 99% VaR thresholds.
Manual Overrides: The sandbox retains manual sliders so users can test custom overrides.


📝 Feature 5: Board-Ready Executive Risk Memo
Automated Drafting: Synthesizes the stress metrics, Monte Carlo losses, and news category into a formal business memo.
Regulatory Compliance: Compares stressed metrics against Capital Adequacy Ratio (CAR) limits (8.00% minimum) and Liquidity Coverage Ratio (LCR) thresholds (100% minimum) to flag compliance breaches.
Interactive Workspace: Features an editable text area so users can modify the memo before copy-pasting or exporting.
4. Technical Stack Details
Frontend UI: Streamlit (with customized CSS style injections for dark theme and glassmorphism cards).
Backend Framework: Python (stdio transport separating business logic and interface via FastMCP).
AI Engine: Google Gemini 2.5 Flash API (via google-genai SDK).
Data Sources: Yahoo Finance Chart API.
Mathematical Operations: Random normal sampling (standard library) and DataFrame math (pandas).
Visualizations: Plotly (charts) and Vis.js (knowledge graph component).
5. System Verification & Integration Status
A dedicated integration test script 
test_hub.py
 was built and executed. The results confirm full system connectivity:

Module Import: [SUCCESS]
Live Feed & Conversion: [SUCCESS] (e.g. RELIANCE valued at 1309.50 INR, TCS at 2125.00 INR with live conversions).
News Ingestion: [SUCCESS] (RSS news pulled successfully).
Correlation Shocks: [SUCCESS] (Monetary Policy mapped to -6.0% market and 150 bps rate hikes).
Linear Stress Test: [SUCCESS] (CAR/LCR calculations completed).
Monte Carlo VaR: [SUCCESS] (1,000 runs resolved a 99% VaR of Rs. 2.3971 Cr).
Gemini API Error Handling: [SUCCESS] (Gracefully handles high-demand 503 errors and redirects to correlation tables).


6. How to Run & Deploy
A. Local Run Commands:
Navigate to the workspace directory and execute the Streamlit server:

powershell

cd "C:\Users\TLS\.gemini\antigravity\scratch\cognitive-risk-hub"
.venv\Scripts\streamlit run app.py --server.port 8505
B. Deployment Options:
Streamlit Community Cloud (Free): Link your GitHub repository, set app.py as the main entry point, and add your API keys under App Secrets:
toml

GEMINI_API_KEY = "your-api-key"
Render / Container Deployments: Set up a Web Service using python runtime, build command pip install -r requirements.txt, and start command streamlit run app.py --server.port $PORT --server.address 0.0.0.0 with environment variables.
VPS Hosting: Run with a virtual environment and place the server in the background using nohup or systemd.
