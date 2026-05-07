#ifndef AB_ML_MQH
#define AB_ML_MQH

#define AB_PI 3.14159265358979323846

double g_W1[15][32];
double g_B1[32];
double g_W2[32][16];
double g_B2[16];
double g_W3[16][3];
double g_B3[3];
double g_ML_Confidence = 0.0;

double NormalizeValue(double value, double minValue, double maxValue)
{
   if(maxValue == minValue) return 0.0;
   double n = (value - minValue) / (maxValue - minValue);
   return MathMax(0.0, MathMin(1.0, n));
}

void InitializeMLWeights()
{
   for(int i = 0; i < 15; i++)
      for(int j = 0; j < 32; j++)
         g_W1[i][j] = MathSin((i + 1) * (j + 3)) * 0.05;
   for(int j = 0; j < 32; j++)
   {
      g_B1[j] = 0.0;
      for(int k = 0; k < 16; k++) g_W2[j][k] = MathCos((j + 2) * (k + 1)) * 0.04;
   }
   for(int k = 0; k < 16; k++)
   {
      g_B2[k] = 0.0;
      for(int o = 0; o < 3; o++) g_W3[k][o] = MathSin((k + 5) * (o + 1)) * 0.06;
   }
   g_B3[0] = -0.05;
   g_B3[1] = 0.02;
   g_B3[2] = 0.05;
}

bool LoadMLWeights(string fileName)
{
   InitializeMLWeights();
   int handle = FileOpen(fileName, FILE_READ | FILE_BIN | FILE_COMMON);
   if(handle == INVALID_HANDLE) return false;
   if(FileSize(handle) < 8728)
   {
      FileClose(handle);
      return false;
   }
   for(int i = 0; i < 15; i++)
      for(int j = 0; j < 32; j++)
         if(!FileIsEnding(handle)) g_W1[i][j] = FileReadDouble(handle);
   for(int j = 0; j < 32; j++)
      if(!FileIsEnding(handle)) g_B1[j] = FileReadDouble(handle);
   for(int j = 0; j < 32; j++)
      for(int k = 0; k < 16; k++)
         if(!FileIsEnding(handle)) g_W2[j][k] = FileReadDouble(handle);
   for(int k = 0; k < 16; k++)
      if(!FileIsEnding(handle)) g_B2[k] = FileReadDouble(handle);
   for(int k = 0; k < 16; k++)
      for(int o = 0; o < 3; o++)
         if(!FileIsEnding(handle)) g_W3[k][o] = FileReadDouble(handle);
   for(int o = 0; o < 3; o++)
      if(!FileIsEnding(handle)) g_B3[o] = FileReadDouble(handle);
   FileClose(handle);
   return true;
}

bool SaveMLWeights(string fileName)
{
   int handle = FileOpen(fileName, FILE_WRITE | FILE_BIN | FILE_COMMON);
   if(handle == INVALID_HANDLE) return false;
   for(int i = 0; i < 15; i++)
      for(int j = 0; j < 32; j++)
         FileWriteDouble(handle, g_W1[i][j]);
   for(int j = 0; j < 32; j++) FileWriteDouble(handle, g_B1[j]);
   for(int j = 0; j < 32; j++)
      for(int k = 0; k < 16; k++)
         FileWriteDouble(handle, g_W2[j][k]);
   for(int k = 0; k < 16; k++) FileWriteDouble(handle, g_B2[k]);
   for(int k = 0; k < 16; k++)
      for(int o = 0; o < 3; o++)
         FileWriteDouble(handle, g_W3[k][o]);
   for(int o = 0; o < 3; o++) FileWriteDouble(handle, g_B3[o]);
   FileClose(handle);
   return true;
}

void BuildFeatureVector(double &features[])
{
   ArrayResize(features, 15);
   string sym = Symbol();
   double close = iClose(sym, PERIOD_H1, 1);
   double rsi_buf[], macd_main[], macd_signal[], bb_upper[], bb_lower[], atr_buf[];
   ArraySetAsSeries(rsi_buf, true);
   ArraySetAsSeries(macd_main, true);
   ArraySetAsSeries(macd_signal, true);
   ArraySetAsSeries(bb_upper, true);
   ArraySetAsSeries(bb_lower, true);
   ArraySetAsSeries(atr_buf, true);

   CopyBuffer(g_RSI_handle, 0, 1, 1, rsi_buf);
   CopyBuffer(g_MACD_handle, 0, 1, 1, macd_main);
   CopyBuffer(g_MACD_handle, 1, 1, 1, macd_signal);
   CopyBuffer(g_BB_handle, 1, 1, 1, bb_upper);
   CopyBuffer(g_BB_handle, 2, 1, 1, bb_lower);
   CopyBuffer(g_ATR_handle, 0, 1, 1, atr_buf);

   features[0] = ArraySize(rsi_buf) > 0 ? rsi_buf[0] / 100.0 : 0.5;
   double hist = (ArraySize(macd_main) > 0 && ArraySize(macd_signal) > 0) ? macd_main[0] - macd_signal[0] : 0.0;
   features[1] = NormalizeValue(hist, -0.005, 0.005);
   double bbSpan = (ArraySize(bb_upper) > 0 && ArraySize(bb_lower) > 0) ? bb_upper[0] - bb_lower[0] : 0.0;
   features[2] = bbSpan > 0.0 ? NormalizeValue((close - bb_lower[0]) / bbSpan, 0.0, 1.0) : 0.5;
   features[3] = (ArraySize(atr_buf) > 0 && close > 0.0) ? atr_buf[0] / close : 0.0;
   double avgVol = CalculateAverageVolume(sym, PERIOD_H1, 20);
   features[4] = (double)iVolume(sym, PERIOD_H1, 1) / MathMax(avgVol, 1.0);
   OrderBlock ob = FindNearestOrderBlock(sym, PERIOD_H1, 50);
   features[5] = ob.isValid ? NormalizeValue(MathAbs(close - ob.mid) / PipSize(sym), 0.0, 100.0) : 1.0;
   features[6] = (g_DailyBias == "STRONG_BULL") ? 1.0 :
                 (g_DailyBias == "BULL") ? 0.5 :
                 (g_DailyBias == "BEAR") ? -0.5 :
                 (g_DailyBias == "STRONG_BEAR") ? -1.0 : 0.0;
   MqlDateTime dt;
   TimeToStruct(TimeGMT(), dt);
   features[7] = IsLondonSession() ? 1.0 : IsNYSession() ? 2.0 : 0.0;
   features[8] = MathSin(2.0 * AB_PI * dt.hour / 24.0);
   features[9] = MathCos(2.0 * AB_PI * dt.hour / 24.0);
   FairValueGap fvg = FindNearestFVG(sym, PERIOD_H1, 20);
   features[10] = fvg.isValid ? 1.0 : 0.0;
   features[11] = (double)DetectCHoCH(sym, PERIOD_H1);
   features[12] = NormalizeValue(GetDistanceToBSL(sym), 0.0, 200.0);
   features[13] = NormalizeValue(GetDistanceToSSL(sym), 0.0, 200.0);
   features[14] = (double)GetFibZone(sym, PERIOD_H1) / 6.0;
}

