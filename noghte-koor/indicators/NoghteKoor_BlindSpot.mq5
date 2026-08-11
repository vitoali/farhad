//+------------------------------------------------------------------+
//|                                      NoghteKoor_BlindSpot.mq5    |
//|  Blind Spot / نقطه کور — نسخه MetaTrader 5                        |
//+------------------------------------------------------------------+
#property copyright "Educational Blind Spot"
#property version   "1.00"
#property indicator_chart_window
#property indicator_plots 0

input int    ATR_Period       = 14;
input int    IDR_Period       = 20;
input double TH_Percent       = 0.6666;
input int    RangeMode        = 0; // 0 Auto, 1 TH, 2 ATR, 3 IDR
input int    SwingLen         = 5;
input double MinBreakBodyPct  = 50.0;
input int    ClassicValidBars = 1;
input double EntryOffsetPct   = 80.0;
input double TP_Mult          = 2.0;
input bool   UseClassic       = true;
input bool   UseLive          = true;
input double LiveFillPct      = 100.0;
input color  ZoneColor        = clrGoldenrod;
input color  LevelColor       = clrDodgerBlue;
input color  BullColor        = clrLime;
input color  BearColor        = clrTomato;

string PREFIX = "NKBS5_";

double PipSize()
{
   if(_Digits == 3 || _Digits == 5) return _Point * 10.0;
   return _Point;
}
double ToPips(const double v){ return v / PipSize(); }

double CalcIDR(const int shift)
{
   double sum = 0.0;
   for(int i=shift; i<shift+IDR_Period; i++)
      sum += (iHigh(_Symbol, _Period, i) - iLow(_Symbol, _Period, i));
   return sum / IDR_Period;
}

double CalcTH(const int shift)
{
   return iClose(_Symbol, _Period, shift) * (TH_Percent / 100.0);
}

double SelectedRange(const int shift)
{
   double th  = CalcTH(shift);
   double atr = iATR(_Symbol, _Period, ATR_Period, shift);
   double idr = CalcIDR(shift);
   if(RangeMode == 1) return th;
   if(RangeMode == 2) return atr;
   if(RangeMode == 3) return idr;
   return MathMax(th, MathMax(atr, idr));
}

bool IsLongBar(const int shift, const double atrRef)
{
   return (iHigh(_Symbol,_Period,shift)-iLow(_Symbol,_Period,shift)) >= atrRef * (MinBreakBodyPct/100.0);
}

void ClearObjects()
{
   int total = ObjectsTotal(0, 0, -1);
   for(int i=total-1; i>=0; i--)
   {
      string name = ObjectName(0, i, 0, -1);
      if(StringFind(name, PREFIX) == 0)
         ObjectDelete(0, name);
   }
}

void DrawHLine(const string name, const double price, const color clr, const int style=STYLE_DASH, const int width=2)
{
   if(ObjectFind(0, name) < 0)
      ObjectCreate(0, name, OBJ_HLINE, 0, 0, price);
   ObjectSetDouble(0, name, OBJPROP_PRICE, price);
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, name, OBJPROP_STYLE, style);
   ObjectSetInteger(0, name, OBJPROP_WIDTH, width);
}

void DrawRect(const string name, const datetime t1, const double p1, const datetime t2, const double p2, const color clr)
{
   if(ObjectFind(0, name) >= 0) ObjectDelete(0, name);
   ObjectCreate(0, name, OBJ_RECTANGLE, 0, t1, p1, t2, p2);
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, name, OBJPROP_FILL, true);
   ObjectSetInteger(0, name, OBJPROP_BACK, true);
}

void DrawLabel(const string name, const int x, const int y, const string text, const color clr)
{
   if(ObjectFind(0, name) < 0)
      ObjectCreate(0, name, OBJ_LABEL, 0, 0, 0);
   ObjectSetInteger(0, name, OBJPROP_CORNER, CORNER_RIGHT_UPPER);
   ObjectSetInteger(0, name, OBJPROP_XDISTANCE, x);
   ObjectSetInteger(0, name, OBJPROP_YDISTANCE, y);
   ObjectSetString(0, name, OBJPROP_TEXT, text);
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE, 10);
}

int FindSwingHigh(const int fromBar, const int len)
{
   int bars = Bars(_Symbol, _Period);
   for(int i=fromBar+len; i<bars-len-2; i++)
   {
      bool isPH = true;
      double h = iHigh(_Symbol,_Period,i);
      for(int k=1; k<=len; k++)
      {
         if(h <= iHigh(_Symbol,_Period,i-k) || h < iHigh(_Symbol,_Period,i+k)) { isPH=false; break; }
      }
      if(isPH) return i;
   }
   return -1;
}

int FindSwingLow(const int fromBar, const int len)
{
   int bars = Bars(_Symbol, _Period);
   for(int i=fromBar+len; i<bars-len-2; i++)
   {
      bool isPL = true;
      double l = iLow(_Symbol,_Period,i);
      for(int k=1; k<=len; k++)
      {
         if(l >= iLow(_Symbol,_Period,i-k) || l > iLow(_Symbol,_Period,i+k)) { isPL=false; break; }
      }
      if(isPL) return i;
   }
   return -1;
}

