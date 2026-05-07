#ifndef AB_DASHBOARD_MQH
#define AB_DASHBOARD_MQH

void CreateDashboardButton(string name, string text, int x, int y, int w, int h)
{
   if(ObjectFind(0, name) < 0) ObjectCreate(0, name, OBJ_BUTTON, 0, 0, 0);
   ObjectSetInteger(0, name, OBJPROP_XDISTANCE, x);
   ObjectSetInteger(0, name, OBJPROP_YDISTANCE, y);
   ObjectSetInteger(0, name, OBJPROP_XSIZE, w);
   ObjectSetInteger(0, name, OBJPROP_YSIZE, h);
   ObjectSetInteger(0, name, OBJPROP_COLOR, clrWhite);
   ObjectSetInteger(0, name, OBJPROP_BGCOLOR, clrDarkSlateGray);
   ObjectSetString(0, name, OBJPROP_TEXT, text);
}

void DrawDashboard()
{
   if(ObjectFind(0, "AB_PANEL") < 0) ObjectCreate(0, "AB_PANEL", OBJ_RECTANGLE_LABEL, 0, 0, 0);
   ObjectSetInteger(0, "AB_PANEL", OBJPROP_XDISTANCE, 8);
   ObjectSetInteger(0, "AB_PANEL", OBJPROP_YDISTANCE, 18);
   ObjectSetInteger(0, "AB_PANEL", OBJPROP_XSIZE, 360);
   ObjectSetInteger(0, "AB_PANEL", OBJPROP_YSIZE, 230);
   ObjectSetInteger(0, "AB_PANEL", OBJPROP_BGCOLOR, clrBlack);
   ObjectSetInteger(0, "AB_PANEL", OBJPROP_COLOR, clrDimGray);

   if(ObjectFind(0, "AB_PANEL_TEXT") < 0) ObjectCreate(0, "AB_PANEL_TEXT", OBJ_LABEL, 0, 0, 0);
   ObjectSetInteger(0, "AB_PANEL_TEXT", OBJPROP_XDISTANCE, 18);
   ObjectSetInteger(0, "AB_PANEL_TEXT", OBJPROP_YDISTANCE, 26);
   ObjectSetInteger(0, "AB_PANEL_TEXT", OBJPROP_COLOR, clrWhite);
   ObjectSetInteger(0, "AB_PANEL_TEXT", OBJPROP_FONTSIZE, 9);
   CreateDashboardButton("AB_BTN_PAUSE", "PAUSE", 18, 208, 80, 26);
   CreateDashboardButton("AB_BTN_CLOSE", "CLOSE ALL", 108, 208, 100, 26);
   CreateDashboardButton("AB_BTN_GRID", "GRID", 218, 208, 70, 26);
}

void UpdateDashboard(int score, int mlSignal, string dailyBias, double sentiment, int elliottWave)
{
   string status = g_TradingEnabled ? "LIVE" : "PAUSED";
   string ml = mlSignal > 0 ? "BUY" : mlSignal < 0 ? "SELL" : "NEUTRAL";
   string text = "AlgoBot v3.0 [" + status + "]\n";
   text += "Balance: " + DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE), 2) + " " + AccountInfoString(ACCOUNT_CURRENCY) + "\n";
   text += "Equity:  " + DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY), 2) + "\n";
   text += "Daily loss: " + DoubleToString(GetDailyLossPercent(), 2) + "% / 5.00%\n";
   text += "Drawdown: " + DoubleToString(GetCurrentDrawdown(), 2) + "%\n";
   text += "Open trades: " + IntegerToString(CountOpenPositionsByMagic()) + "\n";
   text += "Signal score: " + IntegerToString(score) + " | Buy " + IntegerToString(g_BuyScore) + " / Sell " + IntegerToString(g_SellScore) + "\n";
   text += "ML: " + ml + " (" + DoubleToString(GetMLConfidence(), 1) + "%)\n";
   text += "Bias: " + dailyBias + " | Sentiment: " + DoubleToString(sentiment, 2) + "\n";
   text += "Elliott: " + IntegerToString(elliottWave) + " | Grid: " + (g_GridActive ? "ON" : "OFF") + "\n";
   if(UsePropFirmMode)
   {
      PropFirmStatus ps = GetPropFirmStatus();
      text += "Prop daily: " + DoubleToString(ps.dailyLossUsed, 2) + "% | total: " + DoubleToString(ps.totalLossUsed, 2) + "%\n";
   }
   ObjectSetString(0, "AB_PANEL_TEXT", OBJPROP_TEXT, text);
}

#endif
