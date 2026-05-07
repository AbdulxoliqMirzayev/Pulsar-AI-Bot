//+------------------------------------------------------------------+
//| AlgoTradingBot_v1.mq5                                            |
//| Pulsar MT5 Expert Advisor                                        |
//+------------------------------------------------------------------+
#property strict
#property version   "1.00"
#property description "Professional multi-strategy EA with SMC/ICT, ML proxy scoring, dashboard and risk caps."

#include <Trade/Trade.mqh>

enum ENUM_STRATEGY_MODE
{
   STRATEGY_ALL = 0,
   STRATEGY_SINGLE = 1,
   STRATEGY_HYBRID = 2
};

input double RiskPercent = 5.0;
input double MaxDrawdown = 15.0;
input int    MagicNumber = 202401;
input int    Slippage = 3;
input int    TradingHours_Start = 8;
input int    TradingHours_End = 20;
input bool   UseML = true;
input bool   UseSMC = true;
input ENUM_STRATEGY_MODE StrategyMode = STRATEGY_ALL;
input int    MinScoreToTrade = 8;
input int    LookbackBars = 500;
input double MinRR = 1.5;
input int    MaxOpenPositions = 3;

struct StrategyVote
{
   int direction;  // 1 buy, -1 sell, 0 none
   int score;
   string name;
};

struct OrderBlock
{
   double high;
   double low;
   double mid;
   bool isBullish;
   bool isValid;
   int barIndex;
   double volumeAtCreation;
};

CTrade trade;
MqlRates rates[];
double PeakBalance = 0.0;
bool AlgoTradingEnabled = false;
int LastSignalDirection = 0;
int LastSignalScore = 0;
string LastMLSignal = "NEUTRAL";
string HTFBias = "NEUTRAL";
datetime LastTradeBarTime = 0;

int hRSI = INVALID_HANDLE;
int hMACD = INVALID_HANDLE;
int hBands = INVALID_HANDLE;
int hATR = INVALID_HANDLE;
int hEMA9 = INVALID_HANDLE;
int hEMA21 = INVALID_HANDLE;
int hEMA50 = INVALID_HANDLE;
int hEMA100 = INVALID_HANDLE;
int hEMA200 = INVALID_HANDLE;
int hStoch = INVALID_HANDLE;
int hADX = INVALID_HANDLE;
int hCCI = INVALID_HANDLE;
int hWPR = INVALID_HANDLE;
int hIchimoku = INVALID_HANDLE;
int hSAR = INVALID_HANDLE;

//+------------------------------------------------------------------+
int OnInit()
{
   if(!TerminalInfoInteger(TERMINAL_CONNECTED))
   {
      Print("ERROR: MT5 terminal is not connected to broker.");
      return INIT_FAILED;
   }
   if(!AccountInfoInteger(ACCOUNT_TRADE_ALLOWED))
   {
      Print("ERROR: Account trading permission is disabled.");
      return INIT_FAILED;
   }
   if(!MQLInfoInteger(MQL_TRADE_ALLOWED))
   {
      Print("ERROR: Enable Algo Trading in MT5 first.");
      return INIT_FAILED;
   }

   trade.SetExpertMagicNumber(MagicNumber);
   trade.SetDeviationInPoints(Slippage);
   PeakBalance = AccountInfoDouble(ACCOUNT_BALANCE);

   if(!LoadIndicatorHandles())
   {
      Print("ERROR: Indicator handle initialization failed.");
      return INIT_FAILED;
   }

   ArraySetAsSeries(rates, true);
   AlgoTradingEnabled = true;
   CreateChartPanel();
   EventSetMillisecondTimer(500);
   Print("AlgoBot ACTIVE | Risk: ", SafeRiskPercent(), "% | Symbol: ", _Symbol);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   ReleaseIndicatorHandles();
   ObjectsDeleteAll(0, "PULSAR_");
}

void OnTick()
{
   UpdateDashboardPanel();
}

void OnTrade()
{
   UpdateDashboardPanel();
}

void OnChartEvent(const int id,const long &lparam,const double &dparam,const string &sparam)
{
   if(id == CHARTEVENT_OBJECT_CLICK)
   {
      if(sparam == "PULSAR_PAUSE")
      {
         AlgoTradingEnabled = !AlgoTradingEnabled;
         Print("Algo trading toggled: ", AlgoTradingEnabled ? "ON" : "OFF");
      }
      if(sparam == "PULSAR_CLOSE_ALL")
      {
         CloseAllPositions();
      }
   }
}

