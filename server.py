from fastmcp import FastMCP
import json
import os
from dotenv import load_dotenv
from google import genai

# Load environment variables
load_dotenv()

# Initialize the Gemini Client
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
gemini_client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

# Initialize the FastMCP server
mcp = FastMCP("Cognitive Risk Hub Server")

DATA_PATH = os.path.join(os.path.dirname(__file__), "data.json")

def load_data():
    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(f"Mock data file not found at: {DATA_PATH}")
    with open(DATA_PATH, "r") as f:
        return json.load(f)

def fetch_live_quotes(tickers: list) -> dict:
    """Fetch live stock prices from Yahoo Finance Chart API."""
    import urllib.request
    import json
    
    quotes = {}
    for ticker in tickers:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=1d"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                res_data = json.loads(response.read())
                meta = res_data["chart"]["result"][0]["meta"]
                price = meta["regularMarketPrice"]
                quotes[ticker] = price
        except Exception:
            # Fallback will handle missing ticks gracefully
            pass
    return quotes

@mcp.resource("holdings://default")
def get_holdings() -> str:
    """Get the current enterprise portfolio holdings dynamically updated with live market prices in INR."""
    try:
        data = load_data()
        holdings = data["holdings"]
        
        # Extract all tickers to fetch prices
        tickers = [h["ticker"] for h in holdings]
        # Include USDINR exchange rate ticker
        usd_inr_ticker = "USDINR=X"
        tickers.append(usd_inr_ticker)
        
        live_prices = fetch_live_quotes(tickers)
        
        # Default USDINR conversion rate if network fails
        usd_inr_rate = live_prices.get(usd_inr_ticker, 83.5)
        
        # Hardcoded fallback prices in case the live fetch fails for some reason
        fallback_prices = {
            "RELIANCE.NS": 1320.0,
            "TCS.NS": 2080.0,
            "HDFCBANK.NS": 1650.0,
            "INFY.NS": 1820.0,
            "ICICIBANK.NS": 1220.0,
            "AAPL": 298.0,
            "MSFT": 380.0
        }
        
        computed_holdings = []
        for h in holdings:
            ticker = h["ticker"]
            shares = h["shares"]
            currency = h["currency"]
            
            # Get live price, fall back to default price if Yahoo Finance fetch failed
            live_price = live_prices.get(ticker, fallback_prices.get(ticker, 100.0))
            
            # Calculate value in INR
            if currency == "INR":
                value_inr = shares * live_price
            else:  # USD
                value_inr = shares * live_price * usd_inr_rate
                
            # Create holding item with computed value
            computed_holdings.append({
                "ticker": ticker,
                "name": h["name"],
                "asset_class": h["asset_class"],
                "sector": h["sector"],
                "shares": shares,
                "currency": currency,
                "live_price": round(live_price, 2),
                "value": round(value_inr, 2),
                "beta_market": h["beta_market"],
                "beta_interest": h["beta_interest"],
                "beta_commodity": h["beta_commodity"]
            })
            
        return json.dumps(computed_holdings, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})

