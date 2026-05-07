#ifndef AB_PROPFIRM_MQH
#define AB_PROPFIRM_MQH

struct PropFirmStatus
{
   double dailyLossUsed;
   double totalLossUsed;
   double profitProgress;
   int    daysTraded;
   bool   isCompliant;
   string warning;
};

double g_ChallengeStartBalance = 0.0;
string g_PropFirmName = "FTMO";

void InitPropFirmRules(string firmName)
{
   g_PropFirmName = firmName;
   g_ChallengeStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   Print("AB_PropFirm initialized: ", g_PropFirmName);
}

double GetChallengeStartBalance()
{
   if(g_ChallengeStartBalance <= 0.0) g_ChallengeStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   return g_ChallengeStartBalance;
}

int GetTradedDays()
{
   if(!HistorySelect(TimeCurrent() - 86400 * 90, TimeCurrent())) return 0;
   string days = "";
   int count = 0;
   for(int i = 0; i < HistoryDealsTotal(); i++)
   {
      ulong deal = HistoryDealGetTicket(i);
      if((int)HistoryDealGetInteger(deal, DEAL_MAGIC) != MagicNumber) continue;
      datetime t = (datetime)HistoryDealGetInteger(deal, DEAL_TIME);
      MqlDateTime dt;
      TimeToStruct(t, dt);
      string key = IntegerToString(dt.year) + "-" + IntegerToString(dt.mon) + "-" + IntegerToString(dt.day);
      if(StringFind(days, key) < 0)
      {
         days += key + ";";
         count++;
      }
   }
   return count;
}

PropFirmStatus GetPropFirmStatus()
{
   PropFirmStatus status;
   double startBal = MathMax(g_DailyStartBalance, 1.0);
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double challengeStart = GetChallengeStartBalance();
   status.dailyLossUsed = MathMax(0.0, (startBal - equity) / startBal * 100.0);
   status.totalLossUsed = MathMax(0.0, (challengeStart - equity) / challengeStart * 100.0);
   status.profitProgress = (equity - challengeStart) / challengeStart * 100.0;
   status.daysTraded = GetTradedDays();
   status.isCompliant = status.dailyLossUsed < PropFirm_MaxDailyLoss && status.totalLossUsed < PropFirm_MaxTotalLoss;
   status.warning = "";
   if(status.dailyLossUsed > PropFirm_MaxDailyLoss * 0.8) status.warning = "Daily loss limit is near.";
   if(status.totalLossUsed > PropFirm_MaxTotalLoss * 0.8) status.warning = "Total loss limit is near.";
   return status;
}

bool IsNewsTime(int minutesWindow)
{
   int handle = FileOpen("Config/high_impact_news.csv", FILE_READ | FILE_CSV | FILE_COMMON);
   if(handle == INVALID_HANDLE) return false;
   datetime now = TimeGMT();
   bool blocked = false;
   while(!FileIsEnding(handle))
   {
      string rawTime = FileReadString(handle);
      string impact = FileReadString(handle);
      string name = FileReadString(handle);
      if(rawTime == "") continue;
      datetime eventTime = StringToTime(rawTime);
      if((impact == "high" || impact == "3") && MathAbs((int)(eventTime - now)) <= minutesWindow * 60)
      {
         blocked = true;
         Print("News filter blocked trading: ", name);
         break;
      }
   }
   FileClose(handle);
   return blocked;
}

bool PropFirmRulesOK()
{
   PropFirmStatus status = GetPropFirmStatus();
   if(!status.isCompliant)
   {
      g_TradingEnabled = false;
      SendTelegramMessage("<b>Prop firm rule breach guard</b>: trading stopped before violation.");
      return false;
   }
   MqlDateTime dt;
   TimeToStruct(TimeGMT(), dt);
   if(dt.day_of_week == 5 && dt.hour >= 21)
   {
      CloseAllPositions();
      return false;
   }
   return true;
}

#endif
