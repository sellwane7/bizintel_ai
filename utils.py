from textblob import TextBlob
import pandas as pd
import numpy as np
import os
import requests


# ──────────────────────────────────────────────
#  SENTIMENT ENGINE
# ──────────────────────────────────────────────

def get_sentiment(text):
    if pd.isna(text):
        text = ""
    text = str(text)
    polarity     = TextBlob(text).sentiment.polarity
    subjectivity = TextBlob(text).sentiment.subjectivity

    if polarity > 0.1:
        label = "Positive"
    elif polarity < -0.1:
        label = "Negative"
    else:
        label = "Neutral"

    return label, round(polarity, 4), round(subjectivity, 4)


def numeric_sentiment(value, mean, std):
    """Derive a sentiment label from a numeric value relative to its distribution."""
    if std == 0:
        return "Neutral", 0.0, 0.0
    z = (value - mean) / std
    if z > 0.5:
        polarity = min(round(z / 3, 4), 1.0)
        return "Positive", polarity, 0.3
    elif z < -0.5:
        polarity = max(round(z / 3, 4), -1.0)
        return "Negative", polarity, 0.3
    else:
        return "Neutral", round(z / 6, 4), 0.2


def analyze_dataframe(df, column):
    """
    Analyse any column — text or numeric — and append Sentiment / Polarity / Subjectivity.
    All other numeric columns also get summary stats attached in the returned df.
    """
    df = df.copy()
    df[column] = df[column].fillna("")

    # Detect if the selected column is numeric
    try:
        numeric_vals = pd.to_numeric(df[column], errors="raise")
        is_numeric   = True
    except Exception:
        is_numeric = False

    if is_numeric:
        df[column] = numeric_vals
        mean = numeric_vals.mean()
        std  = numeric_vals.std()
        results = numeric_vals.apply(lambda v: numeric_sentiment(v, mean, std))
    else:
        df[column] = df[column].astype(str)
        results = df[column].apply(get_sentiment)

    df["Sentiment"]    = results.apply(lambda x: x[0])
    df["Polarity"]     = results.apply(lambda x: x[1])
    df["Subjectivity"] = results.apply(lambda x: x[2])
    return df


# ──────────────────────────────────────────────
#  NUMERIC COLUMN STATS
# ──────────────────────────────────────────────

def numeric_stats(df):
    """Return a dict of stats for every numeric column in the dataframe."""
    stats = {}
    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    # Exclude our added columns
    exclude = {"Polarity", "Subjectivity"}
    for col in num_cols:
        if col in exclude:
            continue
        s = df[col].dropna()
        if len(s) == 0:
            continue
        stats[col] = {
            "count":  int(s.count()),
            "mean":   round(float(s.mean()),  2),
            "median": round(float(s.median()), 2),
            "std":    round(float(s.std()),   2),
            "min":    round(float(s.min()),   2),
            "max":    round(float(s.max()),   2),
            "sum":    round(float(s.sum()),   2),
            "q25":    round(float(s.quantile(0.25)), 2),
            "q75":    round(float(s.quantile(0.75)), 2),
        }
    return stats


def format_numeric_stats(stats):
    if not stats:
        return "  No numeric columns detected.\n"
    lines = []
    for col, s in stats.items():
        lines.append(f"\n  [{col}]")
        lines.append(f"    Count   : {s['count']}")
        lines.append(f"    Mean    : {s['mean']}")
        lines.append(f"    Median  : {s['median']}")
        lines.append(f"    Std Dev : {s['std']}")
        lines.append(f"    Min     : {s['min']}   Max : {s['max']}")
        lines.append(f"    Sum     : {s['sum']}")
        lines.append(f"    Q25     : {s['q25']}   Q75 : {s['q75']}")
    return "\n".join(lines)


# ──────────────────────────────────────────────
#  REPORT GENERATORS
# ──────────────────────────────────────────────