void OnTimer()
{
   if(!MQLInfoInteger(MQL_TRADE_ALLOWED))
   {
      AlgoTradingEnabled = false;
      UpdateDashboardPanel();
      return;
   }
   if(!AlgoTradingEnabled) { UpdateDashboardPanel(); return; }
   if(!IsMarketOpen()) { UpdateDashboardPanel(); return; }
   if(!InTradingHours()) { UpdateDashboardPanel(); return; }
   if(!RiskCheck()) { UpdateDashboardPanel(); return; }
   if(!LoadRates(PERIOD_M15, LookbackBars)) { UpdateDashboardPanel(); return; }

   AnalyzeMarketStructure(_Symbol, PERIOD_H1);
   MapLiquidity();

   int score = RunAllStrategies();
   int mlSignal = UseML ? GetMLPrediction() : LastSignalDirection;
   if(UseML && mlSignal != 0 && mlSignal == LastSignalDirection)
      score += 3;
   LastSignalScore = score;

   if(score >= MinScoreToTrade && LastSignalDirection != 0 && (!UseML || mlSignal == LastSignalDirection))
      ExecuteTrade(LastSignalDirection);

   ManageOpenTrades();
   UpdateDashboardPanel();
}

//+------------------------------------------------------------------+
bool LoadIndicatorHandles()
{
   hRSI = iRSI(_Symbol, PERIOD_M15, 14, PRICE_CLOSE);
   hMACD = iMACD(_Symbol, PERIOD_M15, 12, 26, 9, PRICE_CLOSE);
   hBands = iBands(_Symbol, PERIOD_M15, 20, 0, 2.0, PRICE_CLOSE);
   hATR = iATR(_Symbol, PERIOD_M15, 14);
   hEMA9 = iMA(_Symbol, PERIOD_M15, 9, 0, MODE_EMA, PRICE_CLOSE);
   hEMA21 = iMA(_Symbol, PERIOD_M15, 21, 0, MODE_EMA, PRICE_CLOSE);
   hEMA50 = iMA(_Symbol, PERIOD_M15, 50, 0, MODE_EMA, PRICE_CLOSE);
   hEMA100 = iMA(_Symbol, PERIOD_M15, 100, 0, MODE_EMA, PRICE_CLOSE);
   hEMA200 = iMA(_Symbol, PERIOD_M15, 200, 0, MODE_EMA, PRICE_CLOSE);
   hStoch = iStochastic(_Symbol, PERIOD_M15, 5, 3, 3, MODE_SMA, STO_LOWHIGH);
   hADX = iADX(_Symbol, PERIOD_M15, 14);
   hCCI = iCCI(_Symbol, PERIOD_M15, 14, PRICE_TYPICAL);
   hWPR = iWPR(_Symbol, PERIOD_M15, 14);
   hIchimoku = iIchimoku(_Symbol, PERIOD_M15, 9, 26, 52);
   hSAR = iSAR(_Symbol, PERIOD_M15, 0.02, 0.2);
   return hRSI != INVALID_HANDLE && hMACD != INVALID_HANDLE && hBands != INVALID_HANDLE && hATR != INVALID_HANDLE &&
          hEMA9 != INVALID_HANDLE && hEMA21 != INVALID_HANDLE && hEMA200 != INVALID_HANDLE && hStoch != INVALID_HANDLE &&
          hADX != INVALID_HANDLE && hCCI != INVALID_HANDLE && hWPR != INVALID_HANDLE && hIchimoku != INVALID_HANDLE && hSAR != INVALID_HANDLE;
}

void ReleaseIndicatorHandles()
{
   int handles[] = {hRSI, hMACD, hBands, hATR, hEMA9, hEMA21, hEMA50, hEMA100, hEMA200, hStoch, hADX, hCCI, hWPR, hIchimoku, hSAR};
   for(int i = 0; i < ArraySize(handles); i++)
      if(handles[i] != INVALID_HANDLE) IndicatorRelease(handles[i]);
}

bool LoadRates(ENUM_TIMEFRAMES tf, int count)
{
   int copied = CopyRates(_Symbol, tf, 0, count, rates);
   ArraySetAsSeries(rates, true);
   return copied >= 220;
}

double BufferValue(int handle, int buffer, int shift)
{
   double data[];
   ArraySetAsSeries(data, true);
   if(CopyBuffer(handle, buffer, shift, 1, data) <= 0) return 0.0;
   return data[0];
}

double SafeRiskPercent()
{
   return MathMin(MathMax(RiskPercent, 0.1), 5.0);
}

bool IsMarketOpen()
{
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   return bid > 0 && ask > 0 && ask > bid;
}

bool InTradingHours()
{
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   if(TradingHours_Start == TradingHours_End) return true;
   if(TradingHours_Start < TradingHours_End)
      return dt.hour >= TradingHours_Start && dt.hour < TradingHours_End;
   return dt.hour >= TradingHours_Start || dt.hour < TradingHours_End;
}

//+------------------------------------------------------------------+
void AnalyzeMarketStructure(string symbol, ENUM_TIMEFRAMES tf)
{
   MqlRates htf[];
   ArraySetAsSeries(htf, true);
   if(CopyRates(symbol, tf, 0, 160, htf) < 80) { HTFBias = "NEUTRAL"; return; }

   double lastHigh = 0, prevHigh = 0, lastLow = 0, prevLow = 0;
   for(int i = 4; i < 120; i++)
   {
      bool sh = htf[i].high > htf[i-1].high && htf[i].high > htf[i+1].high && htf[i].high > htf[i-2].high && htf[i].high > htf[i+2].high;
      bool sl = htf[i].low < htf[i-1].low && htf[i].low < htf[i+1].low && htf[i].low < htf[i-2].low && htf[i].low < htf[i+2].low;
      if(sh && lastHigh == 0) lastHigh = htf[i].high; else if(sh && prevHigh == 0) prevHigh = htf[i].high;
      if(sl && lastLow == 0) lastLow = htf[i].low; else if(sl && prevLow == 0) prevLow = htf[i].low;
      if(lastHigh > 0 && prevHigh > 0 && lastLow > 0 && prevLow > 0) break;
   }
   if(lastHigh > prevHigh && lastLow > prevLow) HTFBias = "BULLISH";
   else if(lastHigh < prevHigh && lastLow < prevLow) HTFBias = "BEARISH";
   else HTFBias = "NEUTRAL";
}

