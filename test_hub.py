import os
import json
import sys

def run_tests():
    print("=" * 60)
    print("COGNITIVE RISK HUB - SYSTEM INTEGRATION TEST")
    print("=" * 60)
    
    # 1. Test Import
    print("\n1. Testing Server Module Import...")
    try:
        import server
        print("   [SUCCESS] Successfully imported server.py")
    except ImportError as e:
        print(f"   [FAIL] Could not import server.py: {e}")
        return False
        
    # 2. Test get_holdings
    print("\n2. Testing get_holdings() [Live Price Feeds & Currency Conversion]...")
    try:
        holdings_json = server.get_holdings()
        holdings = json.loads(holdings_json)
        if "error" in holdings:
            print(f"   [FAIL] get_holdings returned an error: {holdings['error']}")
            return False
        print(f"   [SUCCESS] Fetched {len(holdings)} holdings from data.json + live feeds.")
        for h in holdings[:2]:
            print(f"     - Ticker: {h['ticker']} | Native Price: {h['live_price']} {h['currency']} | Value (INR): Rs. {h['value']/1e7:.4f} Cr")
    except Exception as e:
        print(f"   [FAIL] get_holdings failed: {e}")
        return False
        
    # 3. Test fetch_financial_news
    print("\n3. Testing fetch_financial_news() [RSS Feeds & Mock fallback]...")
    try:
        news_json = server.fetch_financial_news()
        news = json.loads(news_json)
        if "error" in news:
            print(f"   [FAIL] fetch_financial_news returned an error: {news['error']}")
            return False
        print(f"   [SUCCESS] Fetched {len(news)} news articles.")
        for item in news[:2]:
            print(f"     - [{item['category']}] {item['headline']} ({item['severity']} Severity)")
    except Exception as e:
        print(f"   [FAIL] fetch_financial_news failed: {e}")
        return False
        
    # 4. Test analyze_market_correlations
    print("\n4. Testing analyze_market_correlations() [Shocks Mapping]...")
    try:
        category = "Monetary Policy"
        corr_json = server.analyze_market_correlations(category)
        corr = json.loads(corr_json)
        print(f"   [SUCCESS] Retreived shocks for '{category}':")
        print(f"     - Market Shock: {corr['market_shock']*100}%")
        print(f"     - Interest Rate Shock: {corr['interest_rate_shock_bps']} bps")
        print(f"     - Vulnerable Sectors: {corr['vulnerable_sectors']}")
    except Exception as e:
        print(f"   [FAIL] analyze_market_correlations failed: {e}")
        return False
        
    # 5. Test run_stress_test
    print("\n5. Testing run_stress_test() [Beta sensitivity engine]...")
    try:
        res_json = server.run_stress_test(
            market_shock=-0.05,
            interest_rate_shock_bps=100.0,
            commodity_shock=0.10,
            panic_factor=0.2,
            custom_holdings=holdings
        )
        res = json.loads(res_json)
        if "error" in res:
            print(f"   [FAIL] run_stress_test returned an error: {res['error']}")
            return False
        metrics = res["metrics"]
        print("   [SUCCESS] Stress test calculated.")
        print(f"     - Baseline NAV: Rs. {metrics['baseline_nav']/1e7:.2f} Cr")
        print(f"     - Stressed NAV: Rs. {metrics['stressed_nav']/1e7:.2f} Cr")
        print(f"     - NAV Change: {metrics['nav_change_pct']}%")
        print(f"     - Stressed CAR: {metrics['stressed_car_pct']}%")
        print(f"     - Stressed LCR: {metrics['stressed_lcr_pct']}%")
    except Exception as e:
        print(f"   [FAIL] run_stress_test failed: {e}")
        return False
        
    # 6. Test run_monte_carlo_simulation
    print("\n6. Testing run_monte_carlo_simulation() [Quantitative VaR]...")
    try:
        mc_json = server.run_monte_carlo_simulation(
            market_shock=-0.05,
            interest_rate_shock_bps=100.0,
            commodity_shock=0.10,
            panic_factor=0.2,
            custom_holdings=holdings,
            num_simulations=100
        )
        mc = json.loads(mc_json)
        if "error" in mc:
            print(f"   [FAIL] run_monte_carlo_simulation returned an error: {mc['error']}")
            return False
        print("   [SUCCESS] Monte Carlo simulation calculated successfully.")
        print(f"     - 99% VaR (Simulated Max Loss): Rs. {mc['var_99']/1e7:.4f} Cr")
    except Exception as e:
        print(f"   [FAIL] run_monte_carlo_simulation failed: {e}")
        return False
        
    # 7. Test analyze_news_with_gemini
    print("\n7. Testing analyze_news_with_gemini() [LLM Reasoning Node]...")
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("   [WARNING] GEMINI_API_KEY not found in environment. Skipping LLM call test.")
    else:
        try:
            sample_news = "Reserve Bank of India raises repo rates by 50 basis points due to inflation concerns."
            gemini_json = server.analyze_news_with_gemini(sample_news)
            gemini_res = json.loads(gemini_json)
            if "error" in gemini_res:
                print(f"   [WARNING] Gemini API returned error: {gemini_res['error']}")
            else:
                print("   [SUCCESS] Gemini reasoning node successfully parsed parameters:")
                print(f"     - Category: {gemini_res.get('category')}")
                print(f"     - Severity: {gemini_res.get('severity')}")
                print(f"     - Reasoning: {gemini_res.get('reasoning')}")
        except Exception as e:
            print(f"   [WARNING] Gemini API call failed: {e}")

    print("\n" + "=" * 60)
    print("INTEGRATION STATUS: ALL CORE FUNCTION LINKS ARE FUNCTIONAL!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
