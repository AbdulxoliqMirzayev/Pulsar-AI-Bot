#ifndef AB_SMC_MQH
#define AB_SMC_MQH

struct OrderBlock
{
   double high;
   double low;
   double mid;
   bool   isBullish;
   bool   isValid;
   bool   isMitigated;
   int    barIndex;
   double volumeAtCreation;
};

struct FairValueGap
{
   double top;
   double bottom;
   double mid;
   bool   isBullish;
   bool   isValid;
   int    barIndex;
};

struct SwingPoint
{
   int index;
   double price;
   bool isHigh;
};

double PipSize(string symbol)
{
   int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
   double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
   if(digits == 3 || digits == 5) return point * 10.0;
   return point;
}

double GetATRValue(string symbol, ENUM_TIMEFRAMES tf, int period = 14, int shift = 1)
{
   int handle = iATR(symbol, tf, period);
   if(handle == INVALID_HANDLE) return 0.0;
   double buf[];
   ArraySetAsSeries(buf, true);
   double value = 0.0;
   if(CopyBuffer(handle, 0, shift, 1, buf) > 0) value = buf[0];
   IndicatorRelease(handle);
   return value;
}

double CalculateAverageVolume(string symbol, ENUM_TIMEFRAMES tf, int period)
{
   double total = 0.0;
   int count = 0;
   for(int i = 1; i <= period; i++)
   {
      long vol = iVolume(symbol, tf, i);
      if(vol > 0)
      {
         total += (double)vol;
         count++;
      }
   }
   return count == 0 ? 1.0 : total / (double)count;
}

bool IsSwingHigh(string symbol, ENUM_TIMEFRAMES tf, int shift, int wing = 2)
{
   double price = iHigh(symbol, tf, shift);
   for(int i = 1; i <= wing; i++)
   {
      if(price <= iHigh(symbol, tf, shift - i)) return false;
      if(price <= iHigh(symbol, tf, shift + i)) return false;
   }
   return true;
}

bool IsSwingLow(string symbol, ENUM_TIMEFRAMES tf, int shift, int wing = 2)
{
   double price = iLow(symbol, tf, shift);
   for(int i = 1; i <= wing; i++)
   {
      if(price >= iLow(symbol, tf, shift - i)) return false;
      if(price >= iLow(symbol, tf, shift + i)) return false;
   }
   return true;
}

double FindSwingHigh(string symbol, ENUM_TIMEFRAMES tf, int lookback)
{
   for(int i = 3; i <= lookback; i++)
      if(IsSwingHigh(symbol, tf, i)) return iHigh(symbol, tf, i);
   int idx = iHighest(symbol, tf, MODE_HIGH, lookback, 1);
   return idx >= 0 ? iHigh(symbol, tf, idx) : iHigh(symbol, tf, 1);
}

double FindSwingLow(string symbol, ENUM_TIMEFRAMES tf, int lookback)
{
   for(int i = 3; i <= lookback; i++)
      if(IsSwingLow(symbol, tf, i)) return iLow(symbol, tf, i);
   int idx = iLowest(symbol, tf, MODE_LOW, lookback, 1);
   return idx >= 0 ? iLow(symbol, tf, idx) : iLow(symbol, tf, 1);
}

string GetTrend(string symbol, ENUM_TIMEFRAMES tf)
{
   double lastHigh = 0.0, prevHigh = 0.0, lastLow = 0.0, prevLow = 0.0;
   for(int i = 3; i < 120; i++)
   {
      if(IsSwingHigh(symbol, tf, i))
      {
         if(lastHigh == 0.0) lastHigh = iHigh(symbol, tf, i);
         else if(prevHigh == 0.0) prevHigh = iHigh(symbol, tf, i);
      }
      if(IsSwingLow(symbol, tf, i))
      {
         if(lastLow == 0.0) lastLow = iLow(symbol, tf, i);
         else if(prevLow == 0.0) prevLow = iLow(symbol, tf, i);
      }
      if(lastHigh > 0.0 && prevHigh > 0.0 && lastLow > 0.0 && prevLow > 0.0) break;
   }
   if(lastHigh > prevHigh && lastLow > prevLow) return "BULL";
   if(lastHigh < prevHigh && lastLow < prevLow) return "BEAR";
   return "NEUTRAL";
}

