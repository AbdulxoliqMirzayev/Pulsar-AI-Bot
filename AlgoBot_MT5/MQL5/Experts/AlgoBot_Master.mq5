//+------------------------------------------------------------------+
//| AlgoBot_Master.mq5 - Ultra Algorithmic Trading Robot v3.0         |
//| 20 strategies, SMC, ML, grid, prop firm guard, copier, dashboard  |
//+------------------------------------------------------------------+
#property copyright "AlgoBot v3.0"
#property version   "3.00"
#property strict

#include <Trade/Trade.mqh>

input group "RISK MANAGEMENT"
input double   RiskPerTrade      = 2.0;
input double   MaxDailyRisk      = 5.0;
input double   MaxDrawdown       = 10.0;
input double   HardStopDrawdown  = 15.0;
input int      MaxOpenPositions  = 5;
input double   MinRiskReward     = 1.5;
input int      MinScoreToTrade   = 12;

input group "STRATEGIES"
input bool     UseStrategy_Fib        = true;
input bool     UseStrategy_Gann       = true;
input bool     UseStrategy_OB         = true;
input bool     UseStrategy_BOS_CHoCH  = true;
input bool     UseStrategy_Liquidity  = true;
input bool     UseStrategy_FVG        = true;
input bool     UseStrategy_RSI        = true;
input bool     UseStrategy_EMA        = true;
input bool     UseStrategy_VWAP       = true;
input bool     UseStrategy_BB         = true;
input bool     UseStrategy_MACD       = true;
input bool     UseStrategy_SR         = true;
input bool     UseStrategy_ICT        = true;
input bool     UseStrategy_Stoch      = true;
input bool     UseStrategy_ATR        = true;
input bool     UseStrategy_Engulf     = true;
input bool     UseStrategy_Wick       = true;
input bool     UseStrategy_Premium    = true;
input bool     UseStrategy_Martingale = false;
input bool     UseStrategy_MTF        = true;

input group "MACHINE LEARNING"
input bool     UseML              = true;
input int      ML_MinConfidence   = 70;
input int      ML_RetrainBars     = 500;
input bool     UseARIMA           = true;

input group "SMART MONEY CONCEPTS"
input bool     UseSMC             = true;
input int      OB_Lookback        = 50;
input int      FVG_MinSize        = 5;
input bool     UseKillzones       = true;
input bool     UseLiquiditySweep  = true;

input group "ADVANCED MODULES"
input bool     UseGrid             = true;
input double   Grid_PipSpacing     = 20.0;
input int      Grid_MaxLevels      = 5;
input bool     UseElliottWave      = true;
input bool     UseSentiment        = true;
input bool     UseArbitrage        = false;
input bool     UsePropFirmMode     = false;
input bool     UseCorrelationCheck = true;
input bool     UseGenericOptimizer = true;

input group "PROP FIRM MODE"
input double   PropFirm_MaxDailyLoss = 5.0;
input double   PropFirm_MaxTotalLoss = 10.0;
input double   PropFirm_ProfitTarget = 10.0;
input bool     PropFirm_NewsFilter   = true;
input string   PropFirm_Name         = "FTMO";

input group "TELEGRAM"
input string   TelegramToken      = "";
input string   TelegramChatID     = "";
input bool     SendTradeAlerts    = true;
input bool     SendDailyReport    = true;

input group "ACCOUNT COPIER"
input bool     IsMasterAccount    = true;
input string   CopierServerIP     = "127.0.0.1";
input int      CopierServerPort   = 5555;

input group "SYSTEM"
input int      MagicNumber        = 202401;
input int      Slippage           = 3;
input int      ScanIntervalMS     = 500;
input int      TradingHour_Start  = 2;
input int      TradingHour_End    = 20;
input bool     TradeMonday        = true;
input bool     TradeFriday        = true;

CTrade trade;
double g_AccountPeak = 0.0;
double g_DailyStartBalance = 0.0;
double g_DailyPnL = 0.0;
bool   g_TradingEnabled = true;
bool   g_GridActive = false;
int    g_SignalScore = 0;
int    g_ML_Signal = 0;
string g_DailyBias = "NEUTRAL";
int    g_ElliottWave = 0;
double g_SentimentScore = 0.0;
datetime g_LastRetrainTime = 0;
datetime g_LastOptimizeTime = 0;
datetime g_LastTradeBarTime = 0;