@mcp.tool()
def fetch_financial_news(query: str = "") -> str:
    """
    Fetch live financial news from Yahoo Finance RSS feed, falling back to local mock data on network failure.
    Args:
        query: Optional string to filter headlines by category or keyword.
    """
    import urllib.request
    import xml.etree.ElementTree as ET
    
    rss_url = "https://finance.yahoo.com/rss/topstories"
    news_items = []
    
    try:
        # Attempt to fetch live RSS data
        req = urllib.request.Request(rss_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            xml_data = response.read()
            
        root = ET.fromstring(xml_data)
        count = 1
        for item in root.findall('.//item'):
            title_el = item.find('title')
            title = title_el.text if (title_el is not None and title_el.text is not None) else ""
            desc_el = item.find('description')
            desc = desc_el.text if (desc_el is not None and desc_el.text is not None) else ""
            
            # Simple keyword categorization heuristics
            low_text = (title + " " + desc).lower()
            category = "Technology"
            if any(k in low_text for k in ["fed", "hike", "cut", "inflation", "cpi", "rate", "yield", "central bank", "powell", "monetary"]):
                category = "Monetary Policy"
            elif any(k in low_text for k in ["war", "tariff", "border", "geopolitical", "sanction", "conflict", "china", "russia", "middle east"]):
                category = "Geopolitical"
            elif any(k in low_text for k in ["liquidity", "run", "deposit", "withdrawal", "reserve", "default", "bankruptcy", "banking", "svb"]):
                category = "Liquidity"
            elif any(k in low_text for k in ["cyber", "exploit", "hack", "ransomware", "breach", "outage", "security", "zero-day"]):
                category = "Cyber"
            
            # Severity mapping
            severity = "Low"
            if any(k in low_text for k in ["crash", "crisis", "collapse", "blockade", "surge", "plunge", "plummet", "escalates"]):
                severity = "High"
            elif any(k in low_text for k in ["warning", "drop", "rise", "jump", "fear", "delay"]):
                severity = "Medium"
                
            news_items.append({
                "id": f"LIVE-{count:03d}",
                "headline": title,
                "source": "Yahoo Finance (Live)",
                "category": category,
                "severity": severity,
                "description": desc
            })
            count += 1
            if count > 10: # limit to top 10 items
                break
                
    except Exception as e:
        # Silent fallback to data.json if offline or request fails
        pass
        
    # If live fetch failed or returned nothing, load fallback local mock data
    if not news_items:
        try:
            data = load_data()
            news_items = data["news"]
        except Exception as e:
            return json.dumps({"error": f"Failed to load news: {str(e)}"})
            
    # Apply query filtering if provided
    if query:
        news_items = [n for n in news_items if query.lower() in n["headline"].lower() or query.lower() in n["category"].lower()]
        
    return json.dumps(news_items, indent=2)

@mcp.tool()
def analyze_market_correlations(news_category: str) -> str:
    """
    Analyze risk correlation factors based on the active news category.
    Args:
        news_category: The category of the triggering news (e.g., Monetary Policy, Geopolitical, Liquidity, Cyber).
    """
    shocks = {
        "Monetary Policy": {
            "market_shock": -0.06,
            "interest_rate_shock_bps": 150.0,
            "commodity_shock": -0.02,
            "vulnerable_sectors": ["Fixed Income (Government)", "Technology"],
            "resilient_sectors": ["Financials", "Cash"]
        },
        "Geopolitical": {
            "market_shock": -0.08,
            "interest_rate_shock_bps": 50.0,
            "commodity_shock": 0.25,
            "vulnerable_sectors": ["Technology", "Consumer Discretionary"],
            "resilient_sectors": ["Energy", "Government (Bonds)"]
        },
        "Liquidity": {
            "market_shock": -0.12,
            "interest_rate_shock_bps": -25.0,
            "commodity_shock": -0.05,
            "vulnerable_sectors": ["Financials", "Consumer Discretionary"],
            "resilient_sectors": ["Cash", "Government (Bonds)"]
        },
        "Cyber": {
            "market_shock": -0.05,
            "interest_rate_shock_bps": 0.0,
            "commodity_shock": -0.01,
            "vulnerable_sectors": ["Technology", "Financials"],
            "resilient_sectors": ["Cash"]
        },
        "Technology": {
            "market_shock": 0.05,
            "interest_rate_shock_bps": 10.0,
            "commodity_shock": 0.0,
            "vulnerable_sectors": ["Energy"],
            "resilient_sectors": ["Technology", "Consumer Discretionary"]
        }
    }
    
    result = shocks.get(news_category, {
        "market_shock": 0.0,
        "interest_rate_shock_bps": 0.0,
        "commodity_shock": 0.0,
        "vulnerable_sectors": [],
        "resilient_sectors": []
    })
    return json.dumps(result, indent=2)

@mcp.tool()
def run_stress_test(
    market_shock: float,
    interest_rate_shock_bps: float,
    commodity_shock: float,
    panic_factor: float,
    custom_holdings: list | None = None
) -> str:
    """
    Calculate the financial impact of a stress scenario on the enterprise portfolio.
    """
    try:
        if custom_holdings is not None:
            holdings = custom_holdings
        else:
            # If not custom, load computed dynamically
            holdings = json.loads(get_holdings())
            
        rate_shock_pct = (interest_rate_shock_bps / 100.0) / 100.0
        
        scaled_market_shock = market_shock * (1.0 + panic_factor)
        scaled_rate_shock = rate_shock_pct * (1.0 + panic_factor)
        scaled_commodity_shock = commodity_shock * (1.0 + panic_factor)
        
        total_baseline_value = 0.0
        total_stressed_value = 0.0
        updated_holdings = []
        
        for h in holdings:
            val = h["value"]
            total_baseline_value += val
            
            asset_market_impact = h["beta_market"] * scaled_market_shock
            asset_rate_impact = h["beta_interest"] * scaled_rate_shock
            asset_commodity_impact = h["beta_commodity"] * scaled_commodity_shock
            
            total_asset_shock = max(-1.0, asset_market_impact + asset_rate_impact + asset_commodity_impact)
            stressed_val = val * (1.0 + total_asset_shock)
            total_stressed_value += stressed_val
            
            updated_holdings.append({
                "ticker": h["ticker"],
                "name": h["name"],
                "asset_class": h["asset_class"],
                "sector": h["sector"],
                "baseline_value": val,
                "stressed_value": stressed_val,
                "change_pct": round(total_asset_shock * 100, 2)
            })
            
        baseline_car = 0.145
        baseline_lcr = 1.35
        
        total_change_pct = (total_stressed_value - total_baseline_value) / total_baseline_value
        
        stressed_car = max(0.045, baseline_car * (1.0 + total_change_pct * 1.6))
        
        bond_baseline = sum(h["value"] for h in holdings if h["asset_class"] == "Fixed Income")
        bond_stressed = sum(u["stressed_value"] for u in updated_holdings if u["asset_class"] == "Fixed Income")
        bond_perf = bond_stressed / bond_baseline if bond_baseline > 0 else 1.0
        
        cash_perf = 1.0 - (0.45 * panic_factor)
        
        stressed_lcr = max(0.50, baseline_lcr * (bond_perf * 0.70 + cash_perf * 0.30))
        
        results = {
            "metrics": {
                "baseline_nav": total_baseline_value,
                "stressed_nav": total_stressed_value,
                "nav_change_pct": round(total_change_pct * 100, 2),
                "baseline_car_pct": round(baseline_car * 100, 2),
                "stressed_car_pct": round(stressed_car * 100, 2),
                "baseline_lcr_pct": round(baseline_lcr * 100, 2),
                "stressed_lcr_pct": round(stressed_lcr * 100, 2)
            },
            "holdings": updated_holdings
        }
        return json.dumps(results, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})

