import pandas as pd
import pandas_ta as ta
import yfinance as yf
import requests

class TradeSignalGenerator:
    def __init__(self, newsapi_key=None):
        self.newsapi_key = newsapi_key or "demo_key" # Should use environment variable

    def analyze_sentiment(self, symbol: str) -> dict:
        """Analyze sentiment logically based on headlines via NewsAPI"""
        # Since we might not have a real NewsAPI key, we still need to mimic the logic correctly.
        query = symbol
        url = f"https://newsapi.org/v2/everything?q={query}&language=en&sortBy=publishedAt&apiKey={self.newsapi_key}"
        
        try:
            # Using a real query, if fail, return neutral.
            response = requests.get(url, timeout=5)
            data = response.json()
            
            if data.get("status") == "ok":
                articles = data.get("articles", [])[:5]
                headlines = [a.get("title") for a in articles]
                
                # Basic sentiment scoring since we can't use complex paid NLP APIs.
                positive_words = ["surge", "jump", "grow", "buy", "up", "bull", "profit", "win", "beat"]
                negative_words = ["drop", "fall", "sell", "down", "bear", "loss", "miss", "crash"]
                
                score = 0
                for headline in headlines:
                    lower = headline.lower()
                    if any(w in lower for w in positive_words): score += 1
                    if any(w in lower for w in negative_words): score -= 1
                    
                if score > 0:
                    signal = "BULLISH"
                elif score < 0:
                    signal = "BEARISH"
                else:
                    signal = "NEUTRAL"
                    
                return {
                    "symbol": symbol,
                    "score": score,
                    "headlines": headlines,
                    "signal": signal
                }
            else:
                return {
                    "symbol": symbol,
                    "score": 0,
                    "headlines": ["Error fetching or API limit reached"],
                    "signal": "NEUTRAL"
                }

        except Exception as e:
            return {"error": str(e), "signal": "NEUTRAL"}

    def generate_signal(self, symbol: str, timeframe: str = "1d") -> dict:
        """Combine technicals to generate BUY/SELL/HOLD and confidence"""
        formatted_symbol = symbol + ".NS" if not symbol.endswith(".NS") else symbol
        try:
            # Download basic history for TA
            # E.g., fetch 60 days to compute 50 SMA / MACD / RSI reliably
            ticker = yf.Ticker(formatted_symbol)
            df = ticker.history(period="6mo" if timeframe=="1d" else "7d", interval="1d" if timeframe=="1d" else "1h")
            if df.empty:
                return {"error": f"No data for {symbol}"}
                
            # Compute RSI
            df.ta.rsi(length=14, append=True)
            # Compute MACD
            df.ta.macd(fast=12, slow=26, signal=9, append=True)
            # Compute Bollinger Bands
            df.ta.bbands(length=20, std=2, append=True)
            
            # Extract latest
            latest = df.iloc[-1]
            prev = df.iloc[-2]
            
            rsi = latest.get('RSI_14', 50)
            macd = latest.get('MACD_12_26_9', 0)
            macd_signal = latest.get('MACDs_12_26_9', 0)
            close = latest['Close']
            
            # Signals
            buy_score = 0
            sell_score = 0
            
            # RSI Rules
            if rsi < 30: buy_score += 30
            elif rsi > 70: sell_score += 30
            
            # MACD Rules crossover
            if macd > macd_signal and prev.get('MACD_12_26_9',0) <= prev.get('MACDs_12_26_9',0): buy_score += 40
            if macd < macd_signal and prev.get('MACD_12_26_9',0) >= prev.get('MACDs_12_26_9',0): sell_score += 40
            
            # Pattern context (simplified)
            # Compare close to bollinger bands
            bbl = latest.get('BBL_20_2.0', 0)
            bbu = latest.get('BBU_20_2.0', float('inf'))
            if close <= bbl: buy_score += 30
            if close >= bbu: sell_score += 30
            
            # Final scoring
            confidence = max(buy_score, sell_score)
            if buy_score > sell_score and buy_score >= 50:
                signal = "BUY"
            elif sell_score > buy_score and sell_score >= 50:
                signal = "SELL"
            else:
                signal = "HOLD"
                confidence = 100 - abs(buy_score - sell_score) # Confident it's a hold
                
            return {
                "symbol": symbol,
                "timeframe": timeframe,
                "signal": signal,
                "confidence": min(100, confidence),
                "metrics": {
                    "rsi": round(rsi, 2) if pd.notna(rsi) else None,
                    "macd": round(macd, 2) if pd.notna(macd) else None,
                    "close": round(close, 2)
                }
            }
        except Exception as e:
            return {"error": str(e)}