int g_RSI_handle = INVALID_HANDLE;
int g_MACD_handle = INVALID_HANDLE;
int g_BB_handle = INVALID_HANDLE;
int g_ATR_handle = INVALID_HANDLE;
int g_EMA9_handle = INVALID_HANDLE;
int g_EMA21_handle = INVALID_HANDLE;
int g_EMA50_handle = INVALID_HANDLE;
int g_EMA200_handle = INVALID_HANDLE;
int g_Stoch_handle = INVALID_HANDLE;
int g_ADX_handle = INVALID_HANDLE;
int g_CCI_handle = INVALID_HANDLE;
int g_WPR_handle = INVALID_HANDLE;
int g_SAR_handle = INVALID_HANDLE;

#include <AB_SMC.mqh>
#include <AB_Telegram.mqh>
#include <AB_Risk.mqh>
#include <AB_PropFirm.mqh>
#include <AB_Strategies.mqh>
#include <AB_ML.mqh>
#include <AB_Grid.mqh>
#include <AB_Elliott.mqh>
#include <AB_Correlation.mqh>
#include <AB_Arbitrage.mqh>
#include <AB_Copier.mqh>
#include <AB_Dashboard.mqh>

bool LoadConfig(string fileName)
{
   int handle = FileOpen(fileName, FILE_READ | FILE_TXT | FILE_COMMON);
   if(handle == INVALID_HANDLE) return false;
   string text = "";
   while(!FileIsEnding(handle)) text += FileReadString(handle);
   FileClose(handle);
   if(StringFind(text, "\"version\"") < 0) return false;
   if(StringFind(text, "\"max_daily_risk\"") >= 0 && MaxDailyRisk > 5.0)
      Print("Config validation: MaxDailyRisk input is capped to 5% by risk module.");
   return true;
}

bool LoadGAParams(string fileName)
{
   int handle = FileOpen(fileName, FILE_READ | FILE_TXT | FILE_COMMON);
   if(handle == INVALID_HANDLE) return false;
   string text = "";
   while(!FileIsEnding(handle)) text += FileReadString(handle);
   FileClose(handle);
   return StringLen(text) > 2;
}

void RunGeneticOptimizer()
{
   int handle = FileOpen("Logs/optimizer_requests.csv", FILE_READ | FILE_WRITE | FILE_CSV | FILE_COMMON);
   if(handle == INVALID_HANDLE) return;
   FileSeek(handle, 0, SEEK_END);
   FileWrite(handle, TimeToString(TimeGMT(), TIME_DATE | TIME_SECONDS), Symbol(), "RUN_GA");
   FileClose(handle);
}

double GetSentimentScore(string symbol)
{
   int sock = SocketCreate();
   if(sock != INVALID_HANDLE && SocketConnect(sock, "127.0.0.1", 9999, 500))
   {
      uchar req[];
      uchar resp[];
      StringToCharArray(symbol + "\n", req, 0, WHOLE_ARRAY, CP_UTF8);
      SocketSend(sock, req, ArraySize(req));
      ArrayResize(resp, 256);
      uint read = SocketRead(sock, resp, 256, 1200);
      SocketClose(sock);
      if(read > 0) return StringToDouble(CharArrayToString(resp, 0, (int)read, CP_UTF8));
   }

   int handle = FileOpen("Config/sentiment.csv", FILE_READ | FILE_CSV | FILE_COMMON);
   if(handle == INVALID_HANDLE) return 0.0;
   double score = 0.0;
   while(!FileIsEnding(handle))
   {
      string s = FileReadString(handle);
      double v = FileReadNumber(handle);
      if(s == symbol) { score = v; break; }
   }
   FileClose(handle);
   return MathMax(-1.0, MathMin(1.0, score));
}

void AdjustBiasWithSentiment(double score)
{
   if(score > 0.8 && (g_DailyBias == "NEUTRAL" || g_DailyBias == "BULL")) g_DailyBias = "STRONG_BULL";
   if(score < -0.8 && (g_DailyBias == "NEUTRAL" || g_DailyBias == "BEAR")) g_DailyBias = "STRONG_BEAR";
}

