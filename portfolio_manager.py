import sqlite3
import yfinance as yf
from datetime import datetime

class PortfolioManager:
    def __init__(self, db_path="portfolio.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Virtual balances table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS balances (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    balance REAL NOT NULL
                )
            ''')
            # Initialize with 10 Lakh INR (1,000,000)
            cursor.execute('SELECT COUNT(*) FROM balances')
            if cursor.fetchone()[0] == 0:
                cursor.execute('INSERT INTO balances (balance) VALUES (1000000.0)')
            
            # Virtual positions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS positions (
                    symbol TEXT PRIMARY KEY,
                    quantity INTEGER,
                    average_price REAL
                )
            ''')
            # Transactions log table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT,
                    quantity INTEGER,
                    price REAL,
                    side TEXT,
                    timestamp TEXT
                )
            ''')
            conn.commit()

    def _format_symbol(self, symbol: str) -> str:
        if not symbol.endswith(".NS") and not symbol.endswith(".BO") and not symbol.startswith("^"):
            return symbol + ".NS"
        return symbol

    def _get_live_price(self, symbol: str) -> float:
        """Fetch live price silently."""
        formatted_symbol = self._format_symbol(symbol)
        try:
            ticker = yf.Ticker(formatted_symbol)
            todays_data = ticker.history(period='1d')
            if todays_data.empty:
                todays_data = ticker.history(period='5d')
                if todays_data.empty:
                    return 0.0
            return float(todays_data.iloc[-1]['Close'])
        except Exception:
            return 0.0

    def get_portfolio_pnl(self) -> dict:
        """Calculate total unrealized P&L and metrics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT balance FROM balances WHERE id = 1')
                balance = cursor.fetchone()[0]
                
                cursor.execute('SELECT symbol, quantity, average_price FROM positions WHERE quantity > 0')
                positions = cursor.fetchall()
            
            total_invested = 0.0
            current_value = 0.0
            pos_data = []

            for sym, qty, avg_price in positions:
                live_price = self._get_live_price(sym)
                if live_price == 0: # Assume no change if we can't fetch it
                    live_price = avg_price
                    
                invested = qty * avg_price
                value = qty * live_price
                unrealized_pnl = value - invested
                pnl_pct = (unrealized_pnl / invested) * 100 if invested > 0 else 0
                
                total_invested += invested
                current_value += value
                
                pos_data.append({
                    "symbol": sym,
                    "quantity": qty,
                    "avg_price": round(avg_price, 2),
                    "ltp": round(live_price, 2),
                    "unrealized_pnl": round(unrealized_pnl, 2),
                    "pnl_percent": round(pnl_pct, 2)
                })

            total_unrealized_pnl = current_value - total_invested
            net_liquidation_value = balance + current_value
            
            return {
                "summary": {
                    "cash_balance": round(balance, 2),
                    "total_invested": round(total_invested, 2),
                    "current_value": round(current_value, 2),
                    "net_liquidation_value": round(net_liquidation_value, 2),
                    "total_unrealized_pnl": round(total_unrealized_pnl, 2)
                },
                "positions": pos_data
            }
        except Exception as e:
            return {"error": str(e)}

    def place_virtual_trade(self, symbol: str, qty: int, side: str) -> dict:
        """Place a basic virtual market order."""
        side = side.upper()
        if side not in ["BUY", "SELL"]: return {"error": "Side must be BUY or SELL"}
        if qty <= 0: return {"error": "Quantity must be > 0"}
        
        live_price = self._get_live_price(symbol)
        if live_price == 0.0:
            return {"error": f"Failed to get live price for {symbol}"}
        
        trade_value = live_price * qty
        timestamp = datetime.utcnow().isoformat()
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('SELECT balance FROM balances WHERE id = 1')
                balance = cursor.fetchone()[0]
                
                cursor.execute('SELECT quantity, average_price FROM positions WHERE symbol = ?', (symbol,))
                pos = cursor.fetchone()
                current_qty = pos[0] if pos else 0
                current_avg = pos[1] if pos else 0.0
                
                if side == "BUY":
                    if balance < trade_value:
                        return {"error": f"Insufficient funds. Required: {trade_value}, Available: {balance}"}
                    
                    new_balance = balance - trade_value
                    new_qty = current_qty + qty
                    new_avg = ((current_qty * current_avg) + trade_value) / new_qty
                    
                    cursor.execute('UPDATE balances SET balance = ? WHERE id = 1', (new_balance,))
                    cursor.execute('''INSERT INTO positions (symbol, quantity, average_price) 
                                      VALUES (?, ?, ?) 
                                      ON CONFLICT(symbol) DO UPDATE SET quantity = ?, average_price = ?''',
                                      (symbol, new_qty, new_avg, new_qty, new_avg))
                                      
                elif side == "SELL":
                    if current_qty < qty:
                        return {"error": f"Insufficient shares of {symbol}. Available: {current_qty}, Request: {qty}"}
                        
                    new_balance = balance + trade_value
                    new_qty = current_qty - qty
                    
                    cursor.execute('UPDATE balances SET balance = ? WHERE id = 1', (new_balance,))
                    if new_qty == 0:
                        cursor.execute('DELETE FROM positions WHERE symbol = ?', (symbol,))
                    else:
                        # Average price remains the same on partial sell
                        cursor.execute('UPDATE positions SET quantity = ? WHERE symbol = ?', (new_qty, symbol))
                
                cursor.execute('''INSERT INTO transactions (symbol, quantity, price, side, timestamp)
                                  VALUES (?, ?, ?, ?, ?)''', (symbol, qty, live_price, side, timestamp))
                                  
                conn.commit()
                
                return {
                    "order_id": cursor.lastrowid,
                    "symbol": symbol,
                    "quantity": qty,
                    "fill_price": round(live_price, 2),
                    "side": side,
                    "status": "FILLED",
                    "timestamp": timestamp
                }
        except Exception as e:
            return {"error": str(e)}

