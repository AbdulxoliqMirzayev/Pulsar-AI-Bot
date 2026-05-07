#ifndef AB_ARBITRAGE_MQH
#define AB_ARBITRAGE_MQH

double GetFastFeedPrice(string symbol)
{
   string gv = "AB_FAST_" + symbol;
   if(GlobalVariableCheck(gv)) return GlobalVariableGet(gv);
   int handle = FileOpen("Config/fast_feed.csv", FILE_READ | FILE_CSV | FILE_COMMON);
   if(handle == INVALID_HANDLE) return 0.0;
   double price = 0.0;
   while(!FileIsEnding(handle))
   {
      string s = FileReadString(handle);
      double p = FileReadNumber(handle);
      if(s == symbol)
      {
         price = p;
         break;
      }
   }
   FileClose(handle);
   return price;
}

bool ExecuteArbitrageTrade(string symbol, int direction, double lot)
{
   if(!UseArbitrage) return false;
   if(GetDailyLossPercent() >= 4.5) return false;
   double pip = PipSize(symbol);
   double ask = SymbolInfoDouble(symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(symbol, SYMBOL_BID);
   double entry = direction > 0 ? ask : bid;
   double sl = direction > 0 ? entry - 5.0 * pip : entry + 5.0 * pip;
   double tp = direction > 0 ? entry + 3.0 * pip : entry - 3.0 * pip;
   if(!CanOpenWithLot(symbol, lot, 5.0)) return false;
   bool ok = direction > 0 ? trade.Buy(lot, symbol, ask, sl, tp, "AB_ARBITRAGE")
                           : trade.Sell(lot, symbol, bid, sl, tp, "AB_ARBITRAGE");
   if(!ok) Print("Arbitrage order failed: ", trade.ResultRetcodeDescription());
   return ok;
}

bool CheckLatencyArbitrage(string symbol)
{
   if(!UseArbitrage) return false;
   double fastPrice = GetFastFeedPrice(symbol);
   if(fastPrice <= 0.0) return false;
   double slowPrice = SymbolInfoDouble(symbol, SYMBOL_BID);
   double spread = (double)SymbolInfoInteger(symbol, SYMBOL_SPREAD) * SymbolInfoDouble(symbol, SYMBOL_POINT);
   double minDiff = spread + 2.0 * PipSize(symbol);
   double diff = fastPrice - slowPrice;
   if(MathAbs(diff) > minDiff)
   {
      double lot = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
      return ExecuteArbitrageTrade(symbol, diff > 0.0 ? 1 : -1, lot);
   }
   return false;
}

#endif