OrderBlock FindOrderBlocks(int lookback = 50)
{
   OrderBlock ob;
   ob.high = 0;
   ob.low = 0;
   ob.mid = 0;
   ob.isBullish = true;
   ob.isValid = false;
   ob.barIndex = -1;
   ob.volumeAtCreation = 0;

   double atr = BufferValue(hATR, 0, 1);
   for(int i = 4; i < MathMin(lookback, ArraySize(rates) - 6); i++)
   {
      double move = rates[i-4].close - rates[i].close;
      bool bearishCandle = rates[i].close < rates[i].open;
      bool bullishCandle = rates[i].close > rates[i].open;
      if(bearishCandle && move > atr * 2.5)
      {
         ob.high = rates[i].high; ob.low = rates[i].low; ob.mid = (ob.high + ob.low) / 2.0;
         ob.isBullish = true; ob.isValid = rates[0].close >= ob.low; ob.barIndex = i; ob.volumeAtCreation = (double)rates[i].tick_volume;
         return ob;
      }
      if(bullishCandle && move < -atr * 2.5)
      {
         ob.high = rates[i].high; ob.low = rates[i].low; ob.mid = (ob.high + ob.low) / 2.0;
         ob.isBullish = false; ob.isValid = rates[0].close <= ob.high; ob.barIndex = i; ob.volumeAtCreation = (double)rates[i].tick_volume;
         return ob;
      }
   }
   return ob;
}

void MapLiquidity()
{
   double atr = BufferValue(hATR, 0, 1);
   for(int i = 5; i < 80 && i < ArraySize(rates) - 5; i++)
   {
      for(int j = i + 1; j < i + 10 && j < ArraySize(rates) - 2; j++)
      {
         if(MathAbs(rates[i].high - rates[j].high) <= atr * 0.35)
            DrawHLine("PULSAR_BSL_" + IntegerToString(i), rates[i].high, clrDeepSkyBlue, STYLE_DASH);
         if(MathAbs(rates[i].low - rates[j].low) <= atr * 0.35)
            DrawHLine("PULSAR_SSL_" + IntegerToString(i), rates[i].low, clrTomato, STYLE_DASH);
      }
   }
}

bool IsDisplacement(int bar)
{
   double body = MathAbs(rates[bar].close - rates[bar].open);
   double atr = BufferValue(hATR, 0, bar);
   return body > 2.5 * atr && FVGExists(bar);
}

bool FVGExists(int bar)
{
   if(bar + 1 >= ArraySize(rates) || bar - 1 < 0) return false;
   bool bull = rates[bar+1].high < rates[bar-1].low;
   bool bear = rates[bar+1].low > rates[bar-1].high;
   return bull || bear;
}

string DailyBias()
{
   if(HTFBias == "BULLISH" && rates[0].close < MidRange(96)) return "STRONG_BULL";
   if(HTFBias == "BULLISH") return "BULL";
   if(HTFBias == "BEARISH" && rates[0].close > MidRange(96)) return "STRONG_BEAR";
   if(HTFBias == "BEARISH") return "BEAR";
   return "NEUTRAL";
}

//+------------------------------------------------------------------+
int RunAllStrategies()
{
   StrategyVote votes[20];
   votes[0] = Strategy_Fibonacci();
   votes[1] = Strategy_Gann();
   votes[2] = Strategy_OrderBlocks();
   votes[3] = Strategy_BOS_CHOCH();
   votes[4] = Strategy_LiquidityZones();
   votes[5] = Strategy_FVG();
   votes[6] = Strategy_RSIDivergence();
   votes[7] = Strategy_EMACrossover();
   votes[8] = Strategy_VolumeProfileVWAP();
   votes[9] = Strategy_BollingerSqueeze();
   votes[10] = Strategy_MACD();
   votes[11] = Strategy_SupportResistance();
   votes[12] = Strategy_ICTKillzones();
   votes[13] = Strategy_Stochastic();
   votes[14] = Strategy_ATRTrailing();
   votes[15] = Strategy_Engulfing();
   votes[16] = Strategy_WickRejection();
   votes[17] = Strategy_PremiumDiscount();
   votes[18] = Strategy_MartingaleSafety();
   votes[19] = Strategy_MTFConfluence();

   int buyScore = 0;
   int sellScore = 0;
   for(int i = 0; i < 20; i++)
   {
      if(votes[i].direction > 0) buyScore += votes[i].score;
      if(votes[i].direction < 0) sellScore += votes[i].score;
   }
   if(buyScore > sellScore) { LastSignalDirection = 1; return buyScore; }
   if(sellScore > buyScore) { LastSignalDirection = -1; return sellScore; }
   LastSignalDirection = 0;
   return 0;
}

