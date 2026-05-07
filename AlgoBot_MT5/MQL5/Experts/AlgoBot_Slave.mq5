//+------------------------------------------------------------------+
//| AlgoBot_Slave.mq5 - Account copier receiver                       |
//+------------------------------------------------------------------+
#property copyright "AlgoBot v3.0"
#property version   "3.00"
#property strict

#include <Trade/Trade.mqh>

input string CopierServerIP = "127.0.0.1";
input int    CopierServerPort = 5555;
input int    MagicNumber = 202401;
input double SlaveRiskPercent = 1.0;
input double MaxDailyRisk = 5.0;
input double MaxSlippagePips = 3.0;
input bool   UseBalanceScaling = true;
input double MasterBalance = 10000.0;
input int    PollIntervalMS = 200;

CTrade slaveTrade;
int g_Socket = INVALID_HANDLE;
double g_DailyStart = 0.0;
datetime g_Day = 0;

double SlavePipSize(string symbol)
{
   int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
   double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
   return (digits == 3 || digits == 5) ? point * 10.0 : point;
}

void ResetSlaveDaily()
{
   MqlDateTime dt;
   TimeToStruct(TimeGMT(), dt);
   datetime today = StringToTime(IntegerToString(dt.year) + "." + IntegerToString(dt.mon) + "." + IntegerToString(dt.day));
   if(g_Day != today)
   {
      g_Day = today;
      g_DailyStart = AccountInfoDouble(ACCOUNT_BALANCE);
   }
}

double SlaveDailyLoss()
{
   ResetSlaveDaily();
   return MathMax(0.0, (g_DailyStart - AccountInfoDouble(ACCOUNT_EQUITY)) / MathMax(g_DailyStart, 1.0) * 100.0);
}

bool SlaveConnect()
{
   if(g_Socket != INVALID_HANDLE && SocketIsConnected(g_Socket)) return true;
   g_Socket = SocketCreate();
   if(g_Socket == INVALID_HANDLE) return false;
   if(!SocketConnect(g_Socket, CopierServerIP, CopierServerPort, 3000))
   {
      SocketClose(g_Socket);
      g_Socket = INVALID_HANDLE;
      return false;
   }
   uchar hello[];
   StringToCharArray("{\"role\":\"slave\"}\n", hello, 0, WHOLE_ARRAY, CP_UTF8);
   SocketSend(g_Socket, hello, ArraySize(hello));
   return true;
}

string JsonString(string json, string key)
{
   string pat = "\"" + key + "\":\"";
   int start = StringFind(json, pat);
   if(start < 0) return "";
   start += StringLen(pat);
   int end = StringFind(json, "\"", start);
   if(end < 0) return "";
   return StringSubstr(json, start, end - start);
}

double JsonNumber(string json, string key)
{
   string pat = "\"" + key + "\":";
   int start = StringFind(json, pat);
   if(start < 0) return 0.0;
   start += StringLen(pat);
   int end = start;
   while(end < StringLen(json))
   {
      ushort ch = StringGetCharacter(json, end);
      if((ch >= '0' && ch <= '9') || ch == '-' || ch == '.') end++;
      else break;
   }
   return StringToDouble(StringSubstr(json, start, end - start));
}

double SlaveLot(string symbol, double masterLot, double slPips)
{
   double minLot = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
   double maxLot = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MAX);
   double step = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);
   double lot = masterLot;
   if(UseBalanceScaling)
      lot = masterLot * AccountInfoDouble(ACCOUNT_BALANCE) / MathMax(MasterBalance, 1.0);
   else
   {
      double tickValue = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_VALUE);
      double tickSize = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_SIZE);
      double pipValue = tickValue * (SlavePipSize(symbol) / MathMax(tickSize, SymbolInfoDouble(symbol, SYMBOL_POINT)));
      lot = AccountInfoDouble(ACCOUNT_BALANCE) * SlaveRiskPercent / 100.0 / MathMax(slPips * pipValue, 0.01);
   }
   lot = MathFloor(lot / step) * step;
   return NormalizeDouble(MathMax(minLot, MathMin(maxLot, lot)), 2);
}

void ExecuteSlaveSignal(string json)
{
   if(StringFind(json, "\"action\":\"OPEN\"") < 0) return;
   if(SlaveDailyLoss() >= MathMin(MaxDailyRisk, 5.0)) return;
   string symbol = JsonString(json, "symbol");
   if(symbol == "") return;
   int type = (int)JsonNumber(json, "type");
   double masterLot = JsonNumber(json, "lot");
   double masterPrice = JsonNumber(json, "price");
   double sl = JsonNumber(json, "sl");
   double tp = JsonNumber(json, "tp");
   if(sl <= 0.0 || tp <= 0.0) return;
   SymbolSelect(symbol, true);
   double ask = SymbolInfoDouble(symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(symbol, SYMBOL_BID);
   double entry = type == 1 ? ask : bid;
   if(MathAbs(entry - masterPrice) > MaxSlippagePips * SlavePipSize(symbol)) return;
   double slPips = MathAbs(entry - sl) / SlavePipSize(symbol);
   double lot = SlaveLot(symbol, masterLot, slPips);
   bool ok = type == 1 ? slaveTrade.Buy(lot, symbol, ask, sl, tp, "AB_SLAVE")
                       : slaveTrade.Sell(lot, symbol, bid, sl, tp, "AB_SLAVE");
   if(!ok) Print("Slave order failed: ", slaveTrade.ResultRetcodeDescription());
}

int OnInit()
{
   slaveTrade.SetExpertMagicNumber(MagicNumber);
   ResetSlaveDaily();
   EventSetMillisecondTimer(PollIntervalMS);
   SlaveConnect();
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   if(g_Socket != INVALID_HANDLE) SocketClose(g_Socket);
}

void OnTimer()
{
   ResetSlaveDaily();
   if(!SlaveConnect()) return;
   uchar data[];
   ArrayResize(data, 8192);
   uint read = SocketRead(g_Socket, data, 8192, 20);
   if(read > 0)
   {
      string msg = CharArrayToString(data, 0, (int)read, CP_UTF8);
      ExecuteSlaveSignal(msg);
   }
}
