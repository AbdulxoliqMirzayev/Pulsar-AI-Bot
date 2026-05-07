#ifndef AB_STRATEGIES_MQH
#define AB_STRATEGIES_MQH

int g_StrategyDirection = 0;
int g_BuyScore = 0;
int g_SellScore = 0;

bool InitAllIndicators()
{
   g_RSI_handle = iRSI(_Symbol, PERIOD_H1, 14, PRICE_CLOSE);
   g_MACD_handle = iMACD(_Symbol, PERIOD_H1, 12, 26, 9, PRICE_CLOSE);
   g_BB_handle = iBands(_Symbol, PERIOD_H1, 20, 0, 2.0, PRICE_CLOSE);
   g_ATR_handle = iATR(_Symbol, PERIOD_H1, 14);
   g_EMA9_handle = iMA(_Symbol, PERIOD_H1, 9, 0, MODE_EMA, PRICE_CLOSE);
   g_EMA21_handle = iMA(_Symbol, PERIOD_H1, 21, 0, MODE_EMA, PRICE_CLOSE);
   g_EMA50_handle = iMA(_Symbol, PERIOD_H1, 50, 0, MODE_EMA, PRICE_CLOSE);
   g_EMA200_handle = iMA(_Symbol, PERIOD_H1, 200, 0, MODE_EMA, PRICE_CLOSE);
   g_Stoch_handle = iStochastic(_Symbol, PERIOD_H1, 5, 3, 3, MODE_SMA, STO_LOWHIGH);
   g_ADX_handle = iADX(_Symbol, PERIOD_H1, 14);
   g_CCI_handle = iCCI(_Symbol, PERIOD_H1, 14, PRICE_TYPICAL);
   g_WPR_handle = iWPR(_Symbol, PERIOD_H1, 14);
   g_SAR_handle = iSAR(_Symbol, PERIOD_H1, 0.02, 0.2);
   return g_RSI_handle != INVALID_HANDLE && g_MACD_handle != INVALID_HANDLE &&
          g_BB_handle != INVALID_HANDLE && g_ATR_handle != INVALID_HANDLE &&
          g_EMA9_handle != INVALID_HANDLE && g_EMA21_handle != INVALID_HANDLE &&
          g_EMA200_handle != INVALID_HANDLE && g_Stoch_handle != INVALID_HANDLE &&
          g_ADX_handle != INVALID_HANDLE;
}

void ReleaseAllIndicators()
{
   int handles[13];
   handles[0] = g_RSI_handle;
   handles[1] = g_MACD_handle;
   handles[2] = g_BB_handle;
   handles[3] = g_ATR_handle;
   handles[4] = g_EMA9_handle;
   handles[5] = g_EMA21_handle;
   handles[6] = g_EMA50_handle;
   handles[7] = g_EMA200_handle;
   handles[8] = g_Stoch_handle;
   handles[9] = g_ADX_handle;
   handles[10] = g_CCI_handle;
   handles[11] = g_WPR_handle;
   handles[12] = g_SAR_handle;
   for(int i = 0; i < 13; i++)
      if(handles[i] != INVALID_HANDLE) IndicatorRelease(handles[i]);
}

void UpdateAllIndicators()
{
   double tmp[];
   CopyBuffer(g_RSI_handle, 0, 1, 1, tmp);
   CopyBuffer(g_MACD_handle, 0, 1, 1, tmp);
   CopyBuffer(g_ATR_handle, 0, 1, 1, tmp);
}

double IndicatorValue(int handle, int buffer, int shift)
{
   double data[];
   ArraySetAsSeries(data, true);
   if(CopyBuffer(handle, buffer, shift, 1, data) <= 0) return 0.0;
   return data[0];
}

void AddVote(int direction, int score)
{
   if(direction > 0) g_BuyScore += score;
   if(direction < 0) g_SellScore += score;
}

int DirectionFromBias()
{
   if(g_DailyBias == "BULL" || g_DailyBias == "STRONG_BULL") return 1;
   if(g_DailyBias == "BEAR" || g_DailyBias == "STRONG_BEAR") return -1;
   return 0;
}