def generate_quick_scan(df, selected_column=None, business_goal=None):
    """Fast overview: shape, columns, missing values, numeric peek, sentiment counts."""
    try:
        if df is None or df.empty:
            return "No data available."

        rows, cols_count = df.shape
        missing          = df.isnull().sum()
        missing_info     = missing[missing > 0]
        stats            = numeric_stats(df)

        sentiment_section = ""
        if "Sentiment" in df.columns:
            counts = df["Sentiment"].value_counts()
            pos    = counts.get("Positive", 0)
            neg    = counts.get("Negative", 0)
            neu    = counts.get("Neutral",  0)
            total  = len(df)
            sentiment_section = f"""
SENTIMENT SNAPSHOT
------------------
  Total Records : {total}
  ✅ Positive   : {pos}  ({round(pos/total*100,1) if total else 0}%)
  ❌ Negative   : {neg}  ({round(neg/total*100,1) if total else 0}%)
  ➖ Neutral    : {neu}  ({round(neu/total*100,1) if total else 0}%)
  Avg Polarity  : {round(df['Polarity'].mean(), 3) if 'Polarity' in df.columns else 'N/A'}
"""

        numeric_section = ""
        if stats:
            numeric_section = f"""
NUMERIC COLUMN STATS
--------------------{format_numeric_stats(stats)}
"""

        missing_section = (
            "MISSING VALUES\n--------------\n"
            + (missing_info.to_string() if not missing_info.empty else "  None ✅")
            + "\n"
        )

        return f"""
╔══════════════════════════════════════════════╗
║          BIZINTEL AI  —  QUICK SCAN          ║
╚══════════════════════════════════════════════╝

DATASET OVERVIEW
----------------
  Rows           : {rows}
  Columns        : {cols_count}
  Selected Column: {selected_column}
  Business Goal  : {business_goal or 'Not specified'}

COLUMNS
-------
  {', '.join(df.columns.tolist())}

{missing_section}
{numeric_section}
{sentiment_section}
"""
    except Exception as e:
        return f"Quick scan error: {str(e)}"


def generate_executive_summary(df, selected_column=None, business_goal=None):
    """
    Summarises everything: all columns, numeric stats, sentiment results,
    top/bottom records, and key business observations.
    """
    try:
        if df is None or df.empty:
            return "No data available."

        total  = len(df)
        stats  = numeric_stats(df)

        counts   = df["Sentiment"].value_counts() if "Sentiment" in df.columns else {}
        positive = counts.get("Positive", 0)
        negative = counts.get("Negative", 0)
        neutral  = counts.get("Neutral",  0)

        dominant = "Positive" if positive >= negative and positive >= neutral \
               else "Negative" if negative >= positive and negative >= neutral \
               else "Neutral"

        avg_pol  = round(df["Polarity"].mean(), 3)    if "Polarity"     in df.columns else "N/A"
        avg_sub  = round(df["Subjectivity"].mean(), 3) if "Subjectivity" in df.columns else "N/A"

        # Top positive & negative records
        top_pos = ""
        top_neg = ""
        if "Polarity" in df.columns and selected_column in df.columns:
            best_row  = df.nlargest(1,  "Polarity")
            worst_row = df.nsmallest(1, "Polarity")
            top_pos = str(best_row[selected_column].values[0])[:120]
            top_neg = str(worst_row[selected_column].values[0])[:120]

        # Categorical column summaries
        cat_section = ""
        cat_cols = df.select_dtypes(include=["object"]).columns.tolist()
        cat_cols = [c for c in cat_cols if c not in {"Sentiment", selected_column}]
        if cat_cols:
            lines = []
            for c in cat_cols[:5]:   # limit to 5 to keep readable
                top_vals = df[c].value_counts().head(3)
                lines.append(f"\n  [{c}]  (top values)")
                for val, cnt in top_vals.items():
                    lines.append(f"    {val}: {cnt}")
            cat_section = "\nCATEGORICAL COLUMNS\n-------------------" + "\n".join(lines) + "\n"

        return f"""
╔══════════════════════════════════════════════════╗
║       BIZINTEL AI  —  EXECUTIVE SUMMARY          ║
╚══════════════════════════════════════════════════╝

OVERVIEW
--------
  Total Records  : {total}
  Columns        : {len(df.columns)}
  Selected Column: {selected_column}
  Business Goal  : {business_goal or 'Not specified'}

SENTIMENT RESULTS
-----------------
  ✅ Positive    : {positive}  ({round(positive/total*100,1) if total else 0}%)
  ❌ Negative    : {negative}  ({round(negative/total*100,1) if total else 0}%)
  ➖ Neutral     : {neutral}   ({round(neutral/total*100,1)  if total else 0}%)
  Dominant Mood  : {dominant}
  Avg Polarity   : {avg_pol}   (range -1 to +1)
  Avg Subjectivity: {avg_sub}  (0=objective, 1=subjective)

NUMERIC ANALYSIS
----------------{format_numeric_stats(stats) if stats else "  No numeric columns."}

{cat_section}
HIGHLIGHT RECORDS
-----------------
  Most Positive  : "{top_pos}"
  Most Negative  : "{top_neg}"

BUSINESS OBSERVATIONS
---------------------
  • {round(positive/total*100,1) if total else 0}% of records carry a positive signal.
  • {round(negative/total*100,1) if total else 0}% of records carry a negative signal — these warrant attention.
  • Average polarity of {avg_pol} indicates an overall {'positive' if isinstance(avg_pol, float) and avg_pol > 0 else 'negative' if isinstance(avg_pol, float) and avg_pol < 0 else 'neutral'} lean.
  • Review negative records and the numeric outliers for actionable follow-up.
"""
    except Exception as e:
        return f"Executive summary error: {str(e)}"