@mcp.tool()
def run_monte_carlo_simulation(
    market_shock: float,
    interest_rate_shock_bps: float,
    commodity_shock: float,
    panic_factor: float,
    custom_holdings: list,
    num_simulations: int = 1000
) -> str:
    """
    Run Monte Carlo simulations to calculate Value at Risk (VaR) at 99% confidence.
    """
    import random
    try:
        baseline_nav = sum(h["value"] for h in custom_holdings)
        sim_results = []
        
        # Volatility assumptions for randomness
        market_vol = 0.04
        rate_vol = 30.0 # bps
        commodity_vol = 0.06
        
        for _ in range(num_simulations):
            # Sample normal variables
            sim_market = random.normalvariate(market_shock, market_vol)
            sim_rate = random.normalvariate(interest_rate_shock_bps, rate_vol)
            sim_commodity = random.normalvariate(commodity_shock, commodity_vol)
            
            # Apply panic multiplier to the shock means
            sim_market_scaled = sim_market * (1.0 + panic_factor)
            sim_rate_scaled = (sim_rate / 10000.0) * (1.0 + panic_factor)
            sim_commodity_scaled = sim_commodity * (1.0 + panic_factor)
            
            sim_nav = 0.0
            for h in custom_holdings:
                val = h["value"]
                # Combined sensitivity return
                ret = (h.get("beta_market", 1.0) * sim_market_scaled + 
                       h.get("beta_interest", 0.0) * sim_rate_scaled + 
                       h.get("beta_commodity", 0.0) * sim_commodity_scaled)
                # Cap loss at 100%
                ret = max(-1.0, ret)
                sim_nav += val * (1.0 + ret)
            
            sim_results.append(sim_nav)
            
        # Calculate losses
        losses = [baseline_nav - nav for nav in sim_results]
        losses.sort()
        
        # 99% VaR index
        var_index = int(num_simulations * 0.99) - 1
        var_99 = losses[var_index]
        
        return json.dumps({
            "var_99": round(var_99, 2),
            "sim_values": [round(v, 2) for v in sim_results],
            "baseline_nav": baseline_nav
        })
    except Exception as e:
        return json.dumps({"error": str(e)})

@mcp.tool()
def analyze_news_with_gemini(news_text: str) -> str:
    """
    Use Google Gemini model to analyze news and generate risk shock parameters.
    Args:
        news_text: The financial news headline or article text to analyze.
    """
    if not gemini_client:
        return json.dumps({"error": "Gemini API Key is not set in environment variables."})
        
    prompt = f"""
    You are a Quantitative Risk Analyst. Analyze the following financial news and return a JSON object with:
    1. "category": Choose exactly one from ["Monetary Policy", "Geopolitical", "Liquidity", "Cyber", "Technology"].
    2. "severity": Choose exactly one from ["Low", "Medium", "High"].
    3. "market_shock": Estimated market decline (as a float, e.g. -0.10 for -10%. Put positive/0.0 if positive impact).
    4. "interest_rate_shock_bps": Interest rate hike in basis points (as a float, e.g. 150.0).
    5. "commodity_shock": Commodity/oil price change (as a float, e.g. 0.20 for +20%).
    6. "vulnerable_sectors": List of 2 sectors in the portfolio that will suffer the most (from: Technology, Financials, Energy, Government, Consumer Discretionary).
    7. "resilient_sectors": List of 2 sectors that will benefit or remain stable.
    8. "reasoning": A 2-sentence explanation of the correlation.

    News: "{news_text}"

    Return ONLY the raw JSON object, no markdown formatting, no backticks.
    """
    try:
        response = gemini_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        
        # Clean response text safely checking if response or response.text is None
        if not response or not response.text:
            return json.dumps({"error": "Gemini API returned an empty response. Please verify that your API key is active and has sufficient quota."})
            
        clean_json = response.text.replace("```json", "").replace("```", "").strip()
        return clean_json
    except Exception as e:
        return json.dumps({"error": str(e)})

if __name__ == "__main__":
    mcp.run()
