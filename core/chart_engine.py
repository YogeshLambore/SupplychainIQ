"""
NEXORA Finance Visualization Engine
====================================
DatasetProfiler  -> Pandas schema analysis
IntentParser     -> Llama JSON plan + deterministic fallback
ValidationEngine -> Column/type checks before calculation
DataEngine       -> All Pandas/NumPy calculations
ChartRenderer    -> Professional Matplotlib rendering
ChartEngine      -> Orchestrator (preserves existing API)
"""

import re
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from typing import Optional

warnings.filterwarnings("ignore")

PALETTE = ["#A78BFA","#60A5FA","#34D399","#FBBF24","#F87171",
           "#E879F9","#38BDF8","#4ADE80","#FB923C","#818CF8"]
BG_COLOR    = "#1A1C22"
GRID_COLOR  = "#2B2E36"
TEXT_COLOR  = "#9CA3AF"
TITLE_COLOR = "#F3F4F6"
ACCENT      = "#A78BFA"


# ─── 1. DATASET PROFILER ─────────────────────
class DatasetProfiler:
    def profile(self, df: pd.DataFrame) -> dict:
        p = {
            "rows": len(df), "columns": len(df.columns),
            "column_names": df.columns.tolist(),
            "numeric_columns": [], "categorical_columns": [],
            "datetime_columns": [], "boolean_columns": [],
            "id_columns": [], "constant_columns": [],
            "missing_value_columns": {}, "high_cardinality_columns": [],
            "sample_values": {},
        }
        bool_vals = {True,False,0,1,"True","False","true","false",
                     "0","1","yes","no","Yes","No","YES","NO"}
        for col in df.columns:
            s = df[col]; nuniq = s.nunique(dropna=True); n = len(s)
            miss = int(s.isna().sum())
            if miss > 0: p["missing_value_columns"][col] = miss
            if nuniq <= 1: p["constant_columns"].append(col); continue
            if set(s.dropna().unique()).issubset(bool_vals):
                p["boolean_columns"].append(col); continue
            if pd.api.types.is_numeric_dtype(s):
                p["numeric_columns"].append(col)
                if pd.api.types.is_integer_dtype(s) and nuniq==n and s.is_monotonic_increasing:
                    p["id_columns"].append(col)
                continue
            if pd.api.types.is_datetime64_any_dtype(s):
                p["datetime_columns"].append(col); continue
            if s.dtype == object:
                parsed = self._try_dt(s)
                if parsed is not None: p["datetime_columns"].append(col); continue
                if nuniq > min(50, n * 0.5): p["high_cardinality_columns"].append(col)
                p["categorical_columns"].append(col)
                p["sample_values"][col] = s.dropna().unique()[:5].tolist()
        return p

    def _try_dt(self, s):
        try:
            parsed = pd.to_datetime(s, infer_datetime_format=True, errors="coerce")
            if parsed.notna().sum() / max(len(s), 1) > 0.7: return parsed
        except Exception: pass
        return None

    def build_llm_context(self, df, p, query):
        lines = [
            f"Dataset: {p['rows']:,} rows x {p['columns']} columns",
            f"Numeric: {p['numeric_columns']}",
            f"Categorical: {p['categorical_columns']}",
            f"Datetime: {p['datetime_columns']}",
        ]
        if p["missing_value_columns"]:
            lines.append(f"Missing in: {list(p['missing_value_columns'].keys())}")
        for c in p["numeric_columns"][:5]:
            try:
                s = df[c].dropna()
                lines.append(f"  {c}: min={s.min():.2f} max={s.max():.2f} mean={s.mean():.2f}")
            except Exception: pass
        for c in p["categorical_columns"][:3]:
            lines.append(f"  {c} values: {df[c].dropna().value_counts().head(5).index.tolist()}")
        lines.append(f"User request: {query}")
        return "\n".join(lines)