def generate_full_report(df, selected_column=None, business_goal=None, extra_sections=None):
    """
    Full deep-dive: complete numeric stats per column, full sentiment breakdown,
    correlation insights, per-category sentiment if applicable, and recommendations.
    """
    try:
        if df is None or df.empty:
            return "No data available."

        total  = len(df)
        stats  = numeric_stats(df)
        counts = df["Sentiment"].value_counts() if "Sentiment" in df.columns else {}

        positive = counts.get("Positive", 0)
        negative = counts.get("Negative", 0)
        neutral  = counts.get("Neutral",  0)
        avg_pol  = round(df["Polarity"].mean(), 3)     if "Polarity"     in df.columns else "N/A"
        avg_sub  = round(df["Subjectivity"].mean(), 3) if "Subjectivity" in df.columns else "N/A"

        dominant = "Positive" if positive >= negative and positive >= neutral \
               else "Negative" if negative >= positive and negative >= neutral \
               else "Neutral"

        # Per-category breakdown (if any categorical column exists besides selected)
        cat_breakdown = ""
        cat_cols = df.select_dtypes(include=["object"]).columns.tolist()
        cat_cols = [c for c in cat_cols if c not in {"Sentiment", selected_column}]
        if cat_cols and "Sentiment" in df.columns:
            lines = []
            for c in cat_cols[:4]:
                lines.append(f"\n  Breakdown by [{c}]:")
                grp = df.groupby(c)["Sentiment"].value_counts().unstack(fill_value=0)
                for idx in grp.index[:8]:
                    row_data = grp.loc[idx]
                    p = row_data.get("Positive", 0)
                    n = row_data.get("Negative", 0)
                    u = row_data.get("Neutral",  0)
                    lines.append(f"    {str(idx)[:40]:<40}  Pos:{p}  Neg:{n}  Neu:{u}")
            cat_breakdown = "\nSENTIMENT BY CATEGORY\n----------------------" + "\n".join(lines) + "\n"

        # Correlation insights
        corr_section = ""
        num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        num_cols = [c for c in num_cols if c not in {"Polarity", "Subjectivity"}]
        if len(num_cols) >= 2:
            corr = df[num_cols].corr()
            # Find top 3 strongest correlations
            pairs = []
            for i, c1 in enumerate(num_cols):
                for c2 in num_cols[i+1:]:
                    pairs.append((c1, c2, round(corr.loc[c1, c2], 3)))
            pairs.sort(key=lambda x: abs(x[2]), reverse=True)
            lines = []
            for c1, c2, r in pairs[:5]:
                direction = "positive" if r > 0 else "negative"
                lines.append(f"    {c1} ↔ {c2} : r = {r}  ({direction} correlation)")
            corr_section = "\nCORRELATION INSIGHTS\n---------------------\n" + "\n".join(lines) + "\n"

        # Missing values
        missing      = df.isnull().sum()
        missing_info = missing[missing > 0]
        miss_str     = missing_info.to_string() if not missing_info.empty else "  None ✅"

        # Top 5 most positive / negative
        top_records = ""
        if "Polarity" in df.columns and selected_column in df.columns:
            best5  = df.nlargest(5,  "Polarity")[[selected_column, "Polarity", "Sentiment"]]
            worst5 = df.nsmallest(5, "Polarity")[[selected_column, "Polarity", "Sentiment"]]
            lines  = ["\n  TOP 5 POSITIVE:"]
            for _, r in best5.iterrows():
                lines.append(f"    [{r['Polarity']:+.3f}] {str(r[selected_column])[:100]}")
            lines.append("\n  TOP 5 NEGATIVE:")
            for _, r in worst5.iterrows():
                lines.append(f"    [{r['Polarity']:+.3f}] {str(r[selected_column])[:100]}")
            top_records = "\n".join(lines)

        return f"""
╔══════════════════════════════════════════════════════╗
║         BIZINTEL AI  —  FULL ANALYSIS REPORT         ║
╚══════════════════════════════════════════════════════╝

REPORT METADATA
---------------
  Dataset        : {total} records × {len(df.columns)} columns
  Selected Column: {selected_column}
  Business Goal  : {business_goal or 'Not specified'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 SECTION 1 — SENTIMENT ANALYSIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Total Records   : {total}
  ✅ Positive     : {positive}  ({round(positive/total*100,1) if total else 0}%)
  ❌ Negative     : {negative}  ({round(negative/total*100,1) if total else 0}%)
  ➖ Neutral      : {neutral}   ({round(neutral/total*100,1)  if total else 0}%)
  Dominant Mood   : {dominant}
  Avg Polarity    : {avg_pol}   (-1=very negative, 0=neutral, +1=very positive)
  Avg Subjectivity: {avg_sub}   (0=objective, 1=highly subjective)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 SECTION 2 — NUMERIC ANALYSIS (All Numeric Columns)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{format_numeric_stats(stats) if stats else "  No numeric columns in dataset."}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 SECTION 3 — DATA QUALITY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Missing Values:
{miss_str}

{corr_section}
{cat_breakdown}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 SECTION 4 — HIGHLIGHT RECORDS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{top_records}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 SECTION 5 — STRATEGIC RECOMMENDATIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  1. Focus on the {round(negative/total*100,1) if total else 0}% negative records — investigate root causes.
  2. Reinforce drivers behind the {round(positive/total*100,1) if total else 0}% positive signals.
  3. Neutral records ({round(neutral/total*100,1) if total else 0}%) represent an opportunity to convert to positive.
  4. Review numeric outliers (min/max) for anomalies or data quality issues.
  5. Track polarity trend over time to measure improvement.

{('ADDITIONAL NOTES\n----------------\n' + extra_sections) if extra_sections else ''}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Generated by BizIntel AI  |  Powered by Python + TextBlob
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    except Exception as e:
        return f"Full report generation error: {str(e)}"


def generate_summary(df):
    counts = df["Sentiment"].value_counts() if "Sentiment" in df.columns else {}
    return {
        "total":            len(df),
        "positive":         int(counts.get("Positive", 0)),
        "negative":         int(counts.get("Negative", 0)),
        "neutral":          int(counts.get("Neutral",  0)),
        "avg_polarity":     round(float(df["Polarity"].mean()),     3) if "Polarity"     in df.columns else 0,
        "avg_subjectivity": round(float(df["Subjectivity"].mean()), 3) if "Subjectivity" in df.columns else 0,
    }


# ──────────────────────────────────────────────
#  Q&A ENGINE
# ──────────────────────────────────────────────

def answer_user_question(df, selected_column=None, business_goal=None, question=""):
    try:
        if df is None or df.empty:
            return "No dataset is loaded yet. Please upload and analyse your data first."

        if not question or str(question).strip() == "":
            return "Please ask me a question about your dataset."

        q = str(question).lower().strip()

        total_rows = df.shape[0]
        total_cols = df.shape[1]

        # Sentiment counts
        sentiment_counts = {}
        if "Sentiment" in df.columns:
            sentiment_counts = df["Sentiment"].value_counts().to_dict()

        positive = sentiment_counts.get("Positive", 0)
        negative = sentiment_counts.get("Negative", 0)
        neutral = sentiment_counts.get("Neutral", 0)

        # ==========================================================
        # DATASET STRUCTURE QUESTIONS
        # ==========================================================
        if any(x in q for x in ["how many rows", "rows", "records", "entries"]):
            return f"Your dataset contains {total_rows:,} records."

        if any(x in q for x in ["how many columns", "columns", "fields"]):
            return (
                f"Your dataset has {total_cols} columns.\n\n"
                f"The columns are:\n"
                + "\n".join([f"• {col}" for col in df.columns])
            )

        if any(x in q for x in ["missing", "null", "empty", "nan"]):
            missing = df.isnull().sum()
            missing = missing[missing > 0]

            if missing.empty:
                return "Good news — no missing values were found in your dataset."

            response = "Here are the missing values in your dataset:\n\n"
            for col, count in missing.items():
                response += f"• {col}: {count}\n"

            return response

        # ==========================================================
        # SENTIMENT QUESTIONS
        # ==========================================================
        if "positive" in q:
            return (
                f"There are {positive} positive records "
                f"({round((positive/total_rows)*100,1) if total_rows else 0}%)."
            )

        if "negative" in q:
            return (
                f"There are {negative} negative records "
                f"({round((negative/total_rows)*100,1) if total_rows else 0}%)."
            )

        if "neutral" in q:
            return (
                f"There are {neutral} neutral records "
                f"({round((neutral/total_rows)*100,1) if total_rows else 0}%)."
            )

        if any(x in q for x in ["sentiment summary", "sentiment breakdown", "distribution"]):
            return (
                f"Sentiment breakdown:\n\n"
                f"• Positive: {positive}\n"
                f"• Negative: {negative}\n"
                f"• Neutral: {neutral}\n"
                f"• Total: {total_rows}"
            )

        if "polarity" in q and "Polarity" in df.columns:
            return (
                f"Polarity analysis:\n\n"
                f"• Average polarity: {round(df['Polarity'].mean(), 3)}\n"
                f"• Minimum polarity: {round(df['Polarity'].min(), 3)}\n"
                f"• Maximum polarity: {round(df['Polarity'].max(), 3)}"
            )

        if "subjectivity" in q and "Subjectivity" in df.columns:
            return (
                f"Subjectivity analysis:\n\n"
                f"• Average subjectivity: {round(df['Subjectivity'].mean(), 3)}\n"
                f"• Minimum subjectivity: {round(df['Subjectivity'].min(), 3)}\n"
                f"• Maximum subjectivity: {round(df['Subjectivity'].max(), 3)}"
            )

        # ==========================================================
        # TOP POSITIVE / NEGATIVE RECORDS
        # ==========================================================
        if any(x in q for x in ["most positive", "best review", "top positive"]):
            if "Polarity" in df.columns and selected_column in df.columns:
                top = df.nlargest(3, "Polarity")[[selected_column, "Polarity"]]

                response = "Here are the most positive records:\n\n"

                for _, row in top.iterrows():
                    response += (
                        f"• {str(row[selected_column])[:200]} "
                        f"(Score: {round(row['Polarity'],3)})\n"
                    )

                return response

        if any(x in q for x in ["most negative", "worst review", "top negative"]):
            if "Polarity" in df.columns and selected_column in df.columns:
                bottom = df.nsmallest(3, "Polarity")[[selected_column, "Polarity"]]

                response = "Here are the most negative records:\n\n"

                for _, row in bottom.iterrows():
                    response += (
                        f"• {str(row[selected_column])[:200]} "
                        f"(Score: {round(row['Polarity'],3)})\n"
                    )

                return response

        # ==========================================================
        # COLUMN-SPECIFIC QUESTIONS
        # ==========================================================
        numeric_columns = df.select_dtypes(include=["number"]).columns.tolist()

        for col in df.columns:

            if col.lower() in q:

                # Numeric analysis
                if col in numeric_columns:

                    s = df[col].dropna()

                    return (
                        f"Analysis for '{col}':\n\n"
                        f"• Average: {round(s.mean(),2)}\n"
                        f"• Median: {round(s.median(),2)}\n"
                        f"• Minimum: {round(s.min(),2)}\n"
                        f"• Maximum: {round(s.max(),2)}\n"
                        f"• Standard deviation: {round(s.std(),2)}\n"
                        f"• Total sum: {round(s.sum(),2)}"
                    )

                # Text/categorical analysis
                else:

                    top_values = df[col].astype(str).value_counts().head(5)

                    response = f"Top values in '{col}':\n\n"

                    for value, count in top_values.items():
                        response += f"• {value}: {count}\n"

                    return response

        # ==========================================================
        # CORRELATION QUESTIONS
        # ==========================================================
        if any(x in q for x in ["correlation", "relationship", "related"]):

            numeric_df = df.select_dtypes(include=["number"])

            if len(numeric_df.columns) < 2:
                return "There are not enough numeric columns to calculate relationships."

            corr = numeric_df.corr().round(2)

            return (
                "I analysed the numeric relationships in your dataset.\n\n"
                + corr.to_string()
            )

        # ==========================================================
        # GENERAL SUMMARY
        # ==========================================================
        if any(x in q for x in ["summary", "overview", "insights", "report"]):

            avg_polarity = (
                round(df["Polarity"].mean(), 3)
                if "Polarity" in df.columns else "N/A"
            )

            return (
                f"Dataset overview:\n\n"
                f"• Records: {total_rows}\n"
                f"• Columns: {total_cols}\n"
                f"• Positive sentiment: {positive}\n"
                f"• Negative sentiment: {negative}\n"
                f"• Neutral sentiment: {neutral}\n"
                f"• Average polarity: {avg_polarity}\n\n"
                f"Overall, the dataset shows "
                f"{'mostly positive' if positive > negative else 'mostly negative' if negative > positive else 'balanced'} sentiment."
            )

        # ==========================================================
        # FALLBACK AI-LIKE RESPONSE
        # ==========================================================
        return (
            f"I understood your question: '{question}'.\n\n"
            f"I analysed your dataset but couldn't find an exact match for that question.\n"
            f"Try asking naturally, for example:\n\n"
            f"• Which reviews are the most negative?\n"
            f"• What is the average sales value?\n"
            f"• Which product performs best?\n"
            f"• What trends do you see in the data?\n"
            f"• Which category has the most complaints?\n\n"
            f"You can ask in normal business language — I'll analyse it for you."
        )

    except Exception as e:
        return f"Question answering error: {str(e)}"
