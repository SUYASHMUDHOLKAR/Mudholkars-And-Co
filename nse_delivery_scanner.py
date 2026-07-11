"""
nse_delivery_scanner.py
-----------------------
Scans NSE for:
  1. DELIVERY % — high delivery = genuine buying (not just intraday traders)
     > 60% delivery = STRONG conviction buying
     > 80% delivery = Institutions accumulating
  2. BULK DEALS — when someone buys ₹50Cr+ in one shot
  3. BLOCK DEALS — large negotiated trades (institutional)

All FREE from NSE/BSE public data.
"""

import logging
import requests
import csv
import io
from datetime import datetime, date
from typing import Optional

logger = logging.getLogger(__name__)

NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Referer": "https://www.nseindia.com/",
}


class DeliveryScanner:
    """
    Scans NSE bhavcopy for delivery % data.
    High delivery = real buying (institutions, long-term investors).
    Low delivery = just intraday traders (no conviction).
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(NSE_HEADERS)
        try:
            self.session.get("https://www.nseindia.com", timeout=10)
        except:
            pass

    def get_high_delivery_stocks(self, min_delivery_pct: float = 60.0) -> list:
        """
        Get stocks with delivery % above threshold.
        Higher delivery = more genuine buying.
        
        Returns list of: {symbol, delivery_pct, volume, traded_value}
        """
        logger.info(f"Scanning for delivery % > {min_delivery_pct}%...")
        try:
            # NSE Security-wise Delivery Position
            url = "https://www.nseindia.com/api/equity-stockIndices?index=SECURITIES%20IN%20F%26O"
            resp = self.session.get(url, timeout=15)
            
            if resp.status_code != 200:
                # Fallback: try bhavcopy
                return self._get_from_bhavcopy(min_delivery_pct)

            data = resp.json()
            stocks = data.get("data", [])
            
            high_delivery = []
            for stock in stocks:
                try:
                    symbol = stock.get("symbol", "")
                    delivery_qty = float(stock.get("totalTradedVolume", 0) or 0)
                    total_qty = float(stock.get("totalTradedValue", 0) or 0)
                    
                    # Some APIs give direct delivery %
                    del_pct = float(stock.get("deliveryToTradedQuantity", 0) or 0)
                    
                    if del_pct >= min_delivery_pct:
                        high_delivery.append({
                            "symbol": symbol,
                            "delivery_pct": round(del_pct, 2),
                            "price": float(stock.get("lastPrice", 0) or 0),
                            "change_pct": float(stock.get("pChange", 0) or 0),
                            "signal": "STRONG_ACCUMULATION" if del_pct >= 80 else "ACCUMULATION",
                        })
                except:
                    continue

            high_delivery.sort(key=lambda x: x["delivery_pct"], reverse=True)
            logger.info(f"  Found {len(high_delivery)} stocks with delivery > {min_delivery_pct}%")
            return high_delivery

        except Exception as e:
            logger.warning(f"Delivery scan error: {e}")
            return self._get_from_bhavcopy(min_delivery_pct)

    def _get_from_bhavcopy(self, min_delivery_pct: float) -> list:
        """Fallback: get delivery data from NSE bhavcopy CSV."""
        try:
            today = date.today()
            # NSE bhavcopy format: DDMMYYYY
            date_str = today.strftime("%d%m%Y")
            url = f"https://archives.nseindia.com/products/content/sec_bhavdata_full_{date_str}.csv"
            
            resp = self.session.get(url, timeout=15)
            if resp.status_code != 200:
                # Try yesterday
                from datetime import timedelta
                yesterday = today - timedelta(days=1)
                date_str = yesterday.strftime("%d%m%Y")
                url = f"https://archives.nseindia.com/products/content/sec_bhavdata_full_{date_str}.csv"
                resp = self.session.get(url, timeout=15)
            
            if resp.status_code != 200:
                return []

            reader = csv.DictReader(io.StringIO(resp.text))
            results = []
            for row in reader:
                try:
                    symbol = row.get("SYMBOL", "").strip()
                    del_qty = float(row.get("DELIV_QTY", 0) or 0)
                    total_qty = float(row.get("TTL_TRD_QNTY", 0) or 0)
                    
                    if total_qty > 0:
                        del_pct = (del_qty / total_qty) * 100
                        if del_pct >= min_delivery_pct:
                            results.append({
                                "symbol": symbol,
                                "delivery_pct": round(del_pct, 2),
                                "delivery_qty": int(del_qty),
                                "total_qty": int(total_qty),
                                "close": float(row.get("CLOSE_PRICE", 0) or 0),
                                "signal": "STRONG_ACCUMULATION" if del_pct >= 80 else "ACCUMULATION",
                            })
                except:
                    continue

            results.sort(key=lambda x: x["delivery_pct"], reverse=True)
            logger.info(f"  Bhavcopy: {len(results)} stocks with high delivery")
            return results[:50]
        except Exception as e:
            logger.warning(f"Bhavcopy error: {e}")
            return []


class BulkBlockDealTracker:
    """
    Tracks Bulk and Block deals from BSE/NSE.
    Bulk deal = >0.5% of equity traded in one order.
    Block deal = ₹10 Cr+ negotiated off-market.
    Both = BIG MONEY entering/exiting a stock.
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(NSE_HEADERS)
        try:
            self.session.get("https://www.nseindia.com", timeout=10)
        except:
            pass

    def get_bulk_deals(self) -> list:
        """Get today's bulk deals from NSE."""
        try:
            url = "https://www.nseindia.com/api/snapshot-capital-market-bulk-deals"
            resp = self.session.get(url, timeout=15)
            
            if resp.status_code != 200:
                return self._get_bulk_fallback()

            data = resp.json()
            deals = []
            for item in data.get("data", []):
                deal_type = item.get("clientBuySell", "").upper()
                qty = float(item.get("quantity", 0) or 0)
                price = float(item.get("avgPrice", 0) or 0)
                value_cr = (qty * price) / 10000000  # Convert to crore

                deals.append({
                    "symbol": item.get("symbol", ""),
                    "client": item.get("clientName", "")[:40],
                    "type": "BUY" if "BUY" in deal_type else "SELL",
                    "quantity": int(qty),
                    "price": round(price, 2),
                    "value_cr": round(value_cr, 2),
                    "signal": "INSTITUTIONAL_BUYING" if "BUY" in deal_type else "INSTITUTIONAL_SELLING",
                })

            # Sort by value
            deals.sort(key=lambda x: x["value_cr"], reverse=True)
            logger.info(f"  Bulk deals found: {len(deals)}")
            return deals[:20]

        except Exception as e:
            logger.warning(f"Bulk deals error: {e}")
            return self._get_bulk_fallback()

    def _get_bulk_fallback(self) -> list:
        """Fallback for bulk deals."""
        try:
            url = "https://www.nseindia.com/api/snapshot-capital-market-block-deals"
            resp = self.session.get(url, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                deals = []
                for item in data.get("data", []):
                    deals.append({
                        "symbol": item.get("symbol", ""),
                        "type": "BLOCK_DEAL",
                        "quantity": int(item.get("quantity", 0) or 0),
                        "price": float(item.get("avgPrice", 0) or 0),
                    })
                return deals[:10]
        except:
            pass
        return []

    def get_insider_trades(self) -> list:
        """
        Get recent insider/promoter trading from NSE SAST data.
        When promoters BUY their own stock = STRONGEST bullish signal.
        When promoters SELL = danger.
        """
        try:
            url = "https://www.nseindia.com/api/corporates-pit"
            resp = self.session.get(url, timeout=15)
            
            if resp.status_code != 200:
                # Try BSE
                return self._get_insider_bse()

            data = resp.json()
            trades = []
            for item in data.get("data", [])[:30]:
                acq_type = item.get("acqMode", "").upper()
                category = item.get("personCategory", "")
                
                is_buy = "MARKET PURCHASE" in acq_type or "BUY" in acq_type
                is_promoter = "PROMOTER" in category.upper()
                
                trades.append({
                    "symbol": item.get("symbol", ""),
                    "person": item.get("acqName", "")[:30],
                    "category": category,
                    "type": "BUY" if is_buy else "SELL",
                    "shares": int(item.get("secAcq", 0) or 0),
                    "value_cr": round(float(item.get("secVal", 0) or 0) / 10000000, 2),
                    "is_promoter": is_promoter,
                    "signal": "PROMOTER_BUYING" if (is_buy and is_promoter) else (
                        "PROMOTER_SELLING" if (not is_buy and is_promoter) else (
                            "INSIDER_BUYING" if is_buy else "INSIDER_SELLING")),
                    "date": item.get("date", ""),
                })

            # Prioritize promoter trades
            trades.sort(key=lambda x: (x["is_promoter"], x["value_cr"]), reverse=True)
            logger.info(f"  Insider trades found: {len(trades)}")
            return trades[:20]

        except Exception as e:
            logger.warning(f"Insider trades error: {e}")
            return []

    def _get_insider_bse(self) -> list:
        """Fallback: try BSE for insider data."""
        try:
            url = "https://api.bseindia.com/BseIndiaAPI/api/AnnSubCategoryGetData/w?pageno=1&strCat=Insider%20Trading&strPrevDate=&strScrip=&strSearch=P&strToDate=&strType=C"
            resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code == 200:
                data = resp.json()
                trades = []
                for item in data.get("Table", [])[:10]:
                    trades.append({
                        "symbol": item.get("SLONGNAME", "")[:15],
                        "type": "INSIDER_TRADE",
                        "date": item.get("NEWS_DT", ""),
                    })
                return trades
        except:
            pass
        return []


class InsiderDealAgent:
    """
    Combined agent: Delivery + Bulk Deals + Insider Trading.
    Gives ONE combined signal per stock.
    """

    def __init__(self):
        self.delivery = DeliveryScanner()
        self.deals = BulkBlockDealTracker()

    def scan_all(self) -> dict:
        """Run complete scan for institutional activity."""
        logger.info("🏦 INSIDER DEAL AGENT — Scanning...")

        high_delivery = self.delivery.get_high_delivery_stocks(60)
        bulk_deals = self.deals.get_bulk_deals()
        insider_trades = self.deals.get_insider_trades()

        # Find stocks appearing in multiple signals
        hot_stocks = {}
        
        for d in high_delivery[:20]:
            sym = d["symbol"]
            hot_stocks.setdefault(sym, {"signals": [], "score": 0})
            hot_stocks[sym]["signals"].append(f"Delivery {d['delivery_pct']}%")
            hot_stocks[sym]["score"] += 20 if d["delivery_pct"] >= 80 else 10

        for b in bulk_deals:
            sym = b["symbol"]
            if b["type"] == "BUY":
                hot_stocks.setdefault(sym, {"signals": [], "score": 0})
                hot_stocks[sym]["signals"].append(f"Bulk BUY ₹{b['value_cr']}Cr")
                hot_stocks[sym]["score"] += 25

        for t in insider_trades:
            sym = t["symbol"]
            if t["signal"] == "PROMOTER_BUYING":
                hot_stocks.setdefault(sym, {"signals": [], "score": 0})
                hot_stocks[sym]["signals"].append(f"Promoter BUYING ₹{t['value_cr']}Cr")
                hot_stocks[sym]["score"] += 30  # Strongest signal

        # Sort by combined score
        ranked = sorted(hot_stocks.items(), key=lambda x: x[1]["score"], reverse=True)

        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "high_delivery_stocks": high_delivery[:15],
            "bulk_deals": bulk_deals[:10],
            "insider_trades": insider_trades[:10],
            "hot_stocks": [{
                "symbol": sym, 
                "score": data["score"],
                "signals": data["signals"],
            } for sym, data in ranked[:10]],
            "total_scanned": {
                "delivery": len(high_delivery),
                "bulk_deals": len(bulk_deals),
                "insider_trades": len(insider_trades),
            },
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
    agent = InsiderDealAgent()
    result = agent.scan_all()
    
    print("\n🏦 INSIDER DEAL SCAN RESULTS")
    print("=" * 50)
    
    if result["hot_stocks"]:
        print("\n  🔥 HOT STOCKS (multiple insider signals):")
        for h in result["hot_stocks"][:5]:
            print(f"    {h['symbol']:12s} Score={h['score']:3d} | {', '.join(h['signals'])}")
    
    if result["insider_trades"]:
        print("\n  👤 INSIDER TRADES:")
        for t in result["insider_trades"][:5]:
            icon = "🟢" if "BUY" in t["signal"] else "🔴"
            print(f"    {icon} {t['symbol']:12s} {t['type']:5s} ₹{t['value_cr']}Cr | {t['signal']}")
    
    if result["high_delivery_stocks"]:
        print("\n  📦 HIGH DELIVERY (>60%):")
        for d in result["high_delivery_stocks"][:5]:
            print(f"    {d['symbol']:12s} Delivery={d['delivery_pct']}% | {d['signal']}")