void LogTradeCSV(string action, string symbol, int direction, double lot, double price, double sl, double tp, int score)
{
   int handle = FileOpen("Logs/trades.csv", FILE_READ | FILE_WRITE | FILE_CSV | FILE_COMMON);
   if(handle == INVALID_HANDLE)
   {
      Print("Trade log open failed: ", GetLastError());
      return;
   }
   FileSeek(handle, 0, SEEK_END);
   FileWrite(handle, TimeToString(TimeGMT(), TIME_DATE | TIME_SECONDS), action, symbol, direction > 0 ? "BUY" : "SELL", lot, price, sl, tp, score, GetMLConfidence());
   FileClose(handle);
}

void LogSignalCSV(string symbol, int direction, int score)
{
   int handle = FileOpen("Logs/signals.csv", FILE_READ | FILE_WRITE | FILE_CSV | FILE_COMMON);
   if(handle == INVALID_HANDLE) return;
   FileSeek(handle, 0, SEEK_END);
   FileWrite(handle, TimeToString(TimeGMT(), TIME_DATE | TIME_SECONDS), symbol, direction, score, g_BuyScore, g_SellScore, g_DailyBias, g_ML_Signal, g_SentimentScore);
   FileClose(handle);
}

void WriteStateJSON()
{
   int handle = FileOpen("Logs/state.json", FILE_WRITE | FILE_TXT | FILE_COMMON);
   if(handle == INVALID_HANDLE) return;
   string ml = g_ML_Signal > 0 ? "BUY" : g_ML_Signal < 0 ? "SELL" : "NEUTRAL";
   string json = "{";
   json += "\"active\":" + (g_TradingEnabled ? "true" : "false") + ",";
   json += "\"balance\":" + DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE), 2) + ",";
   json += "\"currency\":\"" + AccountInfoString(ACCOUNT_CURRENCY) + "\",";
   json += "\"open_trades\":" + IntegerToString(CountOpenPositionsByMagic()) + ",";
   json += "\"daily_pnl\":" + DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY) - g_DailyStartBalance, 2) + ",";
   json += "\"risk_used\":" + DoubleToString(OpenRiskMoney() / MathMax(AccountInfoDouble(ACCOUNT_BALANCE), 1.0) * 100.0, 2) + ",";
   json += "\"signal_score\":" + IntegerToString(g_SignalScore) + ",";
   json += "\"ml_signal\":\"" + ml + "\",";
   json += "\"elliott_wave\":" + IntegerToString(g_ElliottWave) + ",";
   json += "\"sentiment\":" + DoubleToString(g_SentimentScore, 4) + ",";
   json += "\"daily_bias\":\"" + g_DailyBias + "\"";
   json += "}";
   FileWriteString(handle, json);
   FileClose(handle);
}

void ProcessControlCommands()
{
   int handle = FileOpen("Config/commands.csv", FILE_READ | FILE_CSV | FILE_COMMON);
   if(handle == INVALID_HANDLE) return;
   string lastCommand = "";
   while(!FileIsEnding(handle))
   {
      string command = FileReadString(handle);
      if(command != "") lastCommand = command;
   }
   FileClose(handle);
   FileDelete("Config/commands.csv", FILE_COMMON);
   if(lastCommand == "START") g_TradingEnabled = true;
   if(lastCommand == "PAUSE") g_TradingEnabled = false;
   if(lastCommand == "CLOSE_ALL") CloseAllPositions();
}

bool ExecuteMainTrade(int direction, int score)
{
   if(direction == 0) return false;
   if(g_LastTradeBarTime == iTime(Symbol(), PERIOD_M15, 0)) return false;
   if(!CheckAllRiskLimits()) return false;
   if(!CanTradeAfterLosses()) return false;
   if(!SpreadOK(Symbol())) return false;
   if(CountOpenPositionsByMagic() >= MaxOpenPositions) return false;

   double atr = GetATRValue(Symbol(), PERIOD_M15, 14, 1);
   double pip = PipSize(Symbol());
   double slPips = MathMax(atr * 2.0 / pip, 12.0);
   double tpPips = slPips * MathMax(MinRiskReward, 1.5);
   double lot = CalculateLotSize(Symbol(), slPips);
   if(lot <= 0.0) return false;

   double ask = SymbolInfoDouble(Symbol(), SYMBOL_ASK);
   double bid = SymbolInfoDouble(Symbol(), SYMBOL_BID);
   double entry = direction > 0 ? ask : bid;
   double sl = direction > 0 ? entry - slPips * pip : entry + slPips * pip;
   double tp = direction > 0 ? entry + tpPips * pip : entry - tpPips * pip;
   if(sl <= 0.0 || tp <= 0.0) return false;

   bool ok = false;
   if(direction > 0)
      ok = trade.Buy(lot, Symbol(), ask, sl, tp, "AlgoBot v3 score " + IntegerToString(score));
   else
      ok = trade.Sell(lot, Symbol(), bid, sl, tp, "AlgoBot v3 score " + IntegerToString(score));

   if(!ok)
   {
      Print("OrderSend failed: ", trade.ResultRetcode(), " ", trade.ResultRetcodeDescription());
      int err = FileOpen("Logs/errors.log", FILE_READ | FILE_WRITE | FILE_TXT | FILE_COMMON);
      if(err != INVALID_HANDLE)
      {
         FileSeek(err, 0, SEEK_END);
         FileWrite(err, TimeToString(TimeGMT(), TIME_DATE | TIME_SECONDS) + " OrderSend failed " + trade.ResultRetcodeDescription());
         FileClose(err);
      }
      return false;
   }

   g_LastTradeBarTime = iTime(Symbol(), PERIOD_M15, 0);
   LogTradeCSV("OPEN", Symbol(), direction, lot, entry, sl, tp, score);
   SendTradeTelegram(Symbol(), direction, lot, entry, sl, tp, score);
   BroadcastTradeToSlaves(Symbol(), direction, lot, entry, sl, tp, score);
   return true;
}