# ─── 2. INTENT PARSER ────────────────────────
CHART_KW = {
    "corr_heatmap": ["correlation","correlations","corr matrix","heatmap of corr","correlation heatmap"],
    "heatmap":      ["heatmap"],
    "histogram":    ["histogram","distribution","dist ","frequency","spread of","how are.*distributed"],
    "scatter":      ["scatter","relationship between","versus"," vs "," against "],
    "box":          ["box plot","boxplot","quartile","outlier","iqr","box chart"],
    "pie":          ["pie chart","pie graph"],
    "donut":        ["donut","doughnut"],
    "stacked_bar":  ["stacked bar","stacked chart","stack"],
    "grouped_bar":  ["grouped bar","side by side","grouped","compare.*and.*by","approved.*rejected","rejected.*approved"],
    "hbar":         ["horizontal bar","hbar","ranked","ranking chart"],
    "area":         ["area chart","area graph"],
    "cumulative":   ["cumulative","running total","cumsum","running sum"],
    "pareto":       ["pareto","80/20","80-20"],
    "funnel":       ["funnel","conversion"],
    "time_series":  ["daily","weekly","monthly","quarterly","yearly","time series","by month","by year","by week"],
    "line":         ["line chart","line graph","trend","over time","growth over","change over"],
    "top_n":        ["top [0-9]+","bottom [0-9]+"],
    "count":        ["count of","number of","how many","frequency of"],
    "bar":          ["bar chart","bar graph","compare","total by","by region","by department","by category"],
}
AGG_KW = {
    "mean":   ["average","mean","avg"],
    "median": ["median"],
    "count":  ["count","frequency","how many","number of"],
    "min":    ["minimum","min "],
    "max":    ["maximum","max ","highest"],
    "std":    ["std","standard deviation"],
}


class IntentParser:
    def parse(self, query, df, profile, llm=None):
        plan = None
        if llm is not None:
            try:
                schema = (f"Numeric: {profile['numeric_columns']}\n"
                          f"Categorical: {profile['categorical_columns']}\n"
                          f"Datetime: {profile['datetime_columns']}")
                plan = llm.generate_viz_plan(query, schema)
            except Exception: plan = None
        return plan if plan else self._det(query, df, profile)

    def _det(self, query, df, profile):
        q = query.lower()
        ct = self._chart_type(q, profile)
        agg = self._agg(q)
        top_n = self._top_n(q)
        sort = "descending" if any(w in q for w in ["top","highest","best","most","largest"]) else "none"
        x, y, gb = self._cols(q, df, profile, ct, agg)
        fc, fo, fv = self._filter(q, df, profile)
        title = self._title(ct, x, y, agg, top_n)
        return {"chart_type":ct,"x_column":x,"y_column":y,"aggregation":agg,
                "group_by":gb,"filter_column":fc,"filter_operator":fo,"filter_value":fv,
                "sort":sort,"top_n":top_n,"title":title}

    def _chart_type(self, q, profile):
        for ctype, kwlist in CHART_KW.items():
            for kw in kwlist:
                if re.search(kw, q): return ctype
        num = profile["numeric_columns"]; cat = profile["categorical_columns"]
        dt  = profile["datetime_columns"]
        if dt and num: return "time_series"
        if len(num) >= 3 and not cat: return "corr_heatmap"
        if len(num) >= 2 and not cat: return "scatter"
        if cat and num: return "bar"
        if num: return "histogram"
        if cat: return "count"
        return "bar"

    def _agg(self, q):
        for agg, kwlist in AGG_KW.items():
            for kw in kwlist:
                if kw in q: return agg
        return "sum"

    def _top_n(self, q):
        m = re.search(r"top\s+(\d+)", q)
        if m: return int(m.group(1))
        m = re.search(r"bottom\s+(\d+)", q)
        if m: return int(m.group(1))
        return None

    def _cols(self, q, df, profile, ct, agg):
        num = profile["numeric_columns"]; cat = profile["categorical_columns"]
        dt  = profile["datetime_columns"]; cols = df.columns.tolist()
        mentioned = [c for c in cols if c.lower().replace("_"," ") in q]
        mn = [c for c in mentioned if c in num]
        mc = [c for c in mentioned if c in cat]
        md = [c for c in mentioned if c in dt]
        x = y = gb = None
        if ct in ("corr_heatmap","heatmap"): return None, None, None
        if ct == "histogram":
            x = mn[0] if mn else (num[0] if num else None); return x, None, None
        if ct == "scatter":
            x = mn[0] if len(mn)>=1 else (num[0] if num else None)
            y = mn[1] if len(mn)>=2 else (num[1] if len(num)>=2 else None); return x, y, None
        if ct in ("line","time_series","area","moving_avg","cumulative"):
            x = md[0] if md else (dt[0] if dt else (mc[0] if mc else (cat[0] if cat else None)))
            y = mn[0] if mn else (num[0] if num else None); return x, y, None
        if ct == "box":
            y = mn[0] if mn else (num[0] if num else None)
            x = mc[0] if mc else (cat[0] if cat else None); return x, y, None
        if ct in ("grouped_bar","stacked_bar"):
            x = mc[0] if mc else (cat[0] if cat else None)
            y = mn[0] if mn else (num[0] if num else None)
            gb = mc[1] if len(mc)>=2 else (cat[1] if len(cat)>=2 else None); return x, y, gb
        if ct == "count":
            x = mc[0] if mc else (cat[0] if cat else None); return x, None, None
        if agg == "count":
            x = mc[0] if mc else (cat[0] if cat else None)
        else:
            x = mc[0] if mc else (cat[0] if cat else None)
            y = mn[0] if mn else (num[0] if num else None)
        return x, y, None

    def _filter(self, q, df, profile):
        m = re.search(r"\b(for|in|year|during)\s+(\d{4})\b", q)
        if m:
            for col in profile["datetime_columns"]: return col, "year_eq", m.group(2)
        m = re.search(r"(above|over|greater than|more than|below|under|less than)\s+([\d,]+)", q)
        if m:
            op = "gte" if m.group(1) in ("above","over","greater than","more than") else "lte"
            val = m.group(2).replace(",","")
            for col in profile["numeric_columns"]:
                if col.lower().replace("_"," ") in q: return col, op, float(val)
        return None, None, None

    def _title(self, ct, x, y, agg, top_n):
        al = {"sum":"Total","mean":"Average","count":"Count","median":"Median","min":"Minimum","max":"Maximum"}
        a = al.get(agg, agg.capitalize())
        if top_n: return f"Top {top_n} {x or 'Items'} by {a} {y or ''}".strip()
        if ct in ("corr_heatmap","heatmap"): return "Correlation Heatmap"
        if ct == "histogram": return f"Distribution of {x or ''}"
        if ct == "scatter": return f"{y or ''} vs {x or ''}"
        if ct == "box": return f"Distribution of {y or ''} by {x or ''}"
        if y: return f"{a} {y} by {x or ''}".strip()
        if x: return f"{x} Analysis"
        return "Data Visualization"


