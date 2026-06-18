from fastmcp import FastMCP
import json
import os

# Initialize the FastMCP server
mcp = FastMCP("Cognitive Risk Hub Server")

DATA_PATH = os.path.join(os.path.dirname(__file__), "data.json")

def load_data():
    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(f"Mock data file not found at: {DATA_PATH}")
    with open(DATA_PATH, "r") as f:
        return json.load(f)

@mcp.resource("holdings://default")
def get_holdings() -> str:
    """Get the current enterprise portfolio holdings."""
    try:
        data = load_data()
        return json.dumps(data["holdings"], indent=2)
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
            data = load_data()
            holdings = data["holdings"]
        # Convert interest rate shock to a decimal rate percentage (e.g., 150 bps -> 0.015)
        rate_shock_pct = (interest_rate_shock_bps / 100.0) / 100.0
        
        # Scale inputs by panic factor multiplier
        scaled_market_shock = market_shock * (1.0 + panic_factor)
        scaled_rate_shock = rate_shock_pct * (1.0 + panic_factor)
        scaled_commodity_shock = commodity_shock * (1.0 + panic_factor)
        
        total_baseline_value = 0.0
        total_stressed_value = 0.0
        updated_holdings = []
        
        for h in holdings:
            val = h["value"]
            total_baseline_value += val
            
            # Combine weighted factor sensitivities
            asset_market_impact = h["beta_market"] * scaled_market_shock
            asset_rate_impact = h["beta_interest"] * scaled_rate_shock
            asset_commodity_impact = h["beta_commodity"] * scaled_commodity_shock
            
            # Total shock multiplier (capped at -100% loss)
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
            
        # Calculate structural ratios
        # Base Tier 1 Capital Adequacy Ratio (CAR) baseline is 14.5%
        # Base Liquidity Coverage Ratio (LCR) baseline is 135%
        baseline_car = 0.145
        baseline_lcr = 1.35
        
        total_change_pct = (total_stressed_value - total_baseline_value) / total_baseline_value
        
        # Post-stress CAR is heavily degraded by equity declines which impair Tier 1 Capital buffers
        stressed_car = max(0.045, baseline_car * (1.0 + total_change_pct * 1.6))
        
        # Post-stress LCR is degraded by interest rate shocks hitting Fixed Income (bond devaluation)
        # and deposit outflows (panic factor draining cash)
        bond_baseline = sum(h["value"] for h in holdings if h["asset_class"] == "Fixed Income")
        bond_stressed = sum(u["stressed_value"] for u in updated_holdings if u["asset_class"] == "Fixed Income")
        bond_perf = bond_stressed / bond_baseline if bond_baseline > 0 else 1.0
        
        cash_perf = 1.0 - (0.45 * panic_factor) # Depositors pulling cash out of the bank
        
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

if __name__ == "__main__":
    mcp.run()