void ManageAllOpenPositions()
{
   double atr = GetATRValue(Symbol(), PERIOD_M15, 14, 1);
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0 || !PositionSelectByTicket(ticket)) continue;
      if((int)PositionGetInteger(POSITION_MAGIC) != MagicNumber) continue;
      string symbol = PositionGetString(POSITION_SYMBOL);
      long type = PositionGetInteger(POSITION_TYPE);
      double sl = PositionGetDouble(POSITION_SL);
      double tp = PositionGetDouble(POSITION_TP);
      double bid = SymbolInfoDouble(symbol, SYMBOL_BID);
      double ask = SymbolInfoDouble(symbol, SYMBOL_ASK);
      if(type == POSITION_TYPE_BUY)
      {
         double newSL = bid - atr * 2.0;
         if(newSL > sl && newSL < bid) trade.PositionModify(ticket, newSL, tp);
      }
      else if(type == POSITION_TYPE_SELL)
      {
         double newSL = ask + atr * 2.0;
         if((sl == 0.0 || newSL < sl) && newSL > ask) trade.PositionModify(ticket, newSL, tp);
      }
   }
}

int OnInit()
{
   if(!TerminalInfoInteger(TERMINAL_CONNECTED))
   {
      Alert("MT5 terminal is not connected to broker.");
      return INIT_FAILED;
   }
   if(!TerminalInfoInteger(TERMINAL_TRADE_ALLOWED))
   {
      Alert("Enable Algo Trading in MT5 terminal settings.");
      return INIT_FAILED;
   }
   if(!MQLInfoInteger(MQL_TRADE_ALLOWED))
   {
      Alert("Enable Allow Algo Trading in EA properties.");
      return INIT_FAILED;
   }
   if(MaxDailyRisk > 5.0)
      Print("MaxDailyRisk input above 5%; hard cap remains 5% in code.");

   trade.SetExpertMagicNumber(MagicNumber);
   trade.SetDeviationInPoints(Slippage);
   LoadConfig("Config/config.json");
   if(!InitAllIndicators())
   {
      Print("Indicator initialization failed.");
      return INIT_FAILED;
   }
   if(UseML && !LoadMLWeights("Models/nn_model_weights.bin"))
   {
      Print("ML weights not found. Training lightweight model.");
      TrainMLModel();
   }
   if(UseGenericOptimizer) LoadGAParams("Models/genetic_best_params.json");

   g_AccountPeak = AccountInfoDouble(ACCOUNT_BALANCE);
   g_DailyStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   ResetDailyTrackingIfNeeded();

   if(UseSMC) InitSMC();
   if(UsePropFirmMode) InitPropFirmRules(PropFirm_Name);
   if(UseGrid) InitGrid(Grid_PipSpacing, Grid_MaxLevels);
   if(UseElliottWave) InitElliottWave();
   if(UseCorrelationCheck) InitCorrelationMatrix();
   if(IsMasterAccount) InitCopierServer(CopierServerIP, CopierServerPort);
   if(TelegramToken != "")
   {
      InitTelegram(TelegramToken, TelegramChatID);
      SendTelegramMessage("<b>AlgoBot v3.0 started</b>\nBalance: " + DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE), 2));
   }
   DrawDashboard();
   EventSetMillisecondTimer(MathMax(100, ScanIntervalMS));
   Print("AlgoBot v3.0 loaded. Account: ", (long)AccountInfoInteger(ACCOUNT_LOGIN));
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   ReleaseAllIndicators();
   if(g_CopierSocket != INVALID_HANDLE) SocketClose(g_CopierSocket);
   ObjectsDeleteAll(0, "AB_");
}

