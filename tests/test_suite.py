import unittest
from unittest.mock import MagicMock, patch
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(__file__))

from market_data import MarketDataEngine
from options_analyzer import OptionsAnalyzer

class TestIndiaQuant(unittest.TestCase):
    def setUp(self):
        self.market = MarketDataEngine()
        self.options = OptionsAnalyzer()

    def test_symbol_formatting(self):
        """Test that symbols are correctly formatted for Yahoo Finance"""
        self.assertEqual(self.market.format_symbol("RELIANCE"), "RELIANCE.NS")
        self.assertEqual(self.market.format_symbol("TCS.NS"), "TCS.NS")
        self.assertEqual(self.market.format_symbol("^NSEI"), "^NSEI")

    def test_black_scholes_greeks(self):
        """Test mathematical accuracy of Greeks calculation"""
        details = {
            "spot": 22000,
            "strike": 22000,
            "time_to_expiry_years": 0.02,
            "risk_free_rate": 0.07,
            "implied_volatility": 0.15,
            "option_type": "call"
        }
        greeks = self.options.calculate_greeks(details)
        
        self.assertIn("delta", greeks)
        self.assertGreater(greeks["delta"], 0.4) # Call delta at the money should be near 0.5
        self.assertLess(greeks["delta"], 0.6)
        self.assertIn("gamma", greeks)
        self.assertIn("theta", greeks)

    @patch('yfinance.Ticker')
    def test_market_data_fetch(self, mock_ticker):
        """Mock test for live price fetching logic"""
        # Setup mock data
        mock_hist = MagicMock()
        mock_hist.empty = False
        mock_hist.iloc = [MagicMock()]
        mock_hist.iloc[-1] = {'Close': 100.0, 'Volume': 1000}
        mock_ticker.return_value.history.return_value = mock_hist
        
        price_data = self.market.get_live_price("TEST")
        self.assertEqual(price_data["price"], 100.0)
        self.assertEqual(price_data["symbol"], "TEST")

if __name__ == '__main__':
    unittest.main()