StrategyVote Vote(string name, int direction, int score)
{
   StrategyVote vote;
   vote.name = name;
   vote.direction = direction;
   vote.score = score;
   return vote;
}

StrategyVote Strategy_Fibonacci()
{
   double high = HighestHigh(120);
   double low = LowestLow(120);
   double range = high - low;
   double fib618 = high - range * 0.618;
   double fib786 = high - range * 0.786;
   double atr = BufferValue(hATR, 0, 1);
   if(IsNear(rates[0].close, fib618, atr) || IsNear(rates[0].close, fib786, atr))
      return Vote("Fibonacci", HTFBias == "BEARISH" ? -1 : 1, 1);
   return Vote("Fibonacci", 0, 0);
}

StrategyVote Strategy_Gann()
{
   double price = rates[0].close;
   double support = MathPow(MathSqrt(price) - 0.125, 2);
   double resistance = MathPow(MathSqrt(price) + 0.125, 2);
   double atr = BufferValue(hATR, 0, 1);
   if(VolumeSpike(1.2) && IsNear(price, support, atr)) return Vote("Gann", 1, 1);
   if(VolumeSpike(1.2) && IsNear(price, resistance, atr)) return Vote("Gann", -1, 1);
   return Vote("Gann", 0, 0);
}

StrategyVote Strategy_OrderBlocks()
{
   if(!UseSMC) return Vote("OrderBlock", 0, 0);
   OrderBlock ob = FindOrderBlocks(80);
   if(ob.isValid && rates[0].close >= ob.low && rates[0].close <= ob.high)
      return Vote("OrderBlock", ob.isBullish ? 1 : -1, 2);
   return Vote("OrderBlock", 0, 0);
}

StrategyVote Strategy_BOS_CHOCH()
{
   double swingHigh = RecentSwingHigh(60);
   double swingLow = RecentSwingLow(60);
   if(rates[0].close > swingHigh && swingHigh > 0) return Vote("BOS_CHOCH", 1, 2);
   if(rates[0].close < swingLow && swingLow > 0) return Vote("BOS_CHOCH", -1, 2);
   return Vote("BOS_CHOCH", 0, 0);
}

StrategyVote Strategy_LiquidityZones()
{
   double swingHigh = RecentSwingHigh(80);
   double swingLow = RecentSwingLow(80);
   double atr = BufferValue(hATR, 0, 1);
   if(rates[1].high > swingHigh + atr * 0.2 && rates[1].close < swingHigh) return Vote("Liquidity", -1, 2);
   if(rates[1].low < swingLow - atr * 0.2 && rates[1].close > swingLow) return Vote("Liquidity", 1, 2);
   return Vote("Liquidity", 0, 0);
}

StrategyVote Strategy_FVG()
{
   double atr = BufferValue(hATR, 0, 1);
   for(int i = 2; i < 25; i++)
   {
      if(rates[i+1].high < rates[i-1].low)
      {
         double mid = (rates[i+1].high + rates[i-1].low) / 2.0;
         if(IsNear(rates[0].close, mid, atr * 0.5)) return Vote("FVG", 1, 1);
      }
      if(rates[i+1].low > rates[i-1].high)
      {
         double mid = (rates[i+1].low + rates[i-1].high) / 2.0;
         if(IsNear(rates[0].close, mid, atr * 0.5)) return Vote("FVG", -1, 1);
      }
   }
   return Vote("FVG", 0, 0);
}

StrategyVote Strategy_RSIDivergence()
{
   double rsi = BufferValue(hRSI, 0, 1);
   if(rsi < 30 && rates[1].close > rates[2].close) return Vote("RSI", 1, 1);
   if(rsi > 70 && rates[1].close < rates[2].close) return Vote("RSI", -1, 1);
   return Vote("RSI", 0, 0);
}

StrategyVote Strategy_EMACrossover()
{
   double ema9 = BufferValue(hEMA9, 0, 1);
   double ema21 = BufferValue(hEMA21, 0, 1);
   double ema200 = BufferValue(hEMA200, 0, 1);
   double ema9Prev = BufferValue(hEMA9, 0, 2);
   double ema21Prev = BufferValue(hEMA21, 0, 2);
   if(ema9Prev <= ema21Prev && ema9 > ema21 && rates[1].close > ema200) return Vote("EMA", 1, 2);
   if(ema9Prev >= ema21Prev && ema9 < ema21 && rates[1].close < ema200) return Vote("EMA", -1, 2);
   return Vote("EMA", 0, 0);
}

StrategyVote Strategy_VolumeProfileVWAP()
{
   double poc, vah, val;
   VolumeProfile(160, poc, vah, val);
   double vwap = VWAP(96);
   double atr = BufferValue(hATR, 0, 1);
   if(IsNear(rates[0].close, val, atr) && rates[0].close > vwap) return Vote("VP_VWAP", 1, 2);
   if(IsNear(rates[0].close, vah, atr) && rates[0].close < vwap) return Vote("VP_VWAP", -1, 2);
   return Vote("VP_VWAP", 0, 0);
}

