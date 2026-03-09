import yfinance as yf
import pandas as pd
import math

class MarketDataEngine:
    def __init__(self):
        # We can map some Indian sectors to index symbols
        self.sectors = {
            "NIFTY 50": "^NSEI",
            "NIFTY BANK": "^NSEBANK",
            "NIFTY IT": "^CNXIT",
            "NIFTY AUTO": "^CNXAUTO",
            "NIFTY FMCG": "^CNXFMCG",
            "NIFTY PHARMA": "^CNXPHARMA",
            "NIFTY METAL": "^CNXMETAL",
        }

    def format_symbol(self, symbol: str) -> str:
        """Format symbol for Yahoo Finance (NSE format)"""
        if not symbol.endswith(".NS") and not symbol.endswith(".BO") and not symbol.startswith("^"):
            return symbol + ".NS"
        return symbol

    def get_live_price(self, symbol: str) -> dict:
        """Fetch live price for a given symbol."""
        formatted_symbol = self.format_symbol(symbol)
        try:
            ticker = yf.Ticker(formatted_symbol)
            todays_data = ticker.history(period='1d')
            
            if todays_data.empty:
                # Sometime yfinance fails on 1d for Indian stocks after market close, try 5d
                todays_data = ticker.history(period='5d')
                if todays_data.empty:
                    return {"error": f"No data found for {symbol}"}
            
            # Get latest row
            latest = todays_data.iloc[-1]
            # Try to get previous close for change percentage
            if len(todays_data) > 1:
                prev_close = todays_data.iloc[-2]['Close']
            else:
                info = ticker.info
                prev_close = info.get('previousClose', latest['Close'])
            
            change_pct = ((latest['Close'] - prev_close) / prev_close) * 100 if prev_close else 0

            return {
                "symbol": symbol,
                "price": round(float(latest['Close']), 2),
                "change_percent": round(float(change_pct), 2),
                "volume": int(latest['Volume'])
            }
        except Exception as e:
            return {"error": str(e)}

    def scan_market(self, filter_criteria: dict) -> dict:
        """
        Scan market. This is a heavy operation to do live across all stocks without a proper screener API.
        We'll scan Nifty 50 stocks as a proxy for 'the market'.
        """
        # Nifty 50 list sample
        nifty50_symbols = [
            "RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "INFY", "ITC", "SBIN",
            "BHARTIARTL", "BAJFINANCE", "HINDUNILVR", "LT", "ASIANPAINT",
            "HCLTECH", "AXISBANK", "MARUTI", "SUNPHARMA", "TITAN", "ULTRACEMCO"
        ] # Truncated for speed

        results = []
        for sym in nifty50_symbols:
            formatted = self.format_symbol(sym)
            try:
                ticker = yf.Ticker(formatted)
                hist = ticker.history(period="10d") # need some history for RSI
                if hist.empty:
                    continue
                
                # Assume simple filter criteria for now like "oversold" (RSI < 30) or price > X
                close = float(hist.iloc[-1]['Close'])
                
                # Add basic matching
                match = True
                if "min_price" in filter_criteria and close < filter_criteria["min_price"]: match = False
                if "max_price" in filter_criteria and close > filter_criteria["max_price"]: match = False
                
                # Could expand to calculate RSI manually or with pandas_ta here if criteria includes technicals
                
                if match:
                    results.append({"symbol": sym, "price": close})
            except Exception:
                continue
                
        return {"criteria": filter_criteria, "matches": results}

    def get_sector_heatmap(self) -> dict:
        """Returns sector performance."""
        heatmap = {}
        for sector_name, symbol in self.sectors.items():
            res = self.get_live_price(symbol)
            if "error" not in res:
                heatmap[sector_name] = res["change_percent"]
            else:
                heatmap[sector_name] = "N/A"
                
        return {"sectors": heatmap}
