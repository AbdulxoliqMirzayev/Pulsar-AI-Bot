#ifndef AB_GRID_MQH
#define AB_GRID_MQH

double g_GridSpacingPips = 20.0;
int g_GridMaxLevels = 5;

void InitGrid(double spacingPips, int maxLevels)
{
   g_GridSpacingPips = MathMax(5.0, spacingPips);
   g_GridMaxLevels = MathMax(1, MathMin(maxLevels, 10));
   Print("AB_Grid initialized spacing=", g_GridSpacingPips, " levels=", g_GridMaxLevels);
}

bool GridRangeMarket(string symbol)
{
   double adx = IndicatorValue(g_ADX_handle, 0, 1);
   double upper = IndicatorValue(g_BB_handle, 1, 1);
   double middle = IndicatorValue(g_BB_handle, 0, 1);
   double lower = IndicatorValue(g_BB_handle, 2, 1);
   if(middle <= 0.0) return false;
   double bandwidth = (upper - lower) / middle * 100.0;
   return adx < 20.0 && bandwidth < 1.0;
}

double GridExposurePercent()
{
   double risk = OpenRiskMoney();
   return risk / MathMax(AccountInfoDouble(ACCOUNT_BALANCE), 1.0) * 100.0;
}

bool GridOrderExists(string symbol, double price, int type)
{
   double tol = 0.5 * PipSize(symbol);
   for(int i = OrdersTotal() - 1; i >= 0; i--)
   {
      ulong ticket = OrderGetTicket(i);
      if(ticket == 0) continue;
      if((int)OrderGetInteger(ORDER_MAGIC) != MagicNumber) continue;
      if(OrderGetString(ORDER_SYMBOL) != symbol) continue;
      if((int)OrderGetInteger(ORDER_TYPE) != type) continue;
      if(MathAbs(OrderGetDouble(ORDER_PRICE_OPEN) - price) <= tol) return true;
   }
   return false;
}

void CancelGridOrders(string symbol)
{
   for(int i = OrdersTotal() - 1; i >= 0; i--)
   {
      ulong ticket = OrderGetTicket(i);
      if(ticket == 0) continue;
      if((int)OrderGetInteger(ORDER_MAGIC) != MagicNumber) continue;
      if(OrderGetString(ORDER_SYMBOL) != symbol) continue;
      string comment = OrderGetString(ORDER_COMMENT);
      if(StringFind(comment, "AB_GRID") >= 0)
         trade.OrderDelete(ticket);
   }
}

void ManageGridSystem(string symbol)
{
   if(!UseGrid) return;
   if(GetDailyLossPercent() >= 4.5) { CancelGridOrders(symbol); return; }
   if(GridExposurePercent() >= 3.0) return;
   if(!GridRangeMarket(symbol)) { CancelGridOrders(symbol); g_GridActive = false; return; }
   if(IsNewsTime(30)) { CancelGridOrders(symbol); return; }

   g_GridActive = true;
   double bid = SymbolInfoDouble(symbol, SYMBOL_BID);
   double ask = SymbolInfoDouble(symbol, SYMBOL_ASK);
   double mid = (bid + ask) / 2.0;
   double pip = PipSize(symbol);
   double spacing = g_GridSpacingPips * pip;
   double slPips = g_GridSpacingPips * (double)g_GridMaxLevels * 1.4;
   double baseLot = CalculateLotSize(symbol, slPips) / MathMax((double)g_GridMaxLevels * 2.0, 1.0);
   double minLot = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
   baseLot = MathMax(minLot, NormalizeDouble(baseLot, 2));

   for(int level = 1; level <= g_GridMaxLevels; level++)
   {
      double buyPrice = NormalizeDouble(mid - spacing * level, (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS));
      double sellPrice = NormalizeDouble(mid + spacing * level, (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS));
      double buySL = buyPrice - slPips * pip;
      double buyTP = buyPrice + g_GridSpacingPips * pip;
      double sellSL = sellPrice + slPips * pip;
      double sellTP = sellPrice - g_GridSpacingPips * pip;
      if(!GridOrderExists(symbol, buyPrice, ORDER_TYPE_BUY_LIMIT))
      {
         if(!trade.BuyLimit(baseLot, buyPrice, symbol, buySL, buyTP, ORDER_TIME_GTC, 0, "AB_GRID_BUY"))
            Print("Grid BuyLimit failed: ", trade.ResultRetcodeDescription());
      }
      if(!GridOrderExists(symbol, sellPrice, ORDER_TYPE_SELL_LIMIT))
      {
         if(!trade.SellLimit(baseLot, sellPrice, symbol, sellSL, sellTP, ORDER_TIME_GTC, 0, "AB_GRID_SELL"))
            Print("Grid SellLimit failed: ", trade.ResultRetcodeDescription());
      }
   }
}

#endif