int RunAllStrategies(string symbol)
{
   g_BuyScore = 0;
   g_SellScore = 0;
   int score = 0;
   int s = 0;

   if(UseStrategy_EMA)        { s = Strategy_EMA_Score(symbol);        score += s; AddVote(Strategy_EMA_Direction(symbol), s); }
   if(UseStrategy_Fib)        { s = Strategy_Fibonacci_Score(symbol);  score += s; AddVote(DirectionFromBias(), s); }
   if(UseStrategy_Gann)       { s = Strategy_Gann_Score(symbol);       score += s; AddVote(Strategy_KeyLevel_Direction(symbol), s); }
   if(UseStrategy_OB)         { s = Strategy_OrderBlock_Score(symbol); score += s; AddVote(Strategy_OrderBlock_Direction(symbol), s); }
   if(UseStrategy_BOS_CHoCH)  { s = Strategy_BOS_CHoCH_Score(symbol);  score += s; AddVote(Strategy_Structure_Direction(symbol), s); }
   if(UseStrategy_Liquidity)  { s = Strategy_Liquidity_Score(symbol);  score += s; AddVote(Strategy_Liquidity_Direction(symbol), s); }
   if(UseStrategy_FVG)        { s = Strategy_FVG_Score(symbol);        score += s; AddVote(Strategy_FVG_Direction(symbol), s); }
   if(UseStrategy_RSI)        { s = Strategy_RSI_Score(symbol);        score += s; AddVote(Strategy_RSI_Direction(symbol), s); }
   if(UseStrategy_VWAP)       { s = Strategy_VWAP_Score(symbol);       score += s; AddVote(Strategy_VWAP_Direction(symbol), s); }
   if(UseStrategy_BB)         { s = Strategy_BollingerBands_Score(symbol); score += s; AddVote(Strategy_BB_Direction(symbol), s); }
   if(UseStrategy_MACD)       { s = Strategy_MACD_Score(symbol);       score += s; AddVote(Strategy_MACD_Direction(symbol), s); }
   if(UseStrategy_SR)         { s = Strategy_SupportResistance_Score(symbol); score += s; AddVote(Strategy_KeyLevel_Direction(symbol), s); }
   if(UseStrategy_ICT)        { s = Strategy_ICT_Killzone_Score(symbol); score += s; AddVote(DirectionFromBias(), s); }
   if(UseStrategy_Stoch)      { s = Strategy_Stochastic_Score(symbol); score += s; AddVote(Strategy_Stoch_Direction(symbol), s); }
   if(UseStrategy_ATR)        { s = Strategy_ATR_Score(symbol);        score += s; AddVote(Strategy_EMA_Direction(symbol), s); }
   if(UseStrategy_Engulf)     { s = Strategy_Engulfing_Score(symbol);  score += s; AddVote(Strategy_Engulfing_Direction(symbol), s); }
   if(UseStrategy_Wick)       { s = Strategy_WickRejection_Score(symbol); score += s; AddVote(Strategy_Wick_Direction(symbol), s); }
   if(UseStrategy_Premium)    { s = Strategy_PremiumDiscount_Score(symbol); score += s; AddVote(Strategy_Premium_Direction(symbol), s); }
   if(UseStrategy_Martingale) { s = Strategy_Martingale_Score(symbol); score += s; AddVote(Strategy_KeyLevel_Direction(symbol), s); }
   if(UseStrategy_MTF)        { s = Strategy_MultiTimeframe_Score(symbol); score += s; AddVote(Strategy_MTF_Direction(symbol), s); }

   if(g_BuyScore > g_SellScore) g_StrategyDirection = 1;
   else if(g_SellScore > g_BuyScore) g_StrategyDirection = -1;
   else g_StrategyDirection = 0;
   return score;
}

int DetermineDirection()
{
   if(g_StrategyDirection != 0) return g_StrategyDirection;
   if(g_ML_Signal != 0) return g_ML_Signal;
   return DirectionFromBias();
}