StrategyVote Strategy_BollingerSqueeze()
{
   double upper = BufferValue(hBands, 1, 1);
   double lower = BufferValue(hBands, 2, 1);
   double mid = BufferValue(hBands, 0, 1);
   double width = (upper - lower) / MathMax(mid, _Point);
   if(width < 0.04 && rates[1].close > upper) return Vote("Bollinger", 1, 1);
   if(width < 0.04 && rates[1].close < lower) return Vote("Bollinger", -1, 1);
   return Vote("Bollinger", 0, 0);
}

StrategyVote Strategy_MACD()
{
   double macd = BufferValue(hMACD, 0, 1);
   double signal = BufferValue(hMACD, 1, 1);
   double macdPrev = BufferValue(hMACD, 0, 2);
   double signalPrev = BufferValue(hMACD, 1, 2);
   if(macdPrev <= signalPrev && macd > signal && macd < 0) return Vote("MACD", 1, 1);
   if(macdPrev >= signalPrev && macd < signal && macd > 0) return Vote("MACD", -1, 1);
   return Vote("MACD", 0, 0);
}

StrategyVote Strategy_SupportResistance()
{
   double support = RecentSwingLow(80);
   double resistance = RecentSwingHigh(80);
   double atr = BufferValue(hATR, 0, 1);
   if(IsNear(rates[0].close, support, atr) && rates[0].close > rates[1].close) return Vote("SR", 1, 1);
   if(IsNear(rates[0].close, resistance, atr) && rates[0].close < rates[1].close) return Vote("SR", -1, 1);
   return Vote("SR", 0, 0);
}

StrategyVote Strategy_ICTKillzones()
{
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   bool killzone = (dt.hour >= 7 && dt.hour <= 10) || (dt.hour >= 13 && dt.hour <= 16);
   if(!killzone || !VolumeSpike(1.2)) return Vote("ICT_Killzone", 0, 0);
   if(HTFBias == "BULLISH") return Vote("ICT_Killzone", 1, 1);
   if(HTFBias == "BEARISH") return Vote("ICT_Killzone", -1, 1);
   return Vote("ICT_Killzone", 0, 0);
}

StrategyVote Strategy_Stochastic()
{
   double k = BufferValue(hStoch, 0, 1);
   double d = BufferValue(hStoch, 1, 1);
   double kPrev = BufferValue(hStoch, 0, 2);
   double dPrev = BufferValue(hStoch, 1, 2);
   if(kPrev <= dPrev && k > d && k < 25) return Vote("Stochastic", 1, 1);
   if(kPrev >= dPrev && k < d && k > 75) return Vote("Stochastic", -1, 1);
   return Vote("Stochastic", 0, 0);
}

StrategyVote Strategy_ATRTrailing()
{
   double ema21 = BufferValue(hEMA21, 0, 1);
   double adx = BufferValue(hADX, 0, 1);
   if(adx > 25 && rates[1].close > ema21) return Vote("ATR_Trail", 1, 1);
   if(adx > 25 && rates[1].close < ema21) return Vote("ATR_Trail", -1, 1);
   return Vote("ATR_Trail", 0, 0);
}

StrategyVote Strategy_Engulfing()
{
   double body1 = MathAbs(rates[1].close - rates[1].open);
   double body2 = MathAbs(rates[2].close - rates[2].open);
   bool volumeOk = rates[1].tick_volume > rates[2].tick_volume * 1.2;
   if(rates[1].open < rates[2].close && rates[1].close > rates[2].open && body1 > body2 * 1.2 && volumeOk)
      return Vote("Engulfing", 1, 1);
   if(rates[1].open > rates[2].close && rates[1].close < rates[2].open && body1 > body2 * 1.2 && volumeOk)
      return Vote("Engulfing", -1, 1);
   return Vote("Engulfing", 0, 0);
}

StrategyVote Strategy_WickRejection()
{
   double body = MathAbs(rates[1].close - rates[1].open);
   double upper = rates[1].high - MathMax(rates[1].open, rates[1].close);
   double lower = MathMin(rates[1].open, rates[1].close) - rates[1].low;
   if(lower > body * 2.0 && upper < body * 0.8) return Vote("Wick", 1, 1);
   if(upper > body * 2.0 && lower < body * 0.8) return Vote("Wick", -1, 1);
   return Vote("Wick", 0, 0);
}

StrategyVote Strategy_PremiumDiscount()
{
   double mid = MidRange(120);
   if(rates[0].close < mid && HTFBias != "BEARISH") return Vote("PremiumDiscount", 1, 1);
   if(rates[0].close > mid && HTFBias != "BULLISH") return Vote("PremiumDiscount", -1, 1);
   return Vote("PremiumDiscount", 0, 0);
}

