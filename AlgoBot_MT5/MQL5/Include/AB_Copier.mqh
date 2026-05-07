#ifndef AB_COPIER_MQH
#define AB_COPIER_MQH

int g_CopierSocket = INVALID_HANDLE;
string g_CopierHost = "127.0.0.1";
int g_CopierPort = 5555;

bool InitCopierServer(string host, int port)
{
   g_CopierHost = host;
   g_CopierPort = port;
   g_CopierSocket = SocketCreate();
   if(g_CopierSocket == INVALID_HANDLE)
   {
      Print("Copier socket create failed: ", GetLastError());
      return false;
   }
   if(!SocketConnect(g_CopierSocket, g_CopierHost, g_CopierPort, 3000))
   {
      Print("Copier socket connect failed. Python server may be offline.");
      SocketClose(g_CopierSocket);
      g_CopierSocket = INVALID_HANDLE;
      return false;
   }
   return true;
}

bool EnsureCopierConnected()
{
   if(g_CopierSocket != INVALID_HANDLE && SocketIsConnected(g_CopierSocket)) return true;
   return InitCopierServer(g_CopierHost, g_CopierPort);
}

bool SendSignalToCopier(string json)
{
   if(!EnsureCopierConnected()) return false;
   uchar data[];
   StringToCharArray(json + "\n", data, 0, WHOLE_ARRAY, CP_UTF8);
   int sent = SocketSend(g_CopierSocket, data, ArraySize(data));
   if(sent <= 0)
   {
      Print("Copier send failed: ", GetLastError());
      SocketClose(g_CopierSocket);
      g_CopierSocket = INVALID_HANDLE;
      return false;
   }
   return true;
}

void BroadcastSignalToSlaves()
{
   if(!IsMasterAccount) return;
   string state = "{\"action\":\"HEARTBEAT\",\"symbol\":\"" + Symbol() + "\",\"score\":" + IntegerToString(g_SignalScore) +
                  ",\"direction\":" + IntegerToString(g_StrategyDirection) + ",\"time\":" + IntegerToString((int)TimeCurrent()) + "}";
   SendSignalToCopier(state);
}

void BroadcastTradeToSlaves(string symbol, int direction, double lot, double price, double sl, double tp, int score)
{
   if(!IsMasterAccount) return;
   string json = "{\"action\":\"OPEN\",\"symbol\":\"" + symbol + "\",\"type\":" + IntegerToString(direction > 0 ? 1 : 0) +
                 ",\"lot\":" + DoubleToString(lot, 2) +
                 ",\"price\":" + DoubleToString(price, (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS)) +
                 ",\"sl\":" + DoubleToString(sl, (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS)) +
                 ",\"tp\":" + DoubleToString(tp, (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS)) +
                 ",\"magic\":" + IntegerToString(MagicNumber) +
                 ",\"score\":" + IntegerToString(score) +
                 ",\"time\":" + IntegerToString((int)TimeCurrent()) + "}";
   SendSignalToCopier(json);
}

string ReadSignalFromCopier()
{
   if(!EnsureCopierConnected()) return "";
   uchar data[];
   ArrayResize(data, 8192);
   uint read = SocketRead(g_CopierSocket, data, 8192, 10);
   if(read <= 0) return "";
   return CharArrayToString(data, 0, (int)read, CP_UTF8);
}

#endif