int Strategy_Fibonacci_Score(string symbol)
{
   double high = FindSwingHigh(symbol, PERIOD_H1, 80);
   double low = FindSwingLow(symbol, PERIOD_H1, 80);
   double close = iClose(symbol, PERIOD_H1, 1);
   double range = high - low;
   if(range <= 0.0) return 0;
   double oteHigh = high - range * 0.62;
   double oteLow = high - range * 0.79;
   double fib618 = high - range * 0.618;
   double fib786 = high - range * 0.786;
   double pip = PipSize(symbol);
   if(close >= oteLow && close <= oteHigh) return 3;
   if(MathAbs(close - fib618) < 5.0 * pip) return 2;
   if(MathAbs(close - fib786) < 5.0 * pip) return 1;
   return 0;
}

int Strategy_Gann_Score(string symbol)
{
   double price = iClose(symbol, PERIOD_H1, 1);
   if(price <= 0.0) return 0;
   double root = MathSqrt(price);
   double levels[4];
   levels[0] = MathPow(root + 0.5, 2.0);
   levels[1] = MathPow(root + 1.0, 2.0);
   levels[2] = MathPow(root - 0.5, 2.0);
   levels[3] = MathPow(root - 1.0, 2.0);
   double tolerance = MathMax(10.0 * PipSize(symbol), price * 0.0005);
   for(int i = 0; i < 4; i++)
      if(MathAbs(price - levels[i]) <= tolerance) return i == 0 || i == 2 ? 2 : 1;
   return 0;
}

int Strategy_OrderBlock_Score(string symbol)
{
   OrderBlock ob = FindNearestOrderBlock(symbol, PERIOD_H1, OB_Lookback);
   if(!ob.isValid) return 0;
   double close = iClose(symbol, PERIOD_H1, 1);
   if(close >= ob.low && close <= ob.high && IsVolumeConfirmed(symbol, PERIOD_H1)) return 3;
   if(MathAbs(close - ob.mid) <= (ob.high - ob.low) * 0.75) return 2;
   return 0;
}

int Strategy_OrderBlock_Direction(string symbol)
{
   OrderBlock ob = FindNearestOrderBlock(symbol, PERIOD_H1, OB_Lookback);
   if(!ob.isValid) return 0;
   return ob.isBullish ? 1 : -1;
}

int Strategy_BOS_CHoCH_Score(string symbol)
{
   int choch = DetectCHoCH(symbol, PERIOD_H1);
   if(choch != 0) return 3;
   if(DetectBOS(symbol, PERIOD_H1)) return 2;
   return 0;
}

int Strategy_Structure_Direction(string symbol)
{
   int choch = DetectCHoCH(symbol, PERIOD_H1);
   if(choch != 0) return choch;
   double close = iClose(symbol, PERIOD_H1, 1);
   if(close > FindSwingHigh(symbol, PERIOD_H1, 80)) return 1;
   if(close < FindSwingLow(symbol, PERIOD_H1, 80)) return -1;
   return 0;
}

int Strategy_Liquidity_Score(string symbol)
{
   bool bsl = DetectLiquiditySweep(symbol, PERIOD_H1, true);
   bool ssl = DetectLiquiditySweep(symbol, PERIOD_H1, false);
   if(bsl || ssl) return HasReversalCandle(symbol, PERIOD_H1, 1) ? 3 : 2;
   return 0;
}

int Strategy_Liquidity_Direction(string symbol)
{
   if(DetectLiquiditySweep(symbol, PERIOD_H1, true)) return -1;
   if(DetectLiquiditySweep(symbol, PERIOD_H1, false)) return 1;
   return 0;
}

int Strategy_FVG_Score(string symbol)
{
   FairValueGap fvg = FindNearestFVG(symbol, PERIOD_H1, 30);
   if(!fvg.isValid) return 0;
   double close = iClose(symbol, PERIOD_H1, 1);
   if(MathAbs(close - fvg.mid) < 5.0 * PipSize(symbol)) return 2;
   if(close >= fvg.bottom && close <= fvg.top) return 1;
   return 0;
}

int Strategy_FVG_Direction(string symbol)
{
   FairValueGap fvg = FindNearestFVG(symbol, PERIOD_H1, 30);
   if(!fvg.isValid) return 0;
   return fvg.isBullish ? 1 : -1;
}

