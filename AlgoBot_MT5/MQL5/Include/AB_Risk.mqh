#ifndef AB_RISK_MQH
#define AB_RISK_MQH

datetime g_CurrentDay = 0;

void ResetDailyTrackingIfNeeded()
{
   MqlDateTime dt;
   TimeToStruct(TimeGMT(), dt);
   datetime today = StringToTime(IntegerToString(dt.year) + "." + IntegerToString(dt.mon) + "." + IntegerToString(dt.day));
   if(g_CurrentDay != today)
   {
      g_CurrentDay = today;
      g_DailyStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
      g_DailyPnL = 0.0;
   }
}

double GetCurrentDrawdown()
{
   if(g_AccountPeak <= 0.0) g_AccountPeak = AccountInfoDouble(ACCOUNT_BALANCE);
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   return (g_AccountPeak - equity) / MathMax(g_AccountPeak, 1.0) * 100.0;
}

double GetDailyLossPercent()
{
   ResetDailyTrackingIfNeeded();
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   return MathMax(0.0, (g_DailyStartBalance - equity) / MathMax(g_DailyStartBalance, 1.0) * 100.0);
}

int CountOpenPositionsByMagic()
{
   int count = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(!PositionSelectByTicket(ticket)) continue;
      if((int)PositionGetInteger(POSITION_MAGIC) == MagicNumber) count++;
   }
   return count;
}

double OpenRiskMoney()
{
   double risk = 0.0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0 || !PositionSelectByTicket(ticket)) continue;
      if((int)PositionGetInteger(POSITION_MAGIC) != MagicNumber) continue;
      string symbol = PositionGetString(POSITION_SYMBOL);
      double open = PositionGetDouble(POSITION_PRICE_OPEN);
      double sl = PositionGetDouble(POSITION_SL);
      double volume = PositionGetDouble(POSITION_VOLUME);
      if(sl <= 0.0) continue;
      double tickValue = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_VALUE);
      double tickSize = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_SIZE);
      double ticks = MathAbs(open - sl) / MathMax(tickSize, SymbolInfoDouble(symbol, SYMBOL_POINT));
      risk += ticks * tickValue * volume;
   }
   return risk;
}

bool CanOpenWithLot(string symbol, double lot, double sl_pips)
{
   if(lot <= 0.0 || sl_pips <= 0.0) return false;
   if(GetDailyLossPercent() >= 5.0) return false;
   double tickValue = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSize = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_SIZE);
   double pip = PipSize(symbol);
   double pipValuePerLot = tickValue * (pip / MathMax(tickSize, SymbolInfoDouble(symbol, SYMBOL_POINT)));
   double newRisk = sl_pips * pipValuePerLot * lot;
   double maxDailyMoney = AccountInfoDouble(ACCOUNT_BALANCE) * 0.05;
   return OpenRiskMoney() + newRisk <= maxDailyMoney;
}

double CalculateLotSize(string symbol, double sl_pips)
{
   if(sl_pips <= 0.0) return 0.0;
   double safeRisk = MathMin(MathMax(RiskPerTrade, 0.1), 2.0);
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double riskAmount = balance * safeRisk / 100.0;
   double tickValue = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSize = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_SIZE);
   double pip = PipSize(symbol);
   double pipValuePerLot = tickValue * (pip / MathMax(tickSize, SymbolInfoDouble(symbol, SYMBOL_POINT)));
   double lot = riskAmount / MathMax(sl_pips * pipValuePerLot, 0.01);

   double dd = GetCurrentDrawdown();
   if(dd > 5.0) lot *= 0.5;
   if(dd > 8.0) lot *= 0.25;
   if(dd >= 10.0) return 0.0;

   double minLot = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
   double maxLot = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MAX);
   double step = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);
   lot = MathFloor(lot / step) * step;
   lot = MathMax(minLot, MathMin(maxLot, lot));
   lot = NormalizeDouble(lot, 2);
   if(!CanOpenWithLot(symbol, lot, sl_pips)) return 0.0;
   return lot;
}

