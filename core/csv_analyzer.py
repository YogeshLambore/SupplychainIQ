import pandas as pd
import matplotlib.pyplot as plt
import io

class CSVAnalyzer:
    def __init__(self):
        pass
        
    def analyze_schema(self, df: pd.DataFrame) -> dict:
        """Extracts basic information about the dataset."""
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
        
        # Try to find dates
        date_cols = []
        for col in categorical_cols:
            if 'date' in col.lower():
                date_cols.append(col)
                
        return {
            "rows": len(df),
            "columns": len(df.columns),
            "column_names": df.columns.tolist(),
            "numeric_columns": numeric_cols,
            "categorical_columns": categorical_cols,
            "date_columns": date_cols
        }
        
    def interpret_and_execute(self, query: str, df: pd.DataFrame):
        """
        Intelligently routes a query to generate appropriate data insights and charts (Line, Bar, Pie, Scatter).
        Provides a fallback if no LLM code-generation sandbox is available.
        """
        from core.chart_engine import ChartEngine
        engine = ChartEngine()
        
        is_summary_query = any(w in query.lower() for w in ["explain", "summary", "what is"])
        is_chart_query = any(w in query.lower() for w in ["chart", "plot", "graph", "compare", "trend", "bar", "pie", "scatter", "hist", "distribution"])
        
        # Check if query is explicitly just asking for a summary
        if is_summary_query and not is_chart_query:
            schema = self.analyze_schema(df)
            result_text = (f"This dataset contains **{schema['rows']:,} rows** and **{schema['columns']} columns**.\n\n"
                           f"It includes fields such as: {', '.join(schema['column_names'][:5])}.\n"
                           f"Numeric values are present in: {', '.join(schema['numeric_columns'])}.\n\n"
                           f"*(Local analysis completed successfully without external API calls.)*")
            return result_text, None

        # Otherwise, attempt to generate a chart
        fig, summary_info, error = engine.generate_chart(df, query)
        
        if error:
            return f"I could not generate a chart. {error}", None
            
        if summary_info:
            result_text = (f"**Generating a chart from the uploaded dataset...**\n\n"
                           f"{summary_info['explanation']}\n\n"
                           f"**Data Summary:**\n"
                           f"- Rows Analyzed: {summary_info['rows_analyzed']:,}\n"
                           f"- Columns: {summary_info['columns']}")
            return result_text, fig
            
        return "I could not find enough suitable data to answer that question.", None