bool DetectRSIDivergence(string symbol, ENUM_TIMEFRAMES tf, bool bullish)
{
   int handle = iRSI(symbol, tf, 14, PRICE_CLOSE);
   if(handle == INVALID_HANDLE) return false;
   double rsi[];
   ArraySetAsSeries(rsi, true);
   bool result = false;
   if(CopyBuffer(handle, 0, 1, 80, rsi) >= 40)
   {
      int a = -1, b = -1;
      for(int i = 4; i < 70; i++)
      {
         bool swing = bullish ? IsSwingLow(symbol, tf, i) : IsSwingHigh(symbol, tf, i);
         if(swing)
         {
            if(a < 0) a = i;
            else { b = i; break; }
         }
      }
      if(a > 0 && b > 0)
      {
         if(bullish) result = iLow(symbol, tf, a) < iLow(symbol, tf, b) && rsi[a - 1] > rsi[b - 1];
         else result = iHigh(symbol, tf, a) > iHigh(symbol, tf, b) && rsi[a - 1] < rsi[b - 1];
      }
   }
   IndicatorRelease(handle);
   return result;
}

int Strategy_RSI_Score(string symbol)
{
   double rsi = IndicatorValue(g_RSI_handle, 0, 1);
   bool bullDiv = DetectRSIDivergence(symbol, PERIOD_H1, true);
   bool bearDiv = DetectRSIDivergence(symbol, PERIOD_H1, false);
   if((bullDiv && rsi < 35.0) || (bearDiv && rsi > 65.0)) return 3;
   if(bullDiv || bearDiv) return 2;
   if(rsi < 30.0 || rsi > 70.0) return 1;
   return 0;
}

int Strategy_RSI_Direction(string symbol)
{
   double rsi = IndicatorValue(g_RSI_handle, 0, 1);
   if(DetectRSIDivergence(symbol, PERIOD_H1, true) || rsi < 30.0) return 1;
   if(DetectRSIDivergence(symbol, PERIOD_H1, false) || rsi > 70.0) return -1;
   return 0;
}

int Strategy_EMA_Score(string symbol)
{
   double ema9 = IndicatorValue(g_EMA9_handle, 0, 1);
   double ema21 = IndicatorValue(g_EMA21_handle, 0, 1);
   double ema200 = IndicatorValue(g_EMA200_handle, 0, 1);
   double ema9p = IndicatorValue(g_EMA9_handle, 0, 2);
   double ema21p = IndicatorValue(g_EMA21_handle, 0, 2);
   bool bull = ema9 > ema21 && ema21 > ema200;
   bool bear = ema9 < ema21 && ema21 < ema200;
   bool cross = (ema9p <= ema21p && ema9 > ema21) || (ema9p >= ema21p && ema9 < ema21);
   if((bull || bear) && cross) return 3;
   if(bull || bear) return 2;
   return 0;
}

int Strategy_EMA_Direction(string symbol)
{
   double ema9 = IndicatorValue(g_EMA9_handle, 0, 1);
   double ema21 = IndicatorValue(g_EMA21_handle, 0, 1);
   double ema200 = IndicatorValue(g_EMA200_handle, 0, 1);
   if(ema9 > ema21 && iClose(symbol, PERIOD_H1, 1) > ema200) return 1;
   if(ema9 < ema21 && iClose(symbol, PERIOD_H1, 1) < ema200) return -1;
   return 0;
}

double CalculateVWAP(string symbol, ENUM_TIMEFRAMES tf)
{
   double pv = 0.0, volSum = 0.0;
   for(int i = 1; i <= 48; i++)
   {
      double typical = (iHigh(symbol, tf, i) + iLow(symbol, tf, i) + iClose(symbol, tf, i)) / 3.0;
      double vol = (double)iVolume(symbol, tf, i);
      pv += typical * vol;
      volSum += vol;
   }
   return pv / MathMax(volSum, 1.0);
}

double CalculateVWAP_StdDev(string symbol, ENUM_TIMEFRAMES tf)
{
   double vwap = CalculateVWAP(symbol, tf);
   double total = 0.0;
   for(int i = 1; i <= 48; i++)
   {
      double typical = (iHigh(symbol, tf, i) + iLow(symbol, tf, i) + iClose(symbol, tf, i)) / 3.0;
      total += MathPow(typical - vwap, 2.0);
   }
   return MathSqrt(total / 48.0);
}