string AnalyzeDailyBias(string symbol)
{
   string h4 = GetTrend(symbol, PERIOD_H4);
   double dHigh = iHigh(symbol, PERIOD_D1, 1);
   double dLow = iLow(symbol, PERIOD_D1, 1);
   double close = iClose(symbol, PERIOD_H4, 1);
   double mid = (dHigh + dLow) / 2.0;
   if(h4 == "BULL" && close < mid) return "STRONG_BULL";
   if(h4 == "BULL") return "BULL";
   if(h4 == "BEAR" && close > mid) return "STRONG_BEAR";
   if(h4 == "BEAR") return "BEAR";
   return "NEUTRAL";
}

void AnalyzeMarketStructure(string symbol, ENUM_TIMEFRAMES tf)
{
   double swingHigh = FindSwingHigh(symbol, tf, 80);
   double swingLow = FindSwingLow(symbol, tf, 80);
   double close = iClose(symbol, tf, 1);
   string prefix = "AB_MS_" + symbol + "_" + IntegerToString((int)tf) + "_";
   if(close > swingHigh)
   {
      ObjectCreate(0, prefix + "BOS_UP", OBJ_ARROW_UP, 0, iTime(symbol, tf, 1), swingHigh);
      ObjectSetInteger(0, prefix + "BOS_UP", OBJPROP_COLOR, clrLime);
   }
   if(close < swingLow)
   {
      ObjectCreate(0, prefix + "BOS_DN", OBJ_ARROW_DOWN, 0, iTime(symbol, tf, 1), swingLow);
      ObjectSetInteger(0, prefix + "BOS_DN", OBJPROP_COLOR, clrTomato);
   }
}

OrderBlock EmptyOrderBlock()
{
   OrderBlock ob;
   ob.high = 0.0;
   ob.low = 0.0;
   ob.mid = 0.0;
   ob.isBullish = true;
   ob.isValid = false;
   ob.isMitigated = false;
   ob.barIndex = -1;
   ob.volumeAtCreation = 0.0;
   return ob;
}

OrderBlock FindNearestOrderBlock(string symbol, ENUM_TIMEFRAMES tf, int lookback)
{
   OrderBlock nearest = EmptyOrderBlock();
   double close = iClose(symbol, tf, 1);
   double atr = GetATRValue(symbol, tf, 14, 1);
   double bestDistance = DBL_MAX;
   for(int i = 5; i <= lookback; i++)
   {
      double open = iOpen(symbol, tf, i);
      double candleClose = iClose(symbol, tf, i);
      double futureClose = iClose(symbol, tf, MathMax(i - 4, 1));
      double impulse = futureClose - candleClose;
      bool bearishCandle = candleClose < open;
      bool bullishCandle = candleClose > open;
      bool bullOB = bearishCandle && impulse > atr * 2.5;
      bool bearOB = bullishCandle && impulse < -atr * 2.5;
      if(!bullOB && !bearOB) continue;

      double high = iHigh(symbol, tf, i);
      double low = iLow(symbol, tf, i);
      bool valid = bullOB ? close >= low : close <= high;
      if(!valid) continue;
      double mid = (high + low) / 2.0;
      double distance = MathAbs(close - mid);
      if(distance < bestDistance)
      {
         bestDistance = distance;
         nearest.high = high;
         nearest.low = low;
         nearest.mid = mid;
         nearest.isBullish = bullOB;
         nearest.isValid = true;
         nearest.isMitigated = close >= low && close <= high;
         nearest.barIndex = i;
         nearest.volumeAtCreation = (double)iVolume(symbol, tf, i);
      }
   }
   return nearest;
}