int OnInit()
{
   ClearObjects();
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason)
{
   ClearObjects();
}

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
   if(rates_total < MathMax(ATR_Period, IDR_Period) + SwingLen + 10)
      return(0);

   double th0  = CalcTH(0);
   double atr0 = iATR(_Symbol, _Period, ATR_Period, 0);
   double idr0 = CalcIDR(0);
   double rng0 = SelectedRange(0);
   double live = high[rates_total-1] - low[rates_total-1];
   // safer via series
   live = iHigh(_Symbol,_Period,0) - iLow(_Symbol,_Period,0);
   double fill = (rng0 > 0.0 ? (live/rng0)*100.0 : 0.0);

   int periodSec = PeriodSeconds(_Period);
   int elapsed   = (int)(TimeCurrent() - iTime(_Symbol,_Period,0));
   double remainPct = periodSec > 0 ? MathMax(0.0, 100.0*(1.0 - (double)elapsed/periodSec)) : 0.0;
   bool liveReady = UseLive && (fill >= LiveFillPct) && (remainPct > 0.0);

   DrawLabel(PREFIX+"L1", 20, 20, "Blind Spot | نقطه کور MT5", clrWhite);
   DrawLabel(PREFIX+"L2", 20, 40, StringFormat("TH: %.1f pips", ToPips(th0)), clrDodgerBlue);
   DrawLabel(PREFIX+"L3", 20, 60, StringFormat("ATR: %.1f pips", ToPips(atr0)), clrDodgerBlue);
   DrawLabel(PREFIX+"L4", 20, 80, StringFormat("IDR: %.1f pips", ToPips(idr0)), clrDodgerBlue);
   DrawLabel(PREFIX+"L5", 20, 100, StringFormat("Range: %.1f | Live: %.1f (%.0f%%)", ToPips(rng0), ToPips(live), fill), clrGold);
   DrawLabel(PREFIX+"L6", 20, 120, StringFormat("Remain: %.0f%% | LiveBS: %s", remainPct, liveReady ? "READY" : "WAIT"), liveReady ? clrMagenta : clrSilver);

   if(UseLive)
   {
      double top = MathMax(iOpen(_Symbol,_Period,1), iClose(_Symbol,_Period,1));
      double bot = MathMin(iOpen(_Symbol,_Period,1), iClose(_Symbol,_Period,1));
      DrawRect(PREFIX+"LIVEZONE", iTime(_Symbol,_Period,1), top, iTime(_Symbol,_Period,0) + periodSec*3, bot, liveReady ? clrOrchid : clrDimGray);
   }

   if(UseClassic)
   {
      int sh = FindSwingHigh(1, SwingLen);
      int sl = FindSwingLow(1, SwingLen);
      bool found = false;
      int dir = 0;
      double level = 0, breakRange = 0;
      int breakBar = -1;
      int bars = Bars(_Symbol,_Period);

      for(int i=2; i<MathMin(40, bars-5); i++)
      {
         double atr1 = iATR(_Symbol,_Period,ATR_Period,i);
         if(sh > i)
         {
            double lvl = iHigh(_Symbol,_Period,sh);
            if(iClose(_Symbol,_Period,i) < lvl && iClose(_Symbol,_Period,i+1) >= lvl && IsLongBar(i, atr1))
            {
               double r = SelectedRange(i);
               for(int j=i-1; j>=MathMax(0, i-ClassicValidBars-2); j--)
               {
                  if((lvl - iLow(_Symbol,_Period,j)) >= r)
                  {
                     found=true; dir=-1; level=lvl; breakRange=r; breakBar=i; break;
                  }
               }
            }
         }
         if(found) break;
         if(sl > i)
         {
            double lvl = iLow(_Symbol,_Period,sl);
            if(iClose(_Symbol,_Period,i) > lvl && iClose(_Symbol,_Period,i+1) <= lvl && IsLongBar(i, atr1))
            {
               double r = SelectedRange(i);
               for(int j=i-1; j>=MathMax(0, i-ClassicValidBars-2); j--)
               {
                  if((iHigh(_Symbol,_Period,j) - lvl) >= r)
                  {
                     found=true; dir=1; level=lvl; breakRange=r; breakBar=i; break;
                  }
               }
            }
         }
         if(found) break;
      }

      if(found)
      {
         bool valid = (breakBar >= 1 && breakBar <= ClassicValidBars + 1);
         double offset = breakRange * ((100.0 - EntryOffsetPct)/100.0);
         double entry, slp, tp;
         if(dir < 0)
         {
            entry = level - offset;
            slp   = entry + (breakRange - offset);
            tp    = entry - breakRange * TP_Mult;
         }
         else
         {
            entry = level + offset;
            slp   = entry - (breakRange - offset);
            tp    = entry + breakRange * TP_Mult;
         }
         DrawHLine(PREFIX+"LEVEL", level, LevelColor, STYLE_DASH, 2);
         DrawHLine(PREFIX+"ENTRY", entry, dir < 0 ? BearColor : BullColor, STYLE_SOLID, 2);
         DrawHLine(PREFIX+"SL", slp, BearColor, STYLE_DOT, 1);
         DrawHLine(PREFIX+"TP", tp, BullColor, STYLE_DOT, 1);
         DrawRect(PREFIX+"CLASSZONE", iTime(_Symbol,_Period,MathMin(breakBar, bars-1)), MathMax(level, entry),
                  iTime(_Symbol,_Period,0) + periodSec*2, MathMin(level, entry), ZoneColor);
         DrawLabel(PREFIX+"L7", 20, 140,
            StringFormat("Classic BS: %s | Entry %.5f | valid=%s", dir < 0 ? "SELL" : "BUY", entry, valid ? "YES" : "NO"),
            valid ? clrOrange : clrGray);
      }
      else DrawLabel(PREFIX+"L7", 20, 140, "Classic BS: —", clrGray);
   }
   return(rates_total);
}
//+------------------------------------------------------------------+
