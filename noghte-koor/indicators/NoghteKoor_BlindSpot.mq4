//+------------------------------------------------------------------+
//|                                      NoghteKoor_BlindSpot.mq4    |
//|  استراتژی نقطه کور (Blind Spot)                                  |
//|  مبتنی بر رفتارشناسی حرکت قیمت + ویدیوهای آموزشی نقطه کور       |
//|  نمایش: TH / ATR / IDR / LiveRange + نواحی کلاسیک و لایو        |
//+------------------------------------------------------------------+
#property copyright "Educational Blind Spot"
#property version   "1.00"
#property strict
#property indicator_chart_window
#property indicator_buffers 0

//--- inputs
extern int    ATR_Period        = 14;
extern int    IDR_Period        = 20;
extern double TH_Percent        = 0.6666;   // توان حرکتی = % قیمت
extern int    RangeMode         = 0;        // 0=Auto Max, 1=TH, 2=ATR, 3=IDR
extern int    SwingLen          = 5;
extern double MinBreakBodyPct   = 50.0;
extern int    ClassicValidBars  = 1;
extern double EntryOffsetPct    = 80.0;
extern double TP_Mult           = 2.0;
extern bool   UseClassic        = true;
extern bool   UseLive           = true;
extern double LiveFillPct       = 100.0;
extern color  ZoneColor         = clrGoldenrod;
extern color  LevelColor        = clrDodgerBlue;
extern color  BullColor         = clrLime;
extern color  BearColor         = clrTomato;

string PREFIX = "NKBS_";

//+------------------------------------------------------------------+
double PipSize()
{
   if(Digits == 3 || Digits == 5) return Point * 10.0;
   return Point;
}

double ToPips(double v){ return v / PipSize(); }

double CalcATR(int period, int shift)
{
   return iATR(NULL, 0, period, shift);
}

double CalcIDR(int period, int shift)
{
   double sum = 0.0;
   for(int i=shift; i<shift+period; i++)
      sum += (High[i] - Low[i]);
   return sum / period;
}

double CalcTH(int shift)
{
   return Close[shift] * (TH_Percent / 100.0);
}

double SelectedRange(int shift)
{
   double th  = CalcTH(shift);
   double atr = CalcATR(ATR_Period, shift);
   double idr = CalcIDR(IDR_Period, shift);
   if(RangeMode == 1) return th;
   if(RangeMode == 2) return atr;
   if(RangeMode == 3) return idr;
   return MathMax(th, MathMax(atr, idr));
}

bool IsLongBar(int shift, double atrRef)
{
   return (High[shift]-Low[shift]) >= atrRef * (MinBreakBodyPct/100.0);
}

int FindSwingHigh(int fromBar, int len)
{
   for(int i=fromBar+len; i<Bars-len-2; i++)
   {
      bool isPH = true;
      for(int k=1; k<=len; k++)
      {
         if(High[i] <= High[i-k] || High[i] < High[i+k]) { isPH=false; break; }
      }
      if(isPH) return i;
   }
   return -1;
}

int FindSwingLow(int fromBar, int len)
{
   for(int i=fromBar+len; i<Bars-len-2; i++)
   {
      bool isPL = true;
      for(int k=1; k<=len; k++)
      {
         if(Low[i] >= Low[i-k] || Low[i] > Low[i+k]) { isPL=false; break; }
      }
      if(isPL) return i;
   }
   return -1;
}

void ClearObjects()
{
   int total = ObjectsTotal();
   for(int i=total-1; i>=0; i--)
   {
      string name = ObjectName(i);
      if(StringFind(name, PREFIX) == 0)
         ObjectDelete(name);
   }
}

void DrawHLine(string name, double price, color clr, int style=STYLE_DASH, int width=2)
{
   if(ObjectFind(name) < 0)
      ObjectCreate(name, OBJ_HLINE, 0, 0, price);
   ObjectSet(name, OBJPROP_PRICE1, price);
   ObjectSet(name, OBJPROP_COLOR, clr);
   ObjectSet(name, OBJPROP_STYLE, style);
   ObjectSet(name, OBJPROP_WIDTH, width);
}

void DrawRect(string name, datetime t1, double p1, datetime t2, double p2, color clr)
{
   if(ObjectFind(name) >= 0) ObjectDelete(name);
   ObjectCreate(name, OBJ_RECTANGLE, 0, t1, p1, t2, p2);
   ObjectSet(name, OBJPROP_COLOR, clr);
   ObjectSet(name, OBJPROP_STYLE, STYLE_SOLID);
   ObjectSet(name, OBJPROP_WIDTH, 1);
   ObjectSet(name, OBJPROP_BACK, true);
}

void DrawLabel(string name, int x, int y, string text, color clr)
{
   if(ObjectFind(name) < 0)
      ObjectCreate(name, OBJ_LABEL, 0, 0, 0);
   ObjectSet(name, OBJPROP_CORNER, CORNER_RIGHT_UPPER);
   ObjectSet(name, OBJPROP_XDISTANCE, x);
   ObjectSet(name, OBJPROP_YDISTANCE, y);
   ObjectSetText(name, text, 10, "Arial", clr);
}

//+------------------------------------------------------------------+
int OnInit()
{
   ClearObjects();
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason)
{
   ClearObjects();
}

