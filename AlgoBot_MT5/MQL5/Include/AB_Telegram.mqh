#ifndef AB_TELEGRAM_MQH
#define AB_TELEGRAM_MQH

string g_TelegramToken = "";
string g_TelegramChatID = "";

string UrlEncode(string text)
{
   string out = "";
   for(int i = 0; i < StringLen(text); i++)
   {
      ushort ch = StringGetCharacter(text, i);
      if((ch >= 'A' && ch <= 'Z') || (ch >= 'a' && ch <= 'z') || (ch >= '0' && ch <= '9'))
         out += ShortToString(ch);
      else if(ch == ' ')
         out += "%20";
      else if(ch == '\n')
         out += "%0A";
      else
         out += "%" + StringFormat("%02X", ch);
   }
   return out;
}

void InitTelegram(string token, string chatId)
{
   g_TelegramToken = token;
   g_TelegramChatID = chatId;
}

bool SendTelegramMessage(string text)
{
   if(g_TelegramToken == "" || g_TelegramChatID == "") return false;
   string url = "https://api.telegram.org/bot" + g_TelegramToken + "/sendMessage";
   string body = "chat_id=" + g_TelegramChatID + "&parse_mode=HTML&text=" + UrlEncode(text);
   uchar post[];
   uchar result[];
   string headers = "Content-Type: application/x-www-form-urlencoded\r\n";
   string resultHeaders = "";
   StringToCharArray(body, post, 0, WHOLE_ARRAY, CP_UTF8);
   ResetLastError();
   int code = WebRequest("POST", url, headers, 10000, post, result, resultHeaders);
   if(code != 200)
   {
      Print("Telegram WebRequest failed. HTTP=", code, " error=", GetLastError());
      return false;
   }
   return true;
}

void SendTradeTelegram(string symbol, int direction, double lot, double entry, double sl, double tp, int score)
{
   if(!SendTradeAlerts) return;
   string side = direction > 0 ? "BUY" : "SELL";
   string msg = "<b>AlgoBot trade</b>\n" +
                "Symbol: " + symbol + "\n" +
                "Side: " + side + "\n" +
                "Lot: " + DoubleToString(lot, 2) + "\n" +
                "Entry: " + DoubleToString(entry, (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS)) + "\n" +
                "SL: " + DoubleToString(sl, (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS)) + "\n" +
                "TP: " + DoubleToString(tp, (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS)) + "\n" +
                "Score: " + IntegerToString(score);
   SendTelegramMessage(msg);
}

#endif