FairValueGap EmptyFVG()
{
   FairValueGap fvg;
   fvg.top = 0.0;
   fvg.bottom = 0.0;
   fvg.mid = 0.0;
   fvg.isBullish = true;
   fvg.isValid = false;
   fvg.barIndex = -1;
   return fvg;
}

FairValueGap FindNearestFVG(string symbol, ENUM_TIMEFRAMES tf, int lookback)
{
   FairValueGap nearest = EmptyFVG();
   double close = iClose(symbol, tf, 1);
   double pip = PipSize(symbol);
   double bestDistance = DBL_MAX;
   for(int i = 2; i <= lookback; i++)
   {
      double prevHigh = iHigh(symbol, tf, i + 1);
      double prevLow = iLow(symbol, tf, i + 1);
      double nextHigh = iHigh(symbol, tf, i - 1);
      double nextLow = iLow(symbol, tf, i - 1);
      bool bullFVG = prevHigh < nextLow && (nextLow - prevHigh) >= FVG_MinSize * pip;
      bool bearFVG = prevLow > nextHigh && (prevLow - nextHigh) >= FVG_MinSize * pip;
      if(!bullFVG && !bearFVG) continue;
      double bottom = bullFVG ? prevHigh : nextHigh;
      double top = bullFVG ? nextLow : prevLow;
      bool valid = bullFVG ? close >= bottom : close <= top;
      if(!valid) continue;
      double mid = (top + bottom) / 2.0;
      double distance = MathAbs(close - mid);
      if(distance < bestDistance)
      {
         bestDistance = distance;
         nearest.top = top;
         nearest.bottom = bottom;
         nearest.mid = mid;
         nearest.isBullish = bullFVG;
         nearest.isValid = true;
         nearest.barIndex = i;
      }
   }
   return nearest;
}

bool DetectBOS(string symbol, ENUM_TIMEFRAMES tf)
{
   double close = iClose(symbol, tf, 1);
   double high = FindSwingHigh(symbol, tf, 80);
   double low = FindSwingLow(symbol, tf, 80);
   return close > high || close < low;
}

int DetectCHoCH(string symbol, ENUM_TIMEFRAMES tf)
{
   string trend = GetTrend(symbol, tf);
   double close = iClose(symbol, tf, 1);
   double high = FindSwingHigh(symbol, tf, 80);
   double low = FindSwingLow(symbol, tf, 80);
   if(trend == "BEAR" && close > high) return 1;
   if(trend == "BULL" && close < low) return -1;
   return 0;
}

bool HasReversalCandle(string symbol, ENUM_TIMEFRAMES tf, int shift)
{
   double open = iOpen(symbol, tf, shift);
   double high = iHigh(symbol, tf, shift);
   double low = iLow(symbol, tf, shift);
   double close = iClose(symbol, tf, shift);
   double body = MathAbs(close - open);
   double upper = high - MathMax(open, close);
   double lower = MathMin(open, close) - low;
   return lower > body * 2.0 || upper > body * 2.0 || body > MathAbs(iClose(symbol, tf, shift + 1) - iOpen(symbol, tf, shift + 1)) * 1.2;
}

bool DetectLiquiditySweep(string symbol, ENUM_TIMEFRAMES tf, bool buySide)
{
   double pip = PipSize(symbol);
   double swing = buySide ? FindSwingHigh(symbol, tf, 50) : FindSwingLow(symbol, tf, 50);
   double high = iHigh(symbol, tf, 1);
   double low = iLow(symbol, tf, 1);
   double close = iClose(symbol, tf, 1);
   if(buySide) return high > swing + 3.0 * pip && close < swing - 1.0 * pip;
   return low < swing - 3.0 * pip && close > swing + 1.0 * pip;
}

double GetDistanceToBSL(string symbol)
{
   double level = FindSwingHigh(symbol, PERIOD_H1, 80);
   return MathAbs(level - iClose(symbol, PERIOD_H1, 1)) / PipSize(symbol);
}

double GetDistanceToSSL(string symbol)
{
   double level = FindSwingLow(symbol, PERIOD_H1, 80);
   return MathAbs(iClose(symbol, PERIOD_H1, 1) - level) / PipSize(symbol);
}

