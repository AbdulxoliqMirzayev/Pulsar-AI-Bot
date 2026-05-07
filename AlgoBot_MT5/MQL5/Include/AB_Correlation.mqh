#ifndef AB_CORRELATION_MQH
#define AB_CORRELATION_MQH

double g_CorrelationMatrix[28][28];
string g_Pairs[28] = {
   "EURUSD","GBPUSD","USDJPY","USDCHF","AUDUSD","NZDUSD","USDCAD",
   "EURGBP","EURJPY","GBPJPY","AUDJPY","NZDJPY","CADJPY","CHFJPY",
   "EURAUD","EURNZD","EURCAD","EURCHF","GBPAUD","GBPNZD","GBPCAD",
   "GBPCHF","AUDNZD","AUDCAD","AUDCHF","NZDCAD","NZDCHF","CADCHF"
};

int PairIndex(string symbol)
{
   for(int i = 0; i < 28; i++)
      if(g_Pairs[i] == symbol) return i;
   return -1;
}

double CalculatePearsonCorr(string a, string b, int period)
{
   if(a == b) return 1.0;
   if(Bars(a, PERIOD_H1) < period + 2 || Bars(b, PERIOD_H1) < period + 2) return 0.0;
   double xa[], xb[];
   ArrayResize(xa, period);
   ArrayResize(xb, period);
   double ma = 0.0, mb = 0.0;
   for(int i = 0; i < period; i++)
   {
      double ca0 = iClose(a, PERIOD_H1, i + 1);
      double ca1 = iClose(a, PERIOD_H1, i + 2);
      double cb0 = iClose(b, PERIOD_H1, i + 1);
      double cb1 = iClose(b, PERIOD_H1, i + 2);
      if(ca1 == 0.0 || cb1 == 0.0) return 0.0;
      xa[i] = (ca0 - ca1) / ca1;
      xb[i] = (cb0 - cb1) / cb1;
      ma += xa[i];
      mb += xb[i];
   }
   ma /= (double)period;
   mb /= (double)period;
   double num = 0.0, da = 0.0, db = 0.0;
   for(int i = 0; i < period; i++)
   {
      num += (xa[i] - ma) * (xb[i] - mb);
      da += MathPow(xa[i] - ma, 2.0);
      db += MathPow(xb[i] - mb, 2.0);
   }
   if(da <= 0.0 || db <= 0.0) return 0.0;
   return num / MathSqrt(da * db);
}

void InitCorrelationMatrix()
{
   for(int i = 0; i < 28; i++)
      for(int j = 0; j < 28; j++)
         g_CorrelationMatrix[i][j] = (i == j) ? 1.0 : 0.0;
}

void UpdateCorrelationMatrix()
{
   for(int i = 0; i < 28; i++)
   {
      for(int j = i + 1; j < 28; j++)
      {
         double corr = CalculatePearsonCorr(g_Pairs[i], g_Pairs[j], 50);
         g_CorrelationMatrix[i][j] = corr;
         g_CorrelationMatrix[j][i] = corr;
      }
   }
}

double GetPairCorrelation(string a, string b)
{
   int ia = PairIndex(a);
   int ib = PairIndex(b);
   if(ia >= 0 && ib >= 0) return g_CorrelationMatrix[ia][ib];
   return CalculatePearsonCorr(a, b, 50);
}

bool IsCorrelated(string newPair)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0 || !PositionSelectByTicket(ticket)) continue;
      if((int)PositionGetInteger(POSITION_MAGIC) != MagicNumber) continue;
      string openPair = PositionGetString(POSITION_SYMBOL);
      if(openPair == newPair) continue;
      double corr = GetPairCorrelation(newPair, openPair);
      if(MathAbs(corr) > 0.70)
      {
         Print("Correlation blocked: ", newPair, " <-> ", openPair, " corr=", DoubleToString(corr, 2));
         return true;
      }
   }
   return false;
}

#endif