StrategyVote Strategy_MartingaleSafety()
{
   double dd = DrawdownPercent();
   if(dd > 10.0)
   {
      AlgoTradingEnabled = false;
      Print("Martingale safety module disabled trading because drawdown > 10%.");
   }
   return Vote("MartingaleSafety", 0, 0);
}

StrategyVote Strategy_MTFConfluence()
{
   int score = 0;
   int direction = 0;
   double rsi = BufferValue(hRSI, 0, 1);
   if(HTFBias == "BULLISH") { direction = 1; score += 3; }
   if(HTFBias == "BEARISH") { direction = -1; score += 3; }
   if(direction == 1 && rsi > 50) score += 1;
   if(direction == -1 && rsi < 50) score += 1;
   if(VolumeSpike(1.3)) score += 1;
   if(FVGExists(2)) score += 1;
   if(score >= 4) return Vote("MTF", direction, MathMin(score, 4));
   return Vote("MTF", 0, 0);
}

//+------------------------------------------------------------------+
int GetMLPrediction()
{
   double rsi = BufferValue(hRSI, 0, 1);
   double macdHist = BufferValue(hMACD, 0, 1) - BufferValue(hMACD, 1, 1);
   double ema9 = BufferValue(hEMA9, 0, 1);
   double ema21 = BufferValue(hEMA21, 0, 1);
   double adx = BufferValue(hADX, 0, 1);
   double volumeRatio = VolumeRatio(20);
   double z = 0.0;
   z += (rsi - 50.0) / 50.0;
   z += macdHist > 0 ? 0.7 : -0.7;
   z += ema9 > ema21 ? 0.8 : -0.8;
   z += HTFBias == "BULLISH" ? 1.0 : HTFBias == "BEARISH" ? -1.0 : 0.0;
   z += adx > 25 ? (ema9 > ema21 ? 0.4 : -0.4) : 0.0;
   z += volumeRatio > 1.3 ? (rates[1].close > rates[1].open ? 0.4 : -0.4) : 0.0;
   if(z > 1.0) { LastMLSignal = "BULLISH"; return 1; }
   if(z < -1.0) { LastMLSignal = "BEARISH"; return -1; }
   LastMLSignal = "NEUTRAL";
   return 0;
}

//+------------------------------------------------------------------+
bool RiskCheck()
{
   PeakBalance = MathMax(PeakBalance, AccountInfoDouble(ACCOUNT_BALANCE));
   double dd = DrawdownPercent();
   if(dd > 10.0)
   {
      AlgoTradingEnabled = false;
      Alert("Drawdown > 10%. Trading paused.");
      return false;
   }
   if(dd > MaxDrawdown)
   {
      CloseAllPositions();
      Alert("Max drawdown reached. All positions closed.");
      return false;
   }
   double openRisk = OpenExposureRisk();
   double maxDailyRisk = AccountInfoDouble(ACCOUNT_BALANCE) * 0.05;
   if(openRisk >= maxDailyRisk)
   {
      AlgoTradingEnabled = false;
      Alert("Daily risk limit reached. Trading halted.");
      return false;
   }
   return true;
}

double DrawdownPercent()
{
   if(PeakBalance <= 0.0) PeakBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   return (PeakBalance - AccountInfoDouble(ACCOUNT_EQUITY)) / PeakBalance * 100.0;
}

double OpenExposureRisk()
{
   double risk = 0.0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(!PositionSelectByTicket(ticket)) continue;
      if(PositionGetInteger(POSITION_MAGIC) != MagicNumber) continue;
      string symbol = PositionGetString(POSITION_SYMBOL);
      double sl = PositionGetDouble(POSITION_SL);
      double open = PositionGetDouble(POSITION_PRICE_OPEN);
      double volume = PositionGetDouble(POSITION_VOLUME);
      if(sl <= 0) continue;
      double tickValue = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_VALUE);
      double tickSize = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_SIZE);
      double points = MathAbs(open - sl) / MathMax(tickSize, _Point);
      risk += points * tickValue * volume;
   }
   return risk;
}

void ExecuteTrade(int direction)
{
   if(LastTradeBarTime == rates[0].time) return;
   if(CountOpenTrades() >= MaxOpenPositions) return;
   if(SpreadTooWide()) return;

   double atr = BufferValue(hATR, 0, 1);
   double slDistance = MathMax(atr * 1.5, _Point * 100);
   double tpDistance = slDistance * MinRR;
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double entry = direction > 0 ? ask : bid;
   double sl = direction > 0 ? entry - slDistance : entry + slDistance;
   double tp = direction > 0 ? entry + tpDistance : entry - tpDistance;
   double rr = MathAbs(tp - entry) / MathMax(MathAbs(entry - sl), _Point);
   if(rr < MinRR) return;

   double lot = CalculateLotSize(slDistance / _Point);
   if(lot <= 0) return;

   bool ok = false;
   if(direction > 0)
      ok = trade.Buy(lot, _Symbol, ask, sl, tp, "Pulsar score " + IntegerToString(LastSignalScore));
   else
      ok = trade.Sell(lot, _Symbol, bid, sl, tp, "Pulsar score " + IntegerToString(LastSignalScore));

   if(!ok)
   {
      Print("OrderSend failed. Retcode=", trade.ResultRetcode(), " ", trade.ResultRetcodeDescription());
      return;
   }
   LastTradeBarTime = rates[0].time;
   LogTrade(direction, lot, sl, tp, LastSignalScore);
}