int Strategy_VWAP_Score(string symbol)
{
   double vwap = CalculateVWAP(symbol, PERIOD_H1);
   double sd = CalculateVWAP_StdDev(symbol, PERIOD_H1);
   double close = iClose(symbol, PERIOD_H1, 1);
   bool volSpike = IsVolumeConfirmed(symbol, PERIOD_H1);
   if((close <= vwap - 2.0 * sd || close >= vwap + 2.0 * sd) && volSpike) return 2;
   if(MathAbs(close - vwap) <= sd * 0.25) return 1;
   return 0;
}

int Strategy_VWAP_Direction(string symbol)
{
   double vwap = CalculateVWAP(symbol, PERIOD_H1);
   double sd = CalculateVWAP_StdDev(symbol, PERIOD_H1);
   double close = iClose(symbol, PERIOD_H1, 1);
   if(close <= vwap - 2.0 * sd) return 1;
   if(close >= vwap + 2.0 * sd) return -1;
   if(close > vwap) return 1;
   if(close < vwap) return -1;
   return 0;
}

int Strategy_BollingerBands_Score(string symbol)
{
   double upper = IndicatorValue(g_BB_handle, 1, 1);
   double middle = IndicatorValue(g_BB_handle, 0, 1);
   double lower = IndicatorValue(g_BB_handle, 2, 1);
   double close = iClose(symbol, PERIOD_H1, 1);
   if(middle == 0.0 || upper == lower) return 0;
   double bw = (upper - lower) / middle * 100.0;
   double percentB = (close - lower) / (upper - lower);
   if(bw < 0.5 && (close > upper || close < lower)) return 3;
   if(percentB < 0.05 || percentB > 0.95) return 2;
   if(MathAbs(percentB - 0.5) < 0.05) return 1;
   return 0;
}

int Strategy_BB_Direction(string symbol)
{
   double upper = IndicatorValue(g_BB_handle, 1, 1);
   double lower = IndicatorValue(g_BB_handle, 2, 1);
   double close = iClose(symbol, PERIOD_H1, 1);
   if(close > upper) return 1;
   if(close < lower) return -1;
   if(close <= lower + (upper - lower) * 0.1) return 1;
   if(close >= upper - (upper - lower) * 0.1) return -1;
   return 0;
}

int Strategy_MACD_Score(string symbol)
{
   double main = IndicatorValue(g_MACD_handle, 0, 1);
   double sig = IndicatorValue(g_MACD_handle, 1, 1);
   double mainP = IndicatorValue(g_MACD_handle, 0, 2);
   double sigP = IndicatorValue(g_MACD_handle, 1, 2);
   bool cross = (mainP <= sigP && main > sig) || (mainP >= sigP && main < sig);
   if(cross && MathAbs(main) < MathAbs(main - sig) * 2.0) return 3;
   if(cross) return 2;
   if(MathAbs(main - sig) > MathAbs(mainP - sigP)) return 1;
   return 0;
}

int Strategy_MACD_Direction(string symbol)
{
   double main = IndicatorValue(g_MACD_handle, 0, 1);
   double sig = IndicatorValue(g_MACD_handle, 1, 1);
   if(main > sig) return 1;
   if(main < sig) return -1;
   return 0;
}

void CalculatePivots(string symbol, double &pivots[])
{
   ArrayResize(pivots, 7);
   double h = iHigh(symbol, PERIOD_D1, 1);
   double l = iLow(symbol, PERIOD_D1, 1);
   double c = iClose(symbol, PERIOD_D1, 1);
   double p = (h + l + c) / 3.0;
   pivots[0] = p;
   pivots[1] = 2.0 * p - l;
   pivots[2] = p + (h - l);
   pivots[3] = pivots[1] + (h - l);
   pivots[4] = 2.0 * p - h;
   pivots[5] = p - (h - l);
   pivots[6] = pivots[4] - (h - l);
}

bool IsNearRoundNumber(double price, double tolerance)
{
   double step = price > 100.0 ? 1.0 : 0.005;
   double rounded = MathRound(price / step) * step;
   return MathAbs(price - rounded) <= tolerance;
}