//+------------------------------------------------------------------+
int OnCalculate(const int rates_total,
                const int prev_calculated,
                const datetime &time[],
                const double &open[],
                const double &high[],
                const double &low[],
                const double &close[],
                const long &tick_volume[],
                const long &volume[],
                const int &spread[])
{
   if(Bars < MathMax(ATR_Period, IDR_Period) + SwingLen + 10)
      return(0);

   double th0  = CalcTH(0);
   double atr0 = CalcATR(ATR_Period, 0);
   double idr0 = CalcIDR(IDR_Period, 0);
   double rng0 = SelectedRange(0);
   double live = High[0] - Low[0];
   double fill = (rng0 > 0.0 ? (live/rng0)*100.0 : 0.0);

   // remaining time of current candle (%)
   int periodSec = Period() * 60;
   int elapsed   = (int)(TimeCurrent() - Time[0]);
   double remainPct = periodSec > 0 ? MathMax(0.0, 100.0*(1.0 - (double)elapsed/periodSec)) : 0.0;
   bool liveReady = UseLive && (fill >= LiveFillPct) && (remainPct > 0.0);

   // Dashboard
   DrawLabel(PREFIX+"L1", 20, 20, "Blind Spot | نقطه کور", clrWhite);
   DrawLabel(PREFIX+"L2", 20, 40, StringFormat("TH: %.1f pips", ToPips(th0)), clrDodgerBlue);
   DrawLabel(PREFIX+"L3", 20, 60, StringFormat("ATR: %.1f pips", ToPips(atr0)), clrDodgerBlue);
   DrawLabel(PREFIX+"L4", 20, 80, StringFormat("IDR: %.1f pips", ToPips(idr0)), clrDodgerBlue);
   DrawLabel(PREFIX+"L5", 20, 100, StringFormat("Range: %.1f | Live: %.1f (%.0f%%)", ToPips(rng0), ToPips(live), fill), clrGold);
   DrawLabel(PREFIX+"L6", 20, 120, StringFormat("Remain: %.0f%% | LiveBS: %s", remainPct, liveReady ? "READY" : "WAIT"), liveReady ? clrMagenta : clrSilver);

   // Live Blind Spot zone = previous candle Open/Close
   if(UseLive)
   {
      double top = MathMax(Open[1], Close[1]);
      double bot = MathMin(Open[1], Close[1]);
      DrawRect(PREFIX+"LIVEZONE", Time[1], top, Time[0] + Period()*60*3, bot, liveReady ? clrOrchid : clrDimGray);
   }

   // Classic Blind Spot scan (recent bars)
   if(UseClassic)
   {
      int sh = FindSwingHigh(1, SwingLen);
      int sl = FindSwingLow(1, SwingLen);

      // Look for latest breakout within last 30 bars
      bool found = false;
      int dir = 0; // -1 sell, +1 buy
      double level = 0, breakRange = 0;
      int breakBar = -1;

      for(int i=2; i<MathMin(40, Bars-5); i++)
      {
         double atr1 = CalcATR(ATR_Period, i);
         // break down through recent swing high that existed before bar i
         if(sh > i)
         {
            double lvl = High[sh];
            if(Close[i] < lvl && Close[i+1] >= lvl && IsLongBar(i, atr1))
            {
               // distance check on subsequent bar(s)
               double r = SelectedRange(i);
               for(int j=i-1; j>=MathMax(0, i-ClassicValidBars-2); j--)
               {
                  if((lvl - Low[j]) >= r)
                  {
                     found = true; dir = -1; level = lvl; breakRange = r; breakBar = i;
                     break;
                  }
               }
            }
         }
         if(found) break;

         if(sl > i)
         {
            double lvl = Low[sl];
            if(Close[i] > lvl && Close[i+1] <= lvl && IsLongBar(i, atr1))
            {
               double r = SelectedRange(i);
               for(int j=i-1; j>=MathMax(0, i-ClassicValidBars-2); j--)
               {
                  if((High[j] - lvl) >= r)
                  {
                     found = true; dir = 1; level = lvl; breakRange = r; breakBar = i;
                     break;
                  }
               }
            }
         }
         if(found) break;
      }

      if(found)
      {
         int barsSince = breakBar; // because bar index 0 is current
         bool valid = (barsSince >= 1 && barsSince <= ClassicValidBars + 1);

         double offset = breakRange * ((100.0 - EntryOffsetPct)/100.0);
         double entry, sl, tp;
         if(dir < 0)
         {
            entry = level - offset;
            sl    = entry + (breakRange - offset);
            tp    = entry - breakRange * TP_Mult;
         }
         else
         {
            entry = level + offset;
            sl    = entry - (breakRange - offset);
            tp    = entry + breakRange * TP_Mult;
         }

         DrawHLine(PREFIX+"LEVEL", level, LevelColor, STYLE_DASH, 2);
         DrawHLine(PREFIX+"ENTRY", entry, dir < 0 ? BearColor : BullColor, STYLE_SOLID, 2);
         DrawHLine(PREFIX+"SL", sl, BearColor, STYLE_DOT, 1);
         DrawHLine(PREFIX+"TP", tp, BullColor, STYLE_DOT, 1);
         DrawRect(PREFIX+"CLASSZONE", Time[MathMin(breakBar, Bars-1)], MathMax(level, entry),
                  Time[0] + Period()*60*2, MathMin(level, entry), ZoneColor);

         DrawLabel(PREFIX+"L7", 20, 140,
            StringFormat("Classic BS: %s | Entry %.5f | valid=%s",
               dir < 0 ? "SELL" : "BUY", entry, valid ? "YES" : "NO"),
            valid ? clrOrange : clrGray);
      }
      else
      {
         DrawLabel(PREFIX+"L7", 20, 140, "Classic BS: —", clrGray);
      }
   }

   Comment("");
   return(rates_total);
}
//+------------------------------------------------------------------+
