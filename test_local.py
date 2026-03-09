from market_data import MarketDataEngine
from options_analyzer import OptionsAnalyzer
import json

def test_engine():
    engine = MarketDataEngine()
    print("Testing get_live_price for NIFTY 50 (index)...")
    res = engine.get_live_price("^NSEI")
    print(json.dumps(res, indent=2))
    
    print("\nTesting get_live_price for RELIANCE...")
    res = engine.get_live_price("RELIANCE")
    print(json.dumps(res, indent=2))

def test_options():
    analyzer = OptionsAnalyzer()
    print("\nTesting Black-Scholes Greeks calculation...")
    details = {
        "spot": 22000,
        "strike": 22000,
        "time_to_expiry_years": 0.02, # ~1 week
        "risk_free_rate": 0.07,
        "implied_volatility": 0.15,
        "option_type": "call"
    }
    greeks = analyzer.calculate_greeks(details)
    print(json.dumps(greeks, indent=2))

if __name__ == "__main__":
    try:
        test_engine()
        test_options()
    except Exception as e:
        print(f"Error: {e}")