int Strategy_SupportResistance_Score(string symbol)
{
   double pivots[];
   CalculatePivots(symbol, pivots);
   double close = iClose(symbol, PERIOD_H1, 1);
   double tolerance = 10.0 * PipSize(symbol);
   for(int i = 0; i < 7; i++)
      if(MathAbs(close - pivots[i]) < tolerance) return 2;
   if(IsNearRoundNumber(close, 5.0 * PipSize(symbol))) return 1;
   return 0;
}

int Strategy_KeyLevel_Direction(string symbol)
{
   double close = iClose(symbol, PERIOD_H1, 1);
   double prev = iClose(symbol, PERIOD_H1, 2);
   double support = FindSwingLow(symbol, PERIOD_H1, 80);
   double resistance = FindSwingHigh(symbol, PERIOD_H1, 80);
   double tol = 10.0 * PipSize(symbol);
   if(MathAbs(close - support) < tol && close > prev) return 1;
   if(MathAbs(close - resistance) < tol && close < prev) return -1;
   return DirectionFromBias();
}

int Strategy_ICT_Killzone_Score(string symbol)
{
   if(!IsInKillzone()) return 0;
   if(IsAsianRangeSwept(symbol) && DirectionFromBias() != 0) return 3;
   return 2;
}

int Strategy_Stochastic_Score(string symbol)
{
   double k0 = IndicatorValue(g_Stoch_handle, 0, 1);
   double d0 = IndicatorValue(g_Stoch_handle, 1, 1);
   double k1 = IndicatorValue(g_Stoch_handle, 0, 2);
   double d1 = IndicatorValue(g_Stoch_handle, 1, 2);
   if(k1 < d1 && k0 > d0 && k0 < 20.0) return 2;
   if(k1 > d1 && k0 < d0 && k0 > 80.0) return 2;
   if(k0 < 20.0 || k0 > 80.0) return 1;
   return 0;
}

int Strategy_Stoch_Direction(string symbol)
{
   double k = IndicatorValue(g_Stoch_handle, 0, 1);
   double d = IndicatorValue(g_Stoch_handle, 1, 1);
   if(k < 25.0 && k > d) return 1;
   if(k > 75.0 && k < d) return -1;
   return 0;
}

int Strategy_ATR_Score(string symbol)
{
   double atrPips = IndicatorValue(g_ATR_handle, 0, 1) / PipSize(symbol);
   if(atrPips >= 8.0 && atrPips <= 35.0) return 1;
   if(atrPips > 35.0 && atrPips <= 70.0) return 1;
   return 0;
}

int Strategy_Engulfing_Score(string symbol)
{
   double o0 = iOpen(symbol, PERIOD_H1, 1), c0 = iClose(symbol, PERIOD_H1, 1);
   double o1 = iOpen(symbol, PERIOD_H1, 2), c1 = iClose(symbol, PERIOD_H1, 2);
   double body0 = MathAbs(c0 - o0);
   double body1 = MathAbs(c1 - o1);
   bool volOk = (double)iVolume(symbol, PERIOD_H1, 1) > CalculateAverageVolume(symbol, PERIOD_H1, 20) * 1.1;
   bool bull = c1 < o1 && c0 > o0 && o0 <= c1 && c0 >= o1 && body0 >= body1 && volOk;
   bool bear = c1 > o1 && c0 < o0 && o0 >= c1 && c0 <= o1 && body0 >= body1 && volOk;
   bool key = IsAtKeyLevel(symbol, PERIOD_H1, c0, 10.0 * PipSize(symbol));
   if((bull || bear) && key) return 2;
   if(bull || bear) return 1;
   return 0;
}

int Strategy_Engulfing_Direction(string symbol)
{
   double o0 = iOpen(symbol, PERIOD_H1, 1), c0 = iClose(symbol, PERIOD_H1, 1);
   double o1 = iOpen(symbol, PERIOD_H1, 2), c1 = iClose(symbol, PERIOD_H1, 2);
   if(c1 < o1 && c0 > o0 && o0 <= c1 && c0 >= o1) return 1;
   if(c1 > o1 && c0 < o0 && o0 >= c1 && c0 <= o1) return -1;
   return 0;
}