# ─── 3. VALIDATION ENGINE ────────────────────
class ValidationEngine:
    def validate(self, plan, df, profile):
        ct = plan.get("chart_type","bar")
        plan["x_column"] = self._res(plan.get("x_column"), df)
        plan["y_column"] = self._res(plan.get("y_column"), df)
        plan["group_by"] = self._res(plan.get("group_by"), df)
        x, y = plan["x_column"], plan["y_column"]
        if ct in ("corr_heatmap","heatmap"):
            if len(profile["numeric_columns"]) < 2:
                return False, f"Need at least 2 numeric columns. Found: {profile['numeric_columns']}"
            return True, ""
        if ct == "histogram":
            if not x:
                if profile["numeric_columns"]: plan["x_column"] = profile["numeric_columns"][0]
                else: return False, "Histogram needs a numeric column."
            return True, ""
        if ct == "scatter":
            if not x or not y:
                if len(profile["numeric_columns"]) >= 2:
                    plan["x_column"],plan["y_column"] = profile["numeric_columns"][0],profile["numeric_columns"][1]
                else: return False, f"Scatter needs 2 numeric columns. Have: {profile['numeric_columns']}"
            return True, ""
        if ct in ("bar","hbar","top_n","ranking","pareto"):
            if not x:
                if profile["categorical_columns"]: plan["x_column"] = profile["categorical_columns"][0]
                else: return False, "Bar chart needs a categorical column."
            if not y and profile["numeric_columns"] and plan.get("aggregation") != "count":
                plan["y_column"] = profile["numeric_columns"][0]
            return True, ""
        if ct in ("line","time_series","area","moving_avg","cumulative"):
            if not y:
                if profile["numeric_columns"]: plan["y_column"] = profile["numeric_columns"][0]
                else: return False, "Line chart needs a numeric column."
            return True, ""
        return True, ""

    def _res(self, col, df):
        if not col: return None
        if col in df.columns: return col
        cl = col.lower().replace("_"," ").replace("-"," ")
        for c in df.columns:
            if c.lower().replace("_"," ").replace("-"," ") == cl: return c
        for c in df.columns:
            if cl in c.lower() or c.lower() in cl: return c
        return col