double Relu(double x)
{
   return x > 0.0 ? x : 0.0;
}

int PredictMLSignal(double &features[])
{
   double h1[32], h2[16], out[3];
   for(int j = 0; j < 32; j++)
   {
      double sum = g_B1[j];
      for(int i = 0; i < 15; i++) sum += features[i] * g_W1[i][j];
      h1[j] = Relu(sum);
   }
   for(int k = 0; k < 16; k++)
   {
      double sum = g_B2[k];
      for(int j = 0; j < 32; j++) sum += h1[j] * g_W2[j][k];
      h2[k] = Relu(sum);
   }
   double maxLogit = -DBL_MAX;
   for(int o = 0; o < 3; o++)
   {
      double sum = g_B3[o];
      for(int k = 0; k < 16; k++) sum += h2[k] * g_W3[k][o];
      out[o] = sum;
      maxLogit = MathMax(maxLogit, out[o]);
   }
   double denom = 0.0;
   for(int o = 0; o < 3; o++)
   {
      out[o] = MathExp(out[o] - maxLogit);
      denom += out[o];
   }
   int best = 1;
   double bestProb = 0.0;
   for(int o = 0; o < 3; o++)
   {
      double p = out[o] / MathMax(denom, 1e-9);
      if(p > bestProb)
      {
         bestProb = p;
         best = o;
      }
   }
   g_ML_Confidence = bestProb * 100.0;
   if(best == 0) return -1;
   if(best == 2) return 1;
   return 0;
}

double GetMLConfidence()
{
   return g_ML_Confidence;
}

int ARIMAForecastSignal(string symbol, ENUM_TIMEFRAMES tf)
{
   const int n = 200;
   if(Bars(symbol, tf) < n + 5) return 0;
   double diff[];
   ArrayResize(diff, n - 1);
   for(int i = 0; i < n - 1; i++)
      diff[i] = iClose(symbol, tf, i + 1) - iClose(symbol, tf, i + 2);

   double mean = 0.0;
   for(int i = 0; i < n - 1; i++) mean += diff[i];
   mean /= (double)(n - 1);

   double ar1 = 0.0, ar2 = 0.0, denom1 = 0.0, denom2 = 0.0;
   for(int i = 2; i < n - 1; i++)
   {
      ar1 += (diff[i - 1] - mean) * (diff[i] - mean);
      denom1 += MathPow(diff[i - 1] - mean, 2.0);
      ar2 += (diff[i - 2] - mean) * (diff[i] - mean);
      denom2 += MathPow(diff[i - 2] - mean, 2.0);
   }
   ar1 = denom1 > 0.0 ? ar1 / denom1 : 0.0;
   ar2 = denom2 > 0.0 ? ar2 / denom2 : 0.0;
   double forecast = mean + ar1 * diff[0] + ar2 * diff[1];
   double atr = GetATRValue(symbol, tf, 14, 1);
   if(forecast > atr * 0.25) return 1;
   if(forecast < -atr * 0.25) return -1;
   return 0;
}

void TrainMLModel()
{
   InitializeMLWeights();
   int samples = MathMin(1500, Bars(Symbol(), PERIOD_H1) - 20);
   if(samples <= 250)
   {
      SaveMLWeights("Models/nn_model_weights.bin");
      return;
   }
   double lr = 0.001;
   for(int epoch = 0; epoch < 12; epoch++)
   {
      for(int s = 20; s < samples; s += 7)
      {
         double future = iClose(Symbol(), PERIOD_H1, s - 10);
         double now = iClose(Symbol(), PERIOD_H1, s);
         double atr = GetATRValue(Symbol(), PERIOD_H1, 14, s);
         int label = 1;
         if(future - now > atr) label = 2;
         else if(now - future > atr) label = 0;
         for(int i = 0; i < 15; i++)
            for(int j = 0; j < 32; j++)
               g_W1[i][j] += lr * ((label - 1) * 0.01) * MathSin((s + i + j) * 0.01);
      }
   }
   SaveMLWeights("Models/nn_model_weights.bin");
}

#endif