int GetFibZone(string symbol, ENUM_TIMEFRAMES tf)
{
   double high = FindSwingHigh(symbol, tf, 80);
   double low = FindSwingLow(symbol, tf, 80);
   double close = iClose(symbol, tf, 1);
   double range = MathMax(high - low, SymbolInfoDouble(symbol, SYMBOL_POINT));
   double ratio = (high - close) / range;
   if(ratio >= 0.20 && ratio < 0.30) return 1;
   if(ratio >= 0.35 && ratio < 0.43) return 2;
   if(ratio >= 0.48 && ratio < 0.53) return 3;
   if(ratio >= 0.60 && ratio < 0.64) return 4;
   if(ratio >= 0.68 && ratio < 0.73) return 5;
   if(ratio >= 0.76 && ratio < 0.80) return 6;
   return 0;
}

bool IsAtKeyLevel(string symbol, ENUM_TIMEFRAMES tf, double price, double tolerance)
{
   if(MathAbs(price - FindSwingHigh(symbol, tf, 80)) <= tolerance) return true;
   if(MathAbs(price - FindSwingLow(symbol, tf, 80)) <= tolerance) return true;
   OrderBlock ob = FindNearestOrderBlock(symbol, tf, OB_Lookback);
   if(ob.isValid && price >= ob.low - tolerance && price <= ob.high + tolerance) return true;
   FairValueGap fvg = FindNearestFVG(symbol, tf, 30);
   if(fvg.isValid && price >= fvg.bottom - tolerance && price <= fvg.top + tolerance) return true;
   return false;
}

bool IsVolumeConfirmed(string symbol, ENUM_TIMEFRAMES tf)
{
   return (double)iVolume(symbol, tf, 1) > CalculateAverageVolume(symbol, tf, 20) * 1.2;
}

bool IsRSI_Aligned(string symbol, ENUM_TIMEFRAMES tf, string trend)
{
   int handle = iRSI(symbol, tf, 14, PRICE_CLOSE);
   if(handle == INVALID_HANDLE) return false;
   double buf[];
   ArraySetAsSeries(buf, true);
   bool aligned = false;
   if(CopyBuffer(handle, 0, 1, 1, buf) > 0)
   {
      aligned = (trend == "BULL" && buf[0] > 50.0) || (trend == "BEAR" && buf[0] < 50.0);
   }
   IndicatorRelease(handle);
   return aligned;
}

bool IsLondonSession()
{
   MqlDateTime dt;
   TimeToStruct(TimeGMT(), dt);
   return dt.hour >= 7 && dt.hour < 10;
}

bool IsNYSession()
{
   MqlDateTime dt;
   TimeToStruct(TimeGMT(), dt);
   return dt.hour >= 13 && dt.hour < 16;
}

bool IsInKillzone()
{
   MqlDateTime dt;
   TimeToStruct(TimeGMT(), dt);
   return (dt.hour >= 7 && dt.hour < 10) || (dt.hour >= 13 && dt.hour < 16) || (dt.hour >= 18 && dt.hour < 19);
}

bool IsAsianRangeSwept(string symbol)
{
   double asianHigh = 0.0;
   double asianLow = DBL_MAX;
   for(int i = 1; i <= 24; i++)
   {
      datetime barTime = iTime(symbol, PERIOD_H1, i);
      MqlDateTime dt;
      TimeToStruct(barTime, dt);
      if(dt.hour >= 0 && dt.hour < 4)
      {
         asianHigh = MathMax(asianHigh, iHigh(symbol, PERIOD_H1, i));
         asianLow = MathMin(asianLow, iLow(symbol, PERIOD_H1, i));
      }
   }
   if(asianHigh == 0.0 || asianLow == DBL_MAX) return false;
   return iHigh(symbol, PERIOD_H1, 1) > asianHigh || iLow(symbol, PERIOD_H1, 1) < asianLow;
}

void InitSMC()
{
   Print("AB_SMC initialized.");
}

#endif
