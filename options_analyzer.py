import yfinance as yf
import numpy as np
import scipy.stats as si
from datetime import datetime, date
import pandas as pd

class OptionsAnalyzer:
    def _format_symbol(self, symbol: str) -> str:
        if not symbol.endswith(".NS") and not symbol.endswith(".BO") and not symbol.startswith("^"):
            return symbol + ".NS"
        return symbol

    def calculate_greeks(self, contract_details: dict) -> dict:
        """
        Implementation of Black-Scholes from scratch
        contract_details needs: S (spot), K (strike), T (time to expiry in years), 
                                r (risk-free rate), sigma (implied volatility), option_type (call/put)
        """
        S = contract_details.get('spot', 100.0)
        K = contract_details.get('strike', 100.0)
        T = contract_details.get('time_to_expiry_years', 0.5)
        r = contract_details.get('risk_free_rate', 0.07) # Indian risk-free rate approx 7%
        sigma = contract_details.get('implied_volatility', 0.2)
        opt_type = contract_details.get('option_type', 'call').lower()

        if T <= 0 or sigma <= 0:
            return {"error": "Invalid time to expiry or implied volatility"}

        d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)

        if opt_type == 'call':
            delta = si.norm.cdf(d1, 0.0, 1.0)
            theta = (- (S * sigma * si.norm.pdf(d1, 0.0, 1.0)) / (2 * np.sqrt(T)) 
                     - r * K * np.exp(-r * T) * si.norm.cdf(d2, 0.0, 1.0))
            rho = K * T * np.exp(-r * T) * si.norm.cdf(d2, 0.0, 1.0)
        else: # put
            delta = si.norm.cdf(d1, 0.0, 1.0) - 1
            theta = (- (S * sigma * si.norm.pdf(d1, 0.0, 1.0)) / (2 * np.sqrt(T)) 
                     + r * K * np.exp(-r * T) * si.norm.cdf(-d2, 0.0, 1.0))
            rho = -K * T * np.exp(-r * T) * si.norm.cdf(-d2, 0.0, 1.0)

        gamma = si.norm.pdf(d1, 0.0, 1.0) / (S * sigma * np.sqrt(T))
        vega = S * np.sqrt(T) * si.norm.pdf(d1, 0.0, 1.0) * 0.01 # per 1% change

        # Theta is traditionally given per day (divided by 365)
        theta_per_day = theta / 365

        return {
            "delta": round(float(delta), 4),
            "gamma": round(float(gamma), 6),
            "theta": round(float(theta_per_day), 4),
            "vega": round(float(vega), 4),
            "rho": round(float(rho * 0.01), 4) # scaled to 1% change
        }

    def get_options_chain(self, symbol: str, expiry: str = None) -> dict:
        """Fetch the options chain for a given symbol."""
        formatted = self._format_symbol(symbol)
        
        try:
            ticker = yf.Ticker(formatted)
            opts = ticker.options
            if not opts:
                return {"error": f"No options chain available for {symbol}"}
                
            selected_expiry = expiry if expiry and expiry in opts else opts[0]
            chain = ticker.option_chain(selected_expiry)
            calls = chain.calls.to_dict('records')
            puts = chain.puts.to_dict('records')
            
            # Reduce payload for response
            def map_leg(leg):
                 return {
                     "contractSymbol": leg["contractSymbol"],
                     "strike": leg["strike"],
                     "lastPrice": leg["lastPrice"],
                     "volume": leg.get("volume", 0),
                     "openInterest": leg.get("openInterest", 0),
                     "impliedVolatility": leg.get("impliedVolatility", 0.0)
                 }
            
            return {
                "symbol": symbol,
                "expiry": selected_expiry,
                "available_expiries": list(opts)[:5],
                "calls": [map_leg(c) for c in calls[:50]], # limit output size
                "puts": [map_leg(p) for p in puts[:50]]
            }
            
        except Exception as e:
            return {"error": str(e)}

    def detect_unusual_activity(self, symbol: str) -> dict:
        """Scan options chain for unusual volume relative to OI"""
        formatted = self._format_symbol(symbol)
        anomalies = []
        try:
            ticker = yf.Ticker(formatted)
            opts = ticker.options
            
            if not opts:
                return {"error": "No options"}
            
            for exp in opts[:2]: # check nearest two expiries
                chain = ticker.option_chain(exp)
                for df, typ in [(chain.calls, 'Call'), (chain.puts, 'Put')]:
                    for _, row in df.iterrows():
                        vol = row.get('volume', 0)
                        oi = row.get('openInterest', 0)
                        iv = row.get('impliedVolatility', 0)
                        
                        # Simplistic unusual detection criteria:
                        # Volume > 5x OI and vol > 1000
                        if pd.notna(vol) and pd.notna(oi) and oi > 0:
                            if vol > 5 * oi and vol > 1000:
                                anomalies.append({
                                    "contract": row['contractSymbol'],
                                    "type": typ,
                                    "strike": row['strike'],
                                    "expiry": exp,
                                    "volume": vol,
                                    "openInterest": oi,
                                    "iv": round(iv, 2),
                                    "reason": "Volume spike (>5x OI)"
                                })
                                
            return {
                "symbol": symbol,
                "alerts": f"Found {len(anomalies)} anomalies",
                "anomalies": anomalies
            }
        except Exception as e:
            return {"error": f"Detection failed: {str(e)}"}
