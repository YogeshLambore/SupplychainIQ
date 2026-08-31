import pandas as pd
import matplotlib.pyplot as plt

class ChartEngine:
    def __init__(self):
        pass

    def setup_plot(self):
        """Sets up the Matplotlib figure with the premium dark theme."""
        f, a = plt.subplots(figsize=(10, 6))
        f.patch.set_facecolor('#1A1C22') # Match NEXORA cards
        a.set_facecolor('#1A1C22')
        a.spines['bottom'].set_color('#2B2E36')
        a.spines['left'].set_color('#2B2E36')
        a.spines['top'].set_visible(False)
        a.spines['right'].set_visible(False)
        a.tick_params(axis='x', colors='#9CA3AF')
        a.tick_params(axis='y', colors='#9CA3AF')
        a.yaxis.label.set_color('#9CA3AF')
        a.xaxis.label.set_color('#9CA3AF')
        a.title.set_color('#F3F4F6')
        a.title.set_fontsize(14)
        a.title.set_fontweight('bold')
        return f, a

    def parse_query(self, query: str, df: pd.DataFrame):
        """Parses natural language query to determine chart parameters."""
        query = query.lower()
        
        # Determine chart type
        chart_type = None
        if any(w in query for w in ["hist", "distribution"]):
            chart_type = "histogram"
        elif any(w in query for w in ["pie", "share", "percentage", "breakdown"]):
            chart_type = "pie"
        elif any(w in query for w in ["scatter", "relationship", "versus", "vs"]):
            chart_type = "scatter"
        elif any(w in query for w in ["line", "trend", "over time", "history"]):
            chart_type = "line"
        elif any(w in query for w in ["bar", "compare", "top", "highest", "department", "category"]):
            chart_type = "bar"
            
        # Determine aggregation
        agg = "sum" # default
        if any(w in query for w in ["average", "mean", "avg"]):
            agg = "mean"
        elif "count" in query or "frequency" in query:
            agg = "count"
        elif any(w in query for w in ["min", "minimum"]):
            agg = "min"
        elif any(w in query for w in ["max", "maximum", "highest"]):
            agg = "max"
        elif "median" in query:
            agg = "median"
            
        # Detect columns
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        cat_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
        date_cols = [c for c in df.columns if 'date' in c.lower() or 'time' in c.lower()]
        
        mentioned_cols = [c for c in df.columns if c.lower() in query]
        mentioned_numeric = [c for c in mentioned_cols if c in numeric_cols]
        mentioned_cat = [c for c in mentioned_cols if c in cat_cols]
        
        return {
            "chart_type": chart_type,
            "agg": agg,
            "numeric_cols": numeric_cols,
            "cat_cols": cat_cols,
            "date_cols": date_cols,
            "mentioned_numeric": mentioned_numeric,
            "mentioned_cat": mentioned_cat
        }

    def generate_chart(self, df: pd.DataFrame, query: str):
        """Generates a Matplotlib figure based on a dataframe and a natural query."""
        params = self.parse_query(query, df)
        chart_type = params["chart_type"]
        agg = params["agg"]
        numeric_cols = params["numeric_cols"]
        cat_cols = params["cat_cols"]
        date_cols = params["date_cols"]
        mentioned_numeric = params["mentioned_numeric"]
        mentioned_cat = params["mentioned_cat"]
        
        # Fallbacks if chart_type wasn't explicit
        if not chart_type:
            if len(mentioned_numeric) >= 2:
                chart_type = "scatter"
            elif date_cols and mentioned_numeric:
                chart_type = "line"
            elif cat_cols:
                chart_type = "bar"
            elif numeric_cols:
                chart_type = "histogram"
            else:
                chart_type = "bar"
                
        # Smart overrides based on detected columns
        if chart_type == "bar" and len(mentioned_numeric) >= 2 and not mentioned_cat:
            chart_type = "scatter"
            
        fig, ax = self.setup_plot()
        chart_title = "Data Visualization"
        explanation = ""
        
        try:
            if chart_type == "histogram":
                col = mentioned_numeric[0] if mentioned_numeric else (numeric_cols[0] if numeric_cols else None)
                if not col:
                    raise ValueError(f"Histogram requires a numeric column. Available numeric columns: {', '.join(numeric_cols)}")
                df[col].dropna().plot(kind='hist', bins=20, ax=ax, color='#A78BFA', alpha=0.8, edgecolor='#2B2E36')
                chart_title = f"Distribution of {col}"
                ax.set_xlabel(col)
                ax.set_ylabel("Frequency")
                explanation = f"Generated histogram showing the frequency distribution of **{col}**."
                
            elif chart_type == "scatter":
                if len(mentioned_numeric) >= 2:
                    x_col, y_col = mentioned_numeric[0], mentioned_numeric[1]
                elif len(numeric_cols) >= 2:
                    x_col, y_col = numeric_cols[0], numeric_cols[1]
                else:
                    raise ValueError(f"Scatter plot requires at least two numeric columns. Available: {', '.join(numeric_cols)}")
                ax.scatter(df[x_col], df[y_col], color='#A78BFA', alpha=0.6, s=50)
                chart_title = f"{y_col} vs {x_col}"
                ax.set_xlabel(x_col)
                ax.set_ylabel(y_col)
                explanation = f"Generated scatter plot comparing **{x_col}** and **{y_col}**."
                
            elif chart_type == "pie":
                cat = mentioned_cat[0] if mentioned_cat else (cat_cols[0] if cat_cols else None)
                if not cat:
                    raise ValueError(f"Pie chart requires a categorical column. Available: {', '.join(cat_cols)}")
                    
                if agg == "count" or not numeric_cols:
                    data = df[cat].value_counts()
                    explanation = f"Generated pie chart showing the count of each **{cat}**."
                else:
                    num = mentioned_numeric[0] if mentioned_numeric else numeric_cols[0]
                    data = df.groupby(cat)[num].agg(agg).fillna(0)
                    explanation = f"Generated pie chart showing the {agg} of **{num}** broken down by **{cat}**."
                        
                data = data.sort_values(ascending=False)
                if len(data) > 6:
                    top = data.head(5)
                    other = pd.Series({'Other': data.iloc[5:].sum()})
                    data = pd.concat([top, other])
                    
                ax.pie(data, labels=data.index, autopct='%1.1f%%', colors=['#A78BFA', '#8B5CF6', '#7C3AED', '#6D28D9', '#5B21B6', '#4C1D95'], textprops={'color': '#F3F4F6', 'weight': 'bold'})
                chart_title = f"{cat} Distribution"
                
            elif chart_type == "line":
                num = mentioned_numeric[0] if mentioned_numeric else (numeric_cols[0] if numeric_cols else None)
                if not num:
                    raise ValueError(f"Line chart requires a numeric column. Available: {', '.join(numeric_cols)}")
                    
                date_col = mentioned_cat[0] if mentioned_cat and mentioned_cat[0] in date_cols else (date_cols[0] if date_cols else None)
                
                if date_col:
                    temp_df = df.dropna(subset=[date_col, num]).sort_values(date_col)
                    ax.plot(temp_df[date_col].astype(str), temp_df[num], color='#A78BFA', linewidth=2, marker='o')
                    ax.set_xlabel(date_col)
                    plt.xticks(rotation=45, ha='right')
                    chart_title = f"{num} Trend over {date_col}"
                else:
                    ax.plot(df.index, df[num], color='#A78BFA', linewidth=2)
                    ax.set_xlabel("Index")
                    chart_title = f"{num} Trend"
                    
                ax.set_ylabel(num)
                explanation = f"Generated line chart tracking **{num}**."
                
            else: # Default to Bar
                cat = mentioned_cat[0] if mentioned_cat else (cat_cols[0] if cat_cols else None)
                num = mentioned_numeric[0] if mentioned_numeric else (numeric_cols[0] if numeric_cols else None)
                
                if cat and agg == "count":
                    data = df[cat].value_counts().head(10)
                    chart_title = f"Top 10 {cat} by Count"
                    ax.set_ylabel("Count")
                    explanation = f"Generated bar chart showing the frequency of **{cat}**."
                elif cat and num:
                    data = df.groupby(cat)[num].agg(agg).sort_values(ascending=False).head(10)
                    chart_title = f"Top 10 {cat} by {agg.capitalize()} of {num}"
                    ax.set_ylabel(f"{agg.capitalize()} of {num}")
                    explanation = f"Generated bar chart showing the {agg} of **{num}** by **{cat}**."
                elif num:
                    data = df[num].sort_values(ascending=False).head(10)
                    chart_title = f"Top 10 values for {num}"
                    ax.set_ylabel(num)
                    explanation = f"Generated bar chart for **{num}**."
                elif cat:
                    data = df[cat].value_counts().head(10)
                    chart_title = f"Top 10 {cat} by Count"
                    ax.set_ylabel("Count")
                    explanation = f"Generated bar chart showing the frequency of **{cat}**."
                else:
                    raise ValueError("Not enough data to generate a bar chart.")
                    
                data.plot(kind='bar', ax=ax, color='#A78BFA')
                plt.xticks(rotation=45, ha='right')
                
            ax.set_title(chart_title)
            plt.tight_layout()
            
            # Embed the actual calculated numerical data for the LLM to read and explain
            data_context = ""
            if chart_type in ["pie", "bar"] and 'data' in locals():
                data_context = "\nCalculated Values:\n" + data.to_string()
            elif chart_type == "histogram" and 'col' in locals():
                data_context = f"\nData stats for {col}:\nMin: {df[col].min()}\nMax: {df[col].max()}\nMean: {df[col].mean():.2f}"
            elif chart_type == "scatter" and 'x_col' in locals() and 'y_col' in locals():
                data_context = f"\nStats:\n{x_col} Mean: {df[x_col].mean():.2f}\n{y_col} Mean: {df[y_col].mean():.2f}"
            
            summary_info = {
                "chart_title": chart_title,
                "explanation": explanation + data_context,
                "rows_analyzed": len(df),
                "columns": len(df.columns)
            }
            return fig, summary_info, None
            
        except Exception as e:
            plt.close(fig)
            return None, None, str(e)
