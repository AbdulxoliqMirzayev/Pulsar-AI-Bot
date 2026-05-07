#ifndef AB_ELLIOTT_MQH
#define AB_ELLIOTT_MQH

void InitElliottWave()
{
   Print("AB_Elliott initialized.");
}

int FindAlternatingSwings(string symbol, ENUM_TIMEFRAMES tf, double &swings[], int maxCount)
{
   ArrayResize(swings, maxCount);
   int count = 0;
   int lastType = 0;
   for(int i = 4; i < 220 && count < maxCount; i++)
   {
      bool high = IsSwingHigh(symbol, tf, i);
      bool low = IsSwingLow(symbol, tf, i);
      if(high && lastType != 1)
      {
         swings[count] = iHigh(symbol, tf, i);
         count++;
         lastType = 1;
      }
      else if(low && lastType != -1)
      {
         swings[count] = iLow(symbol, tf, i);
         count++;
         lastType = -1;
      }
   }
   return count;
}

int DetectElliottWave(string symbol, ENUM_TIMEFRAMES tf)
{
   double swings[];
   int count = FindAlternatingSwings(symbol, tf, swings, 10);
   if(count < 6) return 0;

   double w1 = MathAbs(swings[1] - swings[0]);
   double w2 = MathAbs(swings[2] - swings[1]);
   double w3 = MathAbs(swings[3] - swings[2]);
   double w4 = MathAbs(swings[4] - swings[3]);
   double w5 = MathAbs(swings[5] - swings[4]);
   if(w1 <= 0.0 || w3 <= 0.0 || w5 <= 0.0) return 0;

   bool bullish = swings[1] > swings[0];
   bool wave2Valid = bullish ? swings[2] > swings[0] : swings[2] < swings[0];
   bool wave3NotShortest = !(w3 < w1 && w3 < w5);
   bool wave4NoOverlap = bullish ? swings[4] > swings[1] : swings[4] < swings[1];
   if(!wave2Valid || !wave3NotShortest || !wave4NoOverlap) return 0;

   double close = iClose(symbol, tf, 1);
   double wave3Retrace382 = bullish ? swings[3] - w3 * 0.382 : swings[3] + w3 * 0.382;
   double wave2Retrace618 = bullish ? swings[1] - w1 * 0.618 : swings[1] + w1 * 0.618;
   double tol = 12.0 * PipSize(symbol);
   if(MathAbs(close - wave2Retrace618) <= tol) return bullish ? 1 : -1;
   if(MathAbs(close - wave3Retrace382) <= tol) return bullish ? 1 : -1;

   double wave5Target = bullish ? swings[4] + w1 : swings[4] - w1;
   if(MathAbs(close - wave5Target) <= tol) return bullish ? -1 : 1;
   return 0;
}

#endif