double CalculateLotSize(double stopLossPoints)
{
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double riskMoney = balance * SafeRiskPercent() / 100.0;
   double tickValue = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSize = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double pointValue = tickValue * (_Point / MathMax(tickSize, _Point));
   double lot = riskMoney / MathMax(stopLossPoints * pointValue, 0.01);
   double minLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   lot = MathMax(minLot, MathMin(maxLot, lot));
   lot = MathFloor(lot / step) * step;
   return NormalizeDouble(lot, 2);
}

void ManageOpenTrades()
{
   double atr = BufferValue(hATR, 0, 1);
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(!PositionSelectByTicket(ticket)) continue;
      if(PositionGetInteger(POSITION_MAGIC) != MagicNumber) continue;
      string symbol = PositionGetString(POSITION_SYMBOL);
      long type = PositionGetInteger(POSITION_TYPE);
      double sl = PositionGetDouble(POSITION_SL);
      double tp = PositionGetDouble(POSITION_TP);
      double bid = SymbolInfoDouble(symbol, SYMBOL_BID);
      double ask = SymbolInfoDouble(symbol, SYMBOL_ASK);
      if(type == POSITION_TYPE_BUY)
      {
         double newSl = bid - atr * 2.5;
         if(newSl > sl) trade.PositionModify(ticket, newSl, tp);
      }
      if(type == POSITION_TYPE_SELL)
      {
         double newSl = ask + atr * 2.5;
         if(sl == 0 || newSl < sl) trade.PositionModify(ticket, newSl, tp);
      }
   }
}

void CloseAllPositions()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(!PositionSelectByTicket(ticket)) continue;
      if(PositionGetInteger(POSITION_MAGIC) != MagicNumber) continue;
      if(!trade.PositionClose(ticket))
         Print("Close failed ticket=", ticket, " retcode=", trade.ResultRetcodeDescription());
   }
}

int CountOpenTrades()
{
   int count = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(PositionSelectByTicket(ticket) && PositionGetInteger(POSITION_MAGIC) == MagicNumber)
         count++;
   }
   return count;
}

bool SpreadTooWide()
{
   double spread = SymbolInfoDouble(_Symbol, SYMBOL_ASK) - SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double atr = BufferValue(hATR, 0, 1);
   return spread > atr * 0.25;
}

void LogTrade(int direction, double lot, double sl, double tp, int score)
{
   int handle = FileOpen("Pulsar_trades.csv", FILE_READ|FILE_WRITE|FILE_CSV|FILE_ANSI);
   if(handle == INVALID_HANDLE)
   {
      Print("CSV log open failed: ", GetLastError());
      return;
   }
   FileSeek(handle, 0, SEEK_END);
   FileWrite(handle, TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS), _Symbol, direction > 0 ? "BUY" : "SELL", lot, sl, tp, score);
   FileClose(handle);
}

//+------------------------------------------------------------------+
double HighestHigh(int lookback)
{
   double value = rates[1].high;
   for(int i = 1; i < MathMin(lookback, ArraySize(rates)); i++) value = MathMax(value, rates[i].high);
   return value;
}

double LowestLow(int lookback)
{
   double value = rates[1].low;
   for(int i = 1; i < MathMin(lookback, ArraySize(rates)); i++) value = MathMin(value, rates[i].low);
   return value;
}

double MidRange(int lookback)
{
   return (HighestHigh(lookback) + LowestLow(lookback)) / 2.0;
}

double RecentSwingHigh(int lookback)
{
   for(int i = 3; i < MathMin(lookback, ArraySize(rates) - 3); i++)
      if(rates[i].high > rates[i-1].high && rates[i].high > rates[i+1].high && rates[i].high > rates[i-2].high && rates[i].high > rates[i+2].high)
         return rates[i].high;
   return HighestHigh(lookback);
}

double RecentSwingLow(int lookback)
{
   for(int i = 3; i < MathMin(lookback, ArraySize(rates) - 3); i++)
      if(rates[i].low < rates[i-1].low && rates[i].low < rates[i+1].low && rates[i].low < rates[i-2].low && rates[i].low < rates[i+2].low)
         return rates[i].low;
   return LowestLow(lookback);
}

bool IsNear(double price, double level, double tolerance)
{
   return level > 0 && MathAbs(price - level) <= tolerance;
}

double VolumeRatio(int period)
{
   double avg = 0;
   int count = MathMin(period, ArraySize(rates) - 2);
   for(int i = 2; i < count + 2; i++) avg += (double)rates[i].tick_volume;
   avg /= MathMax(count, 1);
   return (double)rates[1].tick_volume / MathMax(avg, 1.0);
}

bool VolumeSpike(double multiplier)
{
   return VolumeRatio(20) >= multiplier;
}