int Strategy_WickRejection_Score(string symbol)
{
   double open = iOpen(symbol, PERIOD_H1, 1);
   double high = iHigh(symbol, PERIOD_H1, 1);
   double low = iLow(symbol, PERIOD_H1, 1);
   double close = iClose(symbol, PERIOD_H1, 1);
   double body = MathAbs(close - open);
   double upper = high - MathMax(open, close);
   double lower = MathMin(open, close) - low;
   double range = MathMax(high - low, SymbolInfoDouble(symbol, SYMBOL_POINT));
   bool bull = lower >= body * 2.0 && body <= range * 0.35;
   bool bear = upper >= body * 2.0 && body <= range * 0.35;
   bool level = IsAtKeyLevel(symbol, PERIOD_H1, close, 15.0 * PipSize(symbol));
   if((bull || bear) && level) return 3;
   if(bull || bear) return 2;
   return 0;
}

int Strategy_Wick_Direction(string symbol)
{
   double open = iOpen(symbol, PERIOD_H1, 1);
   double high = iHigh(symbol, PERIOD_H1, 1);
   double low = iLow(symbol, PERIOD_H1, 1);
   double close = iClose(symbol, PERIOD_H1, 1);
   double body = MathAbs(close - open);
   double upper = high - MathMax(open, close);
   double lower = MathMin(open, close) - low;
   if(lower >= body * 2.0) return 1;
   if(upper >= body * 2.0) return -1;
   return 0;
}

int Strategy_PremiumDiscount_Score(string symbol)
{
   double high = FindSwingHigh(symbol, PERIOD_H1, 100);
   double low = FindSwingLow(symbol, PERIOD_H1, 100);
   double range = high - low;
   if(range <= 0.0) return 0;
   double close = iClose(symbol, PERIOD_H1, 1);
   double oteLow = high - range * 0.79;
   double oteHigh = high - range * 0.62;
   double eq = high - range * 0.50;
   if(close >= oteLow && close <= oteHigh) return 2;
   if(MathAbs(close - eq) < 5.0 * PipSize(symbol)) return 1;
   return 0;
}

int Strategy_Premium_Direction(string symbol)
{
   double high = FindSwingHigh(symbol, PERIOD_H1, 100);
   double low = FindSwingLow(symbol, PERIOD_H1, 100);
   double mid = (high + low) / 2.0;
   double close = iClose(symbol, PERIOD_H1, 1);
   if(close < mid) return 1;
   if(close > mid) return -1;
   return 0;
}

int Strategy_Martingale_Score(string symbol)
{
   double adx = IndicatorValue(g_ADX_handle, 0, 1);
   if(GetCurrentDrawdown() > 8.0) return 0;
   if(adx > 25.0) return 0;
   if(GetCurrentLossStreak() >= 3) return 0;
   return 1;
}

bool HasM15EntrySignal(string symbol)
{
   double close = iClose(symbol, PERIOD_M15, 1);
   double open = iOpen(symbol, PERIOD_M15, 1);
   return close != open && HasReversalCandle(symbol, PERIOD_M15, 1);
}

int Strategy_MultiTimeframe_Score(string symbol)
{
   int mtf = 0;
   string d1 = GetTrend(symbol, PERIOD_D1);
   string h4 = GetTrend(symbol, PERIOD_H4);
   string h1 = GetTrend(symbol, PERIOD_H1);
   string bias = (g_DailyBias == "STRONG_BULL" || g_DailyBias == "BULL") ? "BULL" :
                 (g_DailyBias == "STRONG_BEAR" || g_DailyBias == "BEAR") ? "BEAR" : "NEUTRAL";
   if(d1 == bias) mtf += 3;
   if(h4 == d1) mtf += 2;
   if(h1 == d1) mtf += 2;
   if(HasM15EntrySignal(symbol)) mtf += 2;
   if(IsVolumeConfirmed(symbol, PERIOD_H1)) mtf += 1;
   if(IsRSI_Aligned(symbol, PERIOD_H1, d1)) mtf += 1;
   return MathMin(mtf, 3);
}

int Strategy_MTF_Direction(string symbol)
{
   string d1 = GetTrend(symbol, PERIOD_D1);
   if(d1 == "BULL") return 1;
   if(d1 == "BEAR") return -1;
   return DirectionFromBias();
}

#endif
