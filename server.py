import os
import asyncio
from mcp.server.fastmcp import FastMCP
from market_data import MarketDataEngine
from options_analyzer import OptionsAnalyzer
from trade_signals import TradeSignalGenerator
from portfolio_manager import PortfolioManager

import logging

# Configure logging to a file to capture any startup errors
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename=os.path.join(os.path.dirname(__file__), "server_debug.log")
)
logger = logging.getLogger("IndiaQuant")

# Initialize the server
mcp = FastMCP("IndiaQuant")
logger.info("Server Initialized")

# Initialize engines
market_engine = MarketDataEngine()
options_analyzer = OptionsAnalyzer()
signal_gen = TradeSignalGenerator(newsapi_key=os.getenv("NEWSAPI_KEY"))
db_path = os.path.join(os.path.dirname(__file__), "portfolio.db")
portfolio_mgr = PortfolioManager(db_path=db_path)

@mcp.tool()
async def get_live_price(symbol: str) -> dict:
    """Fetch live price for a given Indian stock symbol (e.g., RELIANCE, TCS)."""
    return market_engine.get_live_price(symbol)

@mcp.tool()
async def get_options_chain(symbol: str, expiry: str = None) -> dict:
    """Fetch the options chain for a given symbol."""
    return options_analyzer.get_options_chain(symbol, expiry)

@mcp.tool()
async def calculate_greeks(spot: float, strike: float, time_to_expiry_years: float, implied_volatility: float, option_type: str = "call", risk_free_rate: float = 0.07) -> dict:
    """Calculate Black-Scholes Greeks (Delta, Gamma, Theta, Vega, Rho) for a given option."""
    details = {
        "spot": spot,
        "strike": strike,
        "time_to_expiry_years": time_to_expiry_years,
        "risk_free_rate": risk_free_rate,
        "implied_volatility": implied_volatility,
        "option_type": option_type
    }
    return options_analyzer.calculate_greeks(details)

@mcp.tool()
async def detect_unusual_activity(symbol: str) -> dict:
    """Scan options chains for high Volume/Open Interest discrepancies."""
    return options_analyzer.detect_unusual_activity(symbol)

@mcp.tool()
async def analyze_sentiment(symbol: str) -> dict:
    """Analyze market sentiment logically based on recent news headlines."""
    return signal_gen.analyze_sentiment(symbol)

@mcp.tool()
async def generate_signal(symbol: str, timeframe: str = "1d") -> dict:
    """Generate Buy/Sell/Hold signal based on technical indicators (RSI, MACD, Bollinger Bands)."""
    return signal_gen.generate_signal(symbol, timeframe)

@mcp.tool()
async def scan_market(min_price: float = 0, max_price: float = 100000) -> dict:
    """Find stocks matching price criteria from Nifty 50."""
    return market_engine.scan_market({"min_price": min_price, "max_price": max_price})

@mcp.tool()
async def get_sector_heatmap() -> dict:
    """Returns the performance of various market sectors."""
    return market_engine.get_sector_heatmap()

@mcp.tool()
async def place_virtual_trade(symbol: str, qty: int, side: str) -> dict:
    """Place a virtual paper trade (BUY/SELL) at live market prices."""
    return portfolio_mgr.place_virtual_trade(symbol, qty, side)

@mcp.tool()
async def get_portfolio_pnl() -> dict:
    """Calculate current portfolio metrics and unrealized P&L."""
    return portfolio_mgr.get_portfolio_pnl()

if __name__ == "__main__":
    try:
        logger.info("Starting IndiaQuant Server")
        mcp.run()
    except Exception as e:
        logger.error(f"Server error: {str(e)}", exc_info=True)
        raise