double VWAP(int lookback)
{
   double pv = 0;
   double vol = 0;
   for(int i = 1; i < MathMin(lookback, ArraySize(rates)); i++)
   {
      double typical = (rates[i].high + rates[i].low + rates[i].close) / 3.0;
      double v = (double)rates[i].tick_volume;
      pv += typical * v;
      vol += v;
   }
   return pv / MathMax(vol, 1.0);
}

void VolumeProfile(int lookback, double &poc, double &vah, double &val)
{
   double high = HighestHigh(lookback);
   double low = LowestLow(lookback);
   int bins = 24;
   double hist[];
   ArrayResize(hist, bins);
   ArrayInitialize(hist, 0.0);
   double step = (high - low) / MathMax(bins, 1);
   if(step <= 0) { poc = rates[0].close; vah = high; val = low; return; }
   for(int i = 1; i < MathMin(lookback, ArraySize(rates)); i++)
   {
      double typical = (rates[i].high + rates[i].low + rates[i].close) / 3.0;
      int idx = (int)MathFloor((typical - low) / step);
      idx = MathMax(0, MathMin(bins - 1, idx));
      hist[idx] += (double)rates[i].tick_volume;
   }
   int maxIdx = 0;
   for(int i = 1; i < bins; i++) if(hist[i] > hist[maxIdx]) maxIdx = i;
   poc = low + step * (maxIdx + 0.5);
   val = low + step * MathMax(0, maxIdx - 4);
   vah = low + step * MathMin(bins - 1, maxIdx + 4);
}

//+------------------------------------------------------------------+
void CreateChartPanel()
{
   ObjectCreate(0, "PULSAR_PANEL", OBJ_RECTANGLE_LABEL, 0, 0, 0);
   ObjectSetInteger(0, "PULSAR_PANEL", OBJPROP_XDISTANCE, 10);
   ObjectSetInteger(0, "PULSAR_PANEL", OBJPROP_YDISTANCE, 20);
   ObjectSetInteger(0, "PULSAR_PANEL", OBJPROP_XSIZE, 310);
   ObjectSetInteger(0, "PULSAR_PANEL", OBJPROP_YSIZE, 185);
   ObjectSetInteger(0, "PULSAR_PANEL", OBJPROP_BGCOLOR, clrBlack);
   ObjectSetInteger(0, "PULSAR_PANEL", OBJPROP_COLOR, clrDimGray);

   ObjectCreate(0, "PULSAR_TEXT", OBJ_LABEL, 0, 0, 0);
   ObjectSetInteger(0, "PULSAR_TEXT", OBJPROP_XDISTANCE, 20);
   ObjectSetInteger(0, "PULSAR_TEXT", OBJPROP_YDISTANCE, 30);
   ObjectSetInteger(0, "PULSAR_TEXT", OBJPROP_COLOR, clrWhite);
   ObjectSetInteger(0, "PULSAR_TEXT", OBJPROP_FONTSIZE, 9);

   CreateButton("PULSAR_PAUSE", "PAUSE", 20, 160, 80, 28);
   CreateButton("PULSAR_CLOSE_ALL", "CLOSE ALL", 110, 160, 95, 28);
}

void CreateButton(string name, string text, int x, int y, int w, int h)
{
   ObjectCreate(0, name, OBJ_BUTTON, 0, 0, 0);
   ObjectSetInteger(0, name, OBJPROP_XDISTANCE, x);
   ObjectSetInteger(0, name, OBJPROP_YDISTANCE, y);
   ObjectSetInteger(0, name, OBJPROP_XSIZE, w);
   ObjectSetInteger(0, name, OBJPROP_YSIZE, h);
   ObjectSetString(0, name, OBJPROP_TEXT, text);
   ObjectSetInteger(0, name, OBJPROP_COLOR, clrWhite);
   ObjectSetInteger(0, name, OBJPROP_BGCOLOR, clrDarkSlateGray);
}

void UpdateDashboardPanel()
{
   string status = AlgoTradingEnabled ? "LIVE" : "PAUSED";
   string text = "Pulsar AlgoBot v1 [" + status + "]\n";
   text += "Balance: " + DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE), 2) + "\n";
   text += "Equity:  " + DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY), 2) + "\n";
   text += "Drawdown: " + DoubleToString(DrawdownPercent(), 2) + "%\n";
   text += "Risk Used: " + DoubleToString(OpenExposureRisk() / MathMax(AccountInfoDouble(ACCOUNT_BALANCE), 1) * 100.0, 2) + "% / 5.0%\n";
   text += "Open Trades: " + IntegerToString(CountOpenTrades()) + "\n";
   text += "Signal Score: " + IntegerToString(LastSignalScore) + "/15\n";
   text += "ML Signal: " + LastMLSignal + "\n";
   text += "HTF Bias: " + HTFBias + "\n";
   ObjectSetString(0, "PULSAR_TEXT", OBJPROP_TEXT, text);
}

void DrawHLine(string name, double price, color clr, ENUM_LINE_STYLE style)
{
   if(ObjectFind(0, name) < 0)
      ObjectCreate(0, name, OBJ_HLINE, 0, 0, price);
   ObjectSetDouble(0, name, OBJPROP_PRICE, price);
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, name, OBJPROP_STYLE, style);
}