void CloseAllPositions()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0 || !PositionSelectByTicket(ticket)) continue;
      if((int)PositionGetInteger(POSITION_MAGIC) != MagicNumber) continue;
      if(!trade.PositionClose(ticket))
         Print("PositionClose failed ticket=", ticket, " retcode=", trade.ResultRetcode(), " ", trade.ResultRetcodeDescription());
   }
}

bool CheckAllRiskLimits()
{
   ResetDailyTrackingIfNeeded();
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   if(balance > g_AccountPeak) g_AccountPeak = balance;

   double dailyLoss = GetDailyLossPercent();
   if(dailyLoss >= MathMin(MaxDailyRisk, 5.0))
   {
      if(g_TradingEnabled)
      {
         Alert("DAILY HARD LIMIT HIT: " + DoubleToString(dailyLoss, 2) + "%. Bot stopped.");
         SendTelegramMessage("<b>Daily hard limit hit</b>: " + DoubleToString(dailyLoss, 2) + "%. Trading stopped.");
      }
      g_TradingEnabled = false;
      return false;
   }

   double dd = GetCurrentDrawdown();
   if(dd >= HardStopDrawdown)
   {
      CloseAllPositions();
      g_TradingEnabled = false;
      Alert("Hard stop drawdown hit. All AlgoBot positions closed.");
      SendTelegramMessage("<b>Hard drawdown stop</b>: all positions closed.");
      return false;
   }
   if(dd >= MaxDrawdown)
   {
      g_TradingEnabled = false;
      SendTelegramMessage("<b>Drawdown pause</b>: " + DoubleToString(dd, 2) + "%.");
      return false;
   }
   if(CountOpenPositionsByMagic() >= MaxOpenPositions) return false;
   return true;
}

bool IsMarketOpen()
{
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   return bid > 0.0 && ask > bid;
}

bool IsInTradingHours(int startHour, int endHour)
{
   MqlDateTime dt;
   TimeToStruct(TimeGMT(), dt);
   if(startHour == endHour) return true;
   if(startHour < endHour) return dt.hour >= startHour && dt.hour < endHour;
   return dt.hour >= startHour || dt.hour < endHour;
}

bool IsTradingDay()
{
   MqlDateTime dt;
   TimeToStruct(TimeGMT(), dt);
   if(dt.day_of_week == 0 || dt.day_of_week == 6) return false;
   if(dt.day_of_week == 1 && !TradeMonday) return false;
   if(dt.day_of_week == 5 && !TradeFriday) return false;
   if(dt.day_of_week == 5 && dt.hour >= 21) return false;
   return true;
}

bool SpreadOK(string symbol)
{
   double spread = SymbolInfoInteger(symbol, SYMBOL_SPREAD) * SymbolInfoDouble(symbol, SYMBOL_POINT);
   double pip = PipSize(symbol);
   return spread <= 5.0 * pip;
}

int GetCurrentLossStreak()
{
   if(!HistorySelect(TimeCurrent() - 86400 * 30, TimeCurrent())) return 0;
   int streak = 0;
   for(int i = HistoryDealsTotal() - 1; i >= 0; i--)
   {
      ulong deal = HistoryDealGetTicket(i);
      if((int)HistoryDealGetInteger(deal, DEAL_MAGIC) != MagicNumber) continue;
      if((long)HistoryDealGetInteger(deal, DEAL_ENTRY) != DEAL_ENTRY_OUT) continue;
      double profit = HistoryDealGetDouble(deal, DEAL_PROFIT) + HistoryDealGetDouble(deal, DEAL_SWAP) + HistoryDealGetDouble(deal, DEAL_COMMISSION);
      if(profit < 0.0) streak++;
      else break;
   }
   return streak;
}

bool CanTradeAfterLosses()
{
   int streak = GetCurrentLossStreak();
   if(streak >= 5)
   {
      g_TradingEnabled = false;
      SendTelegramMessage("<b>Loss streak guard</b>: bot paused for the day.");
      return false;
   }
   return true;
}

#endif