void OnChartEvent(const int id, const long &lparam, const double &dparam, const string &sparam)
{
   if(id != CHARTEVENT_OBJECT_CLICK) return;
   if(sparam == "AB_BTN_PAUSE") g_TradingEnabled = !g_TradingEnabled;
   if(sparam == "AB_BTN_CLOSE") CloseAllPositions();
   if(sparam == "AB_BTN_GRID") g_GridActive = !g_GridActive;
   UpdateDashboard(g_SignalScore, g_ML_Signal, g_DailyBias, g_SentimentScore, g_ElliottWave);
}

void OnTick()
{
   UpdateDashboard(g_SignalScore, g_ML_Signal, g_DailyBias, g_SentimentScore, g_ElliottWave);
}

void OnTimer()
{
   ResetDailyTrackingIfNeeded();
   ProcessControlCommands();
   if(!g_TradingEnabled) { UpdateDashboard(g_SignalScore, g_ML_Signal, g_DailyBias, g_SentimentScore, g_ElliottWave); return; }
   if(!IsMarketOpen()) return;
   if(!IsInTradingHours(TradingHour_Start, TradingHour_End)) return;
   if(!IsTradingDay()) return;

   if(!CheckAllRiskLimits()) return;
   if(UsePropFirmMode)
   {
      if(!PropFirmRulesOK()) return;
      if(PropFirm_NewsFilter && IsNewsTime(30)) return;
   }

   g_DailyBias = AnalyzeDailyBias(Symbol());
   AnalyzeMarketStructure(Symbol(), PERIOD_H1);
   AnalyzeMarketStructure(Symbol(), PERIOD_H4);
   UpdateAllIndicators();

   if(UseCorrelationCheck)
   {
      UpdateCorrelationMatrix();
      if(IsCorrelated(Symbol())) return;
   }

   if(UseSentiment)
   {
      g_SentimentScore = GetSentimentScore(Symbol());
      if(MathAbs(g_SentimentScore) > 0.8) AdjustBiasWithSentiment(g_SentimentScore);
   }

   if(UseElliottWave) g_ElliottWave = DetectElliottWave(Symbol(), PERIOD_H1);
   g_SignalScore = RunAllStrategies(Symbol());

   if(UseML)
   {
      double features[];
      BuildFeatureVector(features);
      g_ML_Signal = PredictMLSignal(features);
      if(UseARIMA)
      {
         int arimaSignal = ARIMAForecastSignal(Symbol(), PERIOD_H1);
         if(arimaSignal != 0 && arimaSignal == g_ML_Signal) g_SignalScore += 1;
      }
      if(GetMLConfidence() < (double)ML_MinConfidence) g_ML_Signal = 0;
   }

   if(UseArbitrage) CheckLatencyArbitrage(Symbol());

   int direction = DetermineDirection();
   LogSignalCSV(Symbol(), direction, g_SignalScore);
   if(direction != 0 && g_SignalScore >= MinScoreToTrade)
   {
      if(g_ML_Signal == 0 || g_ML_Signal == direction)
         ExecuteMainTrade(direction, g_SignalScore);
   }

   if(UseGrid) ManageGridSystem(Symbol());
   ManageAllOpenPositions();

   if(UseML && Bars(Symbol(), PERIOD_H1) % ML_RetrainBars == 0 && TimeCurrent() - g_LastRetrainTime > 3600)
   {
      TrainMLModel();
      g_LastRetrainTime = TimeCurrent();
   }
   if(UseGenericOptimizer && TimeCurrent() - g_LastOptimizeTime > 604800)
   {
      RunGeneticOptimizer();
      g_LastOptimizeTime = TimeCurrent();
   }
   UpdateDashboard(g_SignalScore, g_ML_Signal, g_DailyBias, g_SentimentScore, g_ElliottWave);
   WriteStateJSON();
   if(IsMasterAccount) BroadcastSignalToSlaves();
}