# ─── 4. DATA ENGINE ──────────────────────────
class DataEngine:
    def calculate(self, plan, df, profile):
        ct = plan["chart_type"]; x = plan.get("x_column"); y = plan.get("y_column")
        agg = plan.get("aggregation","sum"); gb = plan.get("group_by")
        top_n = plan.get("top_n"); sort = plan.get("sort","none")
        fc,fo,fv = plan.get("filter_column"),plan.get("filter_operator"),plan.get("filter_value")
        wdf = df.copy()
        if fc and fo and fv is not None and fc in wdf.columns:
            wdf = self._flt(wdf, fc, fo, fv)
        rows_used = len(wdf)
        if ct in ("corr_heatmap","heatmap"):
            nc = [c for c in profile["numeric_columns"] if c in wdf.columns]
            corr = wdf[nc].corr()
            pairs = self._top_corr(corr, 5)
            summary = f"Correlation matrix ({len(nc)} vars).\nStrongest:\n" + "\n".join(
                f"  {a} <-> {b}: {v:.2f}" for a,b,v in pairs)
            return corr, summary, {"rows_used":rows_used}
        if ct == "histogram":
            s = wdf[x].dropna()
            summary = (f"Distribution of {x}: N={len(s):,} Mean={s.mean():.2f} "
                       f"Median={s.median():.2f} Min={s.min():.2f} Max={s.max():.2f} Std={s.std():.2f}")
            return s, summary, {"rows_used":rows_used}
        if ct == "scatter":
            valid = wdf[[x,y]].dropna(); cr = valid[x].corr(valid[y])
            summary = f"Scatter {y} vs {x}: {len(valid):,} points, r={cr:.3f}"
            return valid, summary, {"rows_used":rows_used}
        if ct == "box":
            summary = f"Box plot of {y or x}."
            return wdf, summary, {"rows_used":rows_used}
        if ct in ("line","time_series","area","moving_avg","cumulative"):
            result,summary = self._time_agg(wdf,x,y,agg,ct)
            return result, summary, {"rows_used":rows_used}
        if ct in ("grouped_bar","stacked_bar"):
            if gb and gb in wdf.columns and x and y and x in wdf.columns and y in wdf.columns:
                result = wdf.groupby([x,gb])[y].agg(agg).unstack(fill_value=0)
                summary = f"Grouped {agg} {y} by {x}/{gb}."
            else:
                result, summary = self._single(wdf,x,y,agg,top_n,sort)
            return result, summary, {"rows_used":rows_used}
        if ct in ("pie","donut"):
            if agg == "count" or not y:
                result = wdf[x].value_counts() if x else pd.Series(dtype=float)
                summary = f"Proportions of {x}."
            else:
                result = wdf.groupby(x)[y].agg(agg)
                summary = f"{agg.capitalize()} {y} by {x}."
            if len(result) > 8:
                top = result.nlargest(7); top["Other"] = result.iloc[7:].sum(); result = top
            return result, summary, {"rows_used":rows_used}
        if ct == "pareto":
            result, summary = self._single(wdf,x,y,agg,top_n or 20,"descending")
            return result, summary, {"rows_used":rows_used}
        result, summary = self._single(wdf,x,y,agg,top_n,sort)
        return result, summary, {"rows_used":rows_used}

    def _single(self, df, x, y, agg, top_n, sort):
        if not x or x not in df.columns: return pd.Series(dtype=float), "No categorical column."
        if agg == "count" or not y or y not in df.columns:
            result = df[x].value_counts()
            summary = f"Count {x}: {len(result)} cats. Top: {result.index[0]} ({result.iloc[0]:,})"
        else:
            try:
                result = getattr(df.groupby(x)[y], agg)()
                summary = (f"{agg.capitalize()} {y} by {x}: "
                           f"High={result.idxmax()} ({self._fmt(result.max())}), "
                           f"Low={result.idxmin()} ({self._fmt(result.min())}), {len(result)} cats")
            except Exception as e:
                return pd.Series(dtype=float), f"Calc error: {e}"
        if sort == "descending": result = result.sort_values(ascending=False)
        elif sort == "ascending": result = result.sort_values(ascending=True)
        if top_n: result = result.head(int(top_n)); summary = f"Top {top_n}:\n" + summary
        return result, summary

    def _time_agg(self, df, x, y, agg, chart_type):
        if not x or not y or x not in df.columns or y not in df.columns:
            return pd.Series(dtype=float), "No datetime/numeric column."
        tmp = df[[x,y]].dropna().copy()
        if tmp[x].dtype == object:
            tmp[x] = pd.to_datetime(tmp[x], infer_datetime_format=True, errors="coerce")
        tmp = tmp.dropna(subset=[x]).sort_values(x)
        result = tmp.groupby(x)[y].agg(agg)
        if chart_type == "cumulative": result = result.cumsum()
        elif chart_type == "moving_avg":
            w = max(3, len(result)//10); result = result.rolling(w, min_periods=1).mean()
        summary = (f"Time-series {y}: {len(result):,} pts, "
                   f"{result.index.min()} to {result.index.max()}, peak={self._fmt(result.max())}")
        return result, summary

    def _flt(self, df, col, op, val):
        try:
            if op == "year_eq":
                s = df[col]
                if s.dtype == object: s = pd.to_datetime(s, errors="coerce")
                return df[s.dt.year == int(val)]
            if op == "gte": return df[df[col] >= float(val)]
            if op == "lte": return df[df[col] <= float(val)]
            if op == "gt":  return df[df[col] > float(val)]
            if op == "lt":  return df[df[col] < float(val)]
            if op == "eq":  return df[df[col] == val]
            if op == "contains": return df[df[col].astype(str).str.contains(str(val),case=False,na=False)]
        except Exception: pass
        return df

    def _top_corr(self, corr, n=5):
        pairs = []
        cols = corr.columns.tolist()
        for i in range(len(cols)):
            for j in range(i+1,len(cols)): pairs.append((cols[i],cols[j],corr.iloc[i,j]))
        pairs.sort(key=lambda t: abs(t[2]), reverse=True)
        return pairs[:n]

    def _fmt(self, val):
        try:
            v = float(val)
            if abs(v)>=1e9: return f"{v/1e9:.2f}B"
            if abs(v)>=1e6: return f"{v/1e6:.2f}M"
            if abs(v)>=1e3: return f"{v/1e3:.1f}K"
            return f"{v:,.2f}"
        except Exception: return str(val)


# ─── 5. CHART RENDERER ───────────────────────
class ChartRenderer:
    def _setup(self, figsize=(12,6)):
        fig, ax = plt.subplots(figsize=figsize)
        fig.patch.set_facecolor(BG_COLOR); ax.set_facecolor(BG_COLOR)
        for s in ["top","right"]: ax.spines[s].set_visible(False)
        for s in ["bottom","left"]: ax.spines[s].set_color(GRID_COLOR)
        ax.tick_params(colors=TEXT_COLOR, labelsize=9)
        ax.yaxis.label.set_color(TEXT_COLOR); ax.xaxis.label.set_color(TEXT_COLOR)
        ax.title.set_color(TITLE_COLOR); ax.title.set_fontsize(13); ax.title.set_fontweight("bold")
        ax.grid(axis="y", color=GRID_COLOR, linewidth=0.5, alpha=0.7)
        return fig, ax

    @staticmethod
    def _fa(x, pos=None):
        if abs(x)>=1e9: return f"{x/1e9:.1f}B"
        if abs(x)>=1e6: return f"{x/1e6:.1f}M"
        if abs(x)>=1e3: return f"{x/1e3:.0f}K"
        return f"{x:,.0f}"

    @staticmethod
    def _fv(v):
        if abs(v)>=1e6: return f"{v/1e6:.1f}M"
        if abs(v)>=1e3: return f"{v/1e3:.0f}K"
        return f"{v:,.0f}"

    def render(self, plan, data):
        ct = plan.get("chart_type","bar"); title = plan.get("title","Data Visualization")
        xl = plan.get("x_column",""); yl = plan.get("y_column","")
        try:
            if ct in ("corr_heatmap","heatmap"): return self._corr(data, title)
            if ct == "histogram": return self._hist(data, title, xl)
            if ct == "scatter":   return self._scatter(data, plan, title)
            if ct == "box":       return self._box(data, plan, title)
            if ct in ("pie","donut"): return self._pie(data, title, ct=="donut")
            if ct in ("grouped_bar","stacked_bar"): return self._grouped(data, title, ct=="stacked_bar", xl, yl)
            if ct in ("line","time_series","moving_avg","cumulative"): return self._line(data, title, xl, yl)
            if ct == "area":   return self._area(data, title, xl, yl)
            if ct == "hbar":   return self._hbar(data, title, xl, yl)
            if ct == "pareto": return self._pareto(data, title, yl)
            return self._bar(data, title, xl, yl)
        except Exception as e:
            fig, ax = self._setup()
            ax.text(0.5,0.5,f"Render error:\n{e}",transform=ax.transAxes,
                    ha="center",va="center",color=TEXT_COLOR,fontsize=10)
            ax.set_title(title); plt.tight_layout(); return fig

    def _bar(self, data, title, xl, yl):
        n = len(data)
        fig, ax = self._setup(figsize=(max(10, n*0.6+2), 6))
        colors = [PALETTE[i%len(PALETTE)] for i in range(n)]
        bars = ax.bar(range(n), data.values, color=colors, edgecolor=BG_COLOR, linewidth=0.5)
        ax.set_xticks(range(n))
        ax.set_xticklabels([str(l)[:20] for l in data.index], rotation=40, ha="right", fontsize=9)
        if n <= 20:
            for bar, val in zip(bars, data.values):
                ax.text(bar.get_x()+bar.get_width()/2., bar.get_height()*1.01,
                        self._fv(val), ha="center", va="bottom", fontsize=8, color=TEXT_COLOR)
        ax.set_xlabel(xl, fontsize=10); ax.set_ylabel(yl or "Value", fontsize=10)
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(self._fa))
        ax.set_title(title); plt.tight_layout(); return fig

    def _hbar(self, data, title, xl, yl):
        ds = data.sort_values(ascending=True); n = len(ds)
        fig, ax = self._setup(figsize=(12, max(5, n*0.4+1)))
        ax.barh(range(n), ds.values, color=[PALETTE[i%len(PALETTE)] for i in range(n)], edgecolor=BG_COLOR)
        ax.set_yticks(range(n)); ax.set_yticklabels([str(l)[:25] for l in ds.index], fontsize=9)
        ax.xaxis.set_major_formatter(mticker.FuncFormatter(self._fa))
        ax.set_xlabel(yl or "Value", fontsize=10); ax.set_title(title)
        ax.grid(axis="x",color=GRID_COLOR,linewidth=0.5,alpha=0.7); ax.grid(axis="y",visible=False)
        plt.tight_layout(); return fig

    def _line(self, data, title, xl, yl):
        fig, ax = self._setup(figsize=(13,6))
        ax.plot(range(len(data)), data.values, color=ACCENT, linewidth=2.5, marker="o", markersize=3)
        ax.fill_between(range(len(data)), data.values, alpha=0.1, color=ACCENT)
        step = max(1, len(data)//12)
        ax.set_xticks(range(0,len(data),step))
        ax.set_xticklabels([str(data.index[i])[:16] for i in range(0,len(data),step)], rotation=40, ha="right", fontsize=9)
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(self._fa))
        ax.set_xlabel(xl or "Date", fontsize=10); ax.set_ylabel(yl or "Value", fontsize=10)
        ax.set_title(title); plt.tight_layout(); return fig

    def _area(self, data, title, xl, yl):
        fig, ax = self._setup(figsize=(13,6))
        ax.fill_between(range(len(data)), data.values, alpha=0.45, color=ACCENT)
        ax.plot(range(len(data)), data.values, color=ACCENT, linewidth=2)
        step = max(1, len(data)//12)
        ax.set_xticks(range(0,len(data),step))
        ax.set_xticklabels([str(data.index[i])[:16] for i in range(0,len(data),step)], rotation=40, ha="right", fontsize=9)
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(self._fa))
        ax.set_xlabel(xl or "Date", fontsize=10); ax.set_ylabel(yl or "Value", fontsize=10)
        ax.set_title(title); plt.tight_layout(); return fig

    def _hist(self, data, title, xl):
        fig, ax = self._setup(figsize=(11,6))
        n_bins = min(50, max(10, int(len(data)**0.5)))
        ax.hist(data, bins=n_bins, color=ACCENT, edgecolor=BG_COLOR, alpha=0.85, linewidth=0.5)
        ax.axvline(data.mean(),   color="#FBBF24", linewidth=1.5, linestyle="--", label=f"Mean: {data.mean():.2f}")
        ax.axvline(data.median(), color="#34D399", linewidth=1.5, linestyle=":",  label=f"Median: {data.median():.2f}")
        ax.legend(facecolor=BG_COLOR, labelcolor=TEXT_COLOR, fontsize=9)
        ax.set_xlabel(xl, fontsize=10); ax.set_ylabel("Frequency", fontsize=10)
        ax.xaxis.set_major_formatter(mticker.FuncFormatter(self._fa))
        ax.set_title(title); plt.tight_layout(); return fig

    def _scatter(self, data, plan, title):
        xc, yc = plan["x_column"], plan["y_column"]
        fig, ax = self._setup(figsize=(11,7))
        ax.scatter(data[xc], data[yc], color=ACCENT, alpha=0.5, s=25, edgecolors="none")
        try:
            z = np.polyfit(data[xc].dropna(), data[yc].dropna(), 1)
            xs = np.linspace(data[xc].min(), data[xc].max(), 200)
            ax.plot(xs, np.poly1d(z)(xs), color="#FBBF24", linewidth=1.5, linestyle="--", label="Trend")
            ax.legend(facecolor=BG_COLOR, labelcolor=TEXT_COLOR, fontsize=9)
        except Exception: pass
        ax.set_xlabel(xc, fontsize=10); ax.set_ylabel(yc, fontsize=10)
        ax.xaxis.set_major_formatter(mticker.FuncFormatter(self._fa))
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(self._fa))
        ax.set_title(title); plt.tight_layout(); return fig

    def _box(self, df, plan, title):
        xc, yc = plan.get("x_column"), plan.get("y_column")
        if not yc or yc not in df.columns: yc = xc
        fig, ax = self._setup(figsize=(12,6))
        bkw = dict(patch_artist=True, boxprops=dict(facecolor=ACCENT,color=GRID_COLOR),
                   medianprops=dict(color=TITLE_COLOR,linewidth=2),
                   flierprops=dict(markerfacecolor=ACCENT,markeredgecolor="none",alpha=0.4),
                   whiskerprops=dict(color=TEXT_COLOR), capprops=dict(color=TEXT_COLOR))
        if xc and xc in df.columns and xc != yc:
            groups = [grp[yc].dropna().values for _,grp in df.groupby(xc)]
            labels = [str(l)[:15] for l in df[xc].unique().tolist()]
            ax.boxplot(groups, labels=labels, **bkw)
            plt.xticks(rotation=40, ha="right", fontsize=9); ax.set_xlabel(xc, fontsize=10)
        else:
            ax.boxplot(df[yc].dropna(), **bkw)
        ax.set_ylabel(yc or "", fontsize=10)
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(self._fa))
        ax.set_title(title); plt.tight_layout(); return fig

    def _pie(self, data, title, donut=False):
        fig, ax = plt.subplots(figsize=(9,7))
        fig.patch.set_facecolor(BG_COLOR); ax.set_facecolor(BG_COLOR)
        wedges,texts,autotexts = ax.pie(
            data.values, labels=[str(l)[:20] for l in data.index],
            autopct="%1.1f%%", colors=PALETTE[:len(data)],
            wedgeprops={"linewidth":1.5,"edgecolor":BG_COLOR},
            textprops={"color":TEXT_COLOR,"fontsize":9})
        for at in autotexts: at.set_color(TITLE_COLOR); at.set_fontweight("bold")
        if donut: ax.add_artist(plt.Circle((0,0),0.65,fc=BG_COLOR))
        ax.set_title(title, color=TITLE_COLOR, fontsize=13, fontweight="bold")
        plt.tight_layout(); return fig

    def _grouped(self, data, title, stacked, xl, yl):
        if isinstance(data, pd.Series): return self._bar(data, title, xl, yl)
        ng = len(data.index); nc = len(data.columns)
        fig, ax = self._setup(figsize=(max(12, ng*nc*0.4+2), 7))
        if stacked:
            bottom = np.zeros(ng)
            for i,col in enumerate(data.columns):
                ax.bar(range(ng), data[col].values, bottom=bottom,
                       label=str(col), color=PALETTE[i%len(PALETTE)], edgecolor=BG_COLOR)
                bottom += data[col].values
        else:
            w = 0.8/max(nc,1)
            for i,col in enumerate(data.columns):
                offs = [j+i*w-(nc*w/2) for j in range(ng)]
                ax.bar(offs, data[col].values, width=w-0.02,
                       label=str(col), color=PALETTE[i%len(PALETTE)], edgecolor=BG_COLOR)
        ax.set_xticks(range(ng))
        ax.set_xticklabels([str(l)[:15] for l in data.index], rotation=40, ha="right", fontsize=9)
        ax.legend(facecolor=BG_COLOR, labelcolor=TEXT_COLOR, fontsize=9, loc="upper right", framealpha=0.5)
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(self._fa))
        ax.set_xlabel(xl or "", fontsize=10); ax.set_ylabel(yl or "Value", fontsize=10)
        ax.set_title(title); plt.tight_layout(); return fig

    def _corr(self, corr, title):
        n = len(corr)
        fig, ax = plt.subplots(figsize=(max(8,n), max(6,n*0.7)))
        fig.patch.set_facecolor(BG_COLOR); ax.set_facecolor(BG_COLOR)
        from matplotlib.colors import LinearSegmentedColormap
        cmap = LinearSegmentedColormap.from_list("nx",["#1E3A5F",BG_COLOR,"#5B21B6"])
        im = ax.imshow(corr.values, cmap=cmap, vmin=-1, vmax=1, aspect="auto")
        plt.colorbar(im, ax=ax, label="Correlation", shrink=0.8)
        ax.set_xticks(range(n)); ax.set_yticks(range(n))
        ax.set_xticklabels(corr.columns, rotation=45, ha="right", fontsize=9, color=TEXT_COLOR)
        ax.set_yticklabels(corr.index, fontsize=9, color=TEXT_COLOR)
        for i in range(n):
            for j in range(n):
                v = corr.iloc[i,j]
                ax.text(j,i,f"{v:.2f}",ha="center",va="center",fontsize=8,
                        color=TITLE_COLOR if abs(v)>0.5 else TEXT_COLOR,
                        fontweight="bold" if abs(v)>0.7 else "normal")
        ax.set_title(title, color=TITLE_COLOR, fontsize=13, fontweight="bold")
        plt.tight_layout(); return fig

    def _pareto(self, data, title, yl):
        fig, ax = self._setup(figsize=(13,6))
        ax2 = ax.twinx(); ax2.set_facecolor(BG_COLOR)
        ds = data.sort_values(ascending=False); cum = ds.cumsum()/ds.sum()*100
        ax.bar(range(len(ds)), ds.values, color=ACCENT, edgecolor=BG_COLOR, alpha=0.85)
        ax2.plot(range(len(ds)), cum.values, color="#FBBF24", linewidth=2, marker="o", markersize=4)
        ax2.axhline(80, color="#F87171", linewidth=1, linestyle="--")
        ax2.set_ylim(0,110); ax2.set_ylabel("Cumulative %", color="#FBBF24", fontsize=10)
        ax2.tick_params(colors="#FBBF24"); ax2.spines["right"].set_color("#FBBF24")
        ax.set_xticks(range(len(ds)))
        ax.set_xticklabels([str(l)[:15] for l in ds.index], rotation=40, ha="right", fontsize=9)
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(self._fa))
        ax.set_ylabel(yl or "Value", fontsize=10); ax.set_title(title)
        plt.tight_layout(); return fig


# ─── 6. CHART ENGINE (Public API — Backward Compatible) ──
class ChartEngine:
    """
    Orchestrates the full visualization pipeline.
    API: generate_chart(df, query, llm=None) -> (fig, summary_info, error_str)
    """
    def __init__(self):
        self.profiler  = DatasetProfiler()
        self.parser    = IntentParser()
        self.validator = ValidationEngine()
        self.data_eng  = DataEngine()
        self.renderer  = ChartRenderer()

    def generate_chart(self, df: pd.DataFrame, query: str, llm=None):
        try:
            profile = self.profiler.profile(df)
            plan    = self.parser.parse(query, df, profile, llm=llm)
            valid, err = self.validator.validate(plan, df, profile)
            if not valid: return None, None, err
            result, summary_text, meta = self.data_eng.calculate(plan, df, profile)
            if isinstance(result, pd.Series) and result.empty:
                return None, None, "Query returned no data. Try adjusting filters."
            if isinstance(result, pd.DataFrame) and result.empty:
                return None, None, "Query returned no data after filtering."
            fig = self.renderer.render(plan, result)
            summary_info = {
                "chart_title": plan.get("title","Data Visualization"),
                "explanation": summary_text,
                "rows_analyzed": meta.get("rows_used", len(df)),
                "columns": len(df.columns),
                "chart_type": plan.get("chart_type","bar"),
                "plan": plan,
            }
            return fig, summary_info, None
        except Exception as e:
            import traceback
            return None, None, f"Visualization error: {e}\n{traceback.format_exc()}"
