#!/usr/bin/env python3
"""Generate all Day 050 notebooks: exercises 1-5, project, solution."""
import json
from pathlib import Path

ROOT    = Path(__file__).resolve().parent.parent
DAY_DIR = ROOT / "03_data_analysis" / "day_050"

_cid = 0


def cid():
    global _cid
    _cid += 1
    return f"c{_cid:04d}"


def md(source: str) -> dict:
    return {"cell_type": "markdown", "id": cid(), "metadata": {}, "source": source}


def code(source: str) -> dict:
    return {
        "cell_type": "code",
        "id": cid(),
        "metadata": {},
        "outputs": [],
        "execution_count": None,
        "source": source,
    }


def nb(cells: list) -> dict:
    return {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {
                "display_name": "ai-course",
                "language": "python",
                "name": "ai-course",
            },
            "language_info": {"name": "python", "version": "3.10.0"},
        },
        "cells": cells,
    }


def write_nb(path: Path, cells: list):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(nb(cells), indent=1), encoding="utf-8")
    print(f"  wrote {path.relative_to(ROOT)}")


# ---------------------------------------------------------------------------
# Shared setup
# ---------------------------------------------------------------------------

MAKE_DATA = """\
import io
import warnings
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score, KFold
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
import ollama
warnings.filterwarnings('ignore')


def make_sample_data(n: int = 300, seed: int = 42) -> pd.DataFrame:
    \"\"\"
    Retail sales dataset.
    Columns: date (str), region, category, units_sold, price, discount, revenue.
    Revenue = units_sold*4 + price*1.5 - discount*150 + noise (5% nulls injected).
    \"\"\"
    rng      = np.random.default_rng(seed)
    dates    = pd.date_range('2023-01-01', periods=n, freq='D').strftime('%Y-%m-%d')
    region   = rng.choice(['North', 'South', 'East', 'West'], n)
    category = rng.choice(['Electronics', 'Clothing', 'Food', 'Books'], n)
    units    = rng.integers(1, 50, n)
    price    = rng.uniform(5.0, 200.0, n).round(2)
    discount = rng.choice([0.0, 0.05, 0.10, 0.15, 0.20], n)
    revenue  = (units * 4.0 + price * 1.5 - discount * 150
                + rng.standard_normal(n) * 20).round(2)
    null_idx = rng.choice(n, size=max(1, int(n * 0.05)), replace=False)
    revenue  = revenue.astype(float)
    revenue[null_idx] = np.nan
    return pd.DataFrame({
        'date':       pd.Series(dates),
        'region':     region,
        'category':   category,
        'units_sold': units,
        'price':      price,
        'discount':   discount,
        'revenue':    revenue,
    })"""

# ---------------------------------------------------------------------------
# Implementations
# ---------------------------------------------------------------------------

LOAD_AND_CLEAN_IMPL = """\
def load_and_clean(source) -> pd.DataFrame:
    \"\"\"
    Load from CSV string / file path / DataFrame and clean.

    Steps applied in order:
      1. Parse source into a DataFrame
      2. Detect and parse date/time columns to datetime64
      3. Fill numeric NaN with column median
      4. Drop exact duplicate rows
    \"\"\"
    if isinstance(source, pd.DataFrame):
        df = source.copy()
    elif isinstance(source, str) and ('\\n' in source or ',' in source[:200]):
        df = pd.read_csv(io.StringIO(source))
    else:
        df = pd.read_csv(source)

    # Detect date columns by name
    for col in df.columns:
        if any(kw in col.lower() for kw in ('date', 'time', 'created', 'updated')):
            try:
                df[col] = pd.to_datetime(df[col], errors='coerce')
            except Exception:
                pass

    # Fill numeric NaN with column median
    for col in df.select_dtypes(include='number').columns:
        median = df[col].median()
        df[col] = df[col].fillna(median)

    # Drop duplicates
    df = df.drop_duplicates().reset_index(drop=True)
    return df"""

EDA_IMPL = """\
def run_eda(df: pd.DataFrame) -> dict:
    \"\"\"
    Compute an EDA summary dict with keys:
        shape, columns, dtypes, null_counts,
        numeric_summary, correlations, category_counts,
        numeric_cols, cat_cols
    \"\"\"
    num_cols = df.select_dtypes(include='number').columns.tolist()
    cat_cols = df.select_dtypes(include='object').columns.tolist()

    numeric_summary = {}
    for col in num_cols:
        s = df[col].dropna()
        numeric_summary[col] = {
            'mean':   round(float(s.mean()),   4),
            'std':    round(float(s.std()),    4),
            'min':    round(float(s.min()),    4),
            'max':    round(float(s.max()),    4),
            'median': round(float(s.median()), 4),
        }

    correlations = {}
    if len(num_cols) >= 2:
        cm = df[num_cols].corr()
        for col in num_cols:
            correlations[col] = {
                other: round(float(cm.loc[col, other]), 4)
                for other in num_cols if other != col
            }

    category_counts = {
        col: df[col].value_counts().head(10).to_dict()
        for col in cat_cols
    }

    return {
        'shape':           {'rows': int(df.shape[0]), 'cols': int(df.shape[1])},
        'columns':         df.columns.tolist(),
        'dtypes':          {c: str(t) for c, t in df.dtypes.items()},
        'null_counts':     df.isnull().sum().to_dict(),
        'numeric_summary': numeric_summary,
        'correlations':    correlations,
        'category_counts': category_counts,
        'numeric_cols':    num_cols,
        'cat_cols':        cat_cols,
    }"""

MODEL_IMPL = """\
def train_and_evaluate(df: pd.DataFrame, target_col: str,
                        test_size: float = 0.2,
                        random_state: int = 42) -> dict:
    \"\"\"
    Auto-select numeric features, scale, train LinearRegression with 5-fold CV,
    and evaluate on a held-out test set.

    Returns dict with keys:
        target, features, cv_r2 (mean/std), test_r2, test_rmse, test_mae,
        coefficients (feature → value), n_train, n_test
    \"\"\"
    if target_col not in df.columns:
        return {'error': f'target column {target_col!r} not found'}

    num_cols     = df.select_dtypes(include='number').columns.tolist()
    feature_cols = [c for c in num_cols if c != target_col]

    if not feature_cols:
        return {'error': 'no numeric feature columns found'}

    sub   = df[feature_cols + [target_col]].dropna()
    X     = sub[feature_cols]
    y     = sub[target_col]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state
    )
    scaler   = StandardScaler()
    X_tr_s   = pd.DataFrame(scaler.fit_transform(X_train), columns=feature_cols)
    X_te_s   = pd.DataFrame(scaler.transform(X_test),      columns=feature_cols)

    model = LinearRegression()
    kf    = KFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(model, X_tr_s, y_train, cv=kf, scoring='r2')

    model.fit(X_tr_s, y_train)
    y_pred = model.predict(X_te_s)

    return {
        'target':    target_col,
        'features':  feature_cols,
        'cv_r2':     {'mean': round(float(cv_scores.mean()), 4),
                      'std':  round(float(cv_scores.std()),  4)},
        'test_r2':   round(float(r2_score(y_test, y_pred)),                         4),
        'test_rmse': round(float(np.sqrt(mean_squared_error(y_test, y_pred))),       2),
        'test_mae':  round(float(mean_absolute_error(y_test, y_pred)),               2),
        'coefficients': {
            col: round(float(c), 4)
            for col, c in zip(feature_cols, model.coef_)
        },
        'n_train': int(len(X_train)),
        'n_test':  int(len(X_test)),
    }"""

NARRATE_IMPL = """\
def narrate_insights(eda: dict, model_report: dict,
                     title: str = 'Dataset',
                     model: str = 'llama3.2') -> str:
    \"\"\"
    Generate a 3-sentence executive summary via Ollama (llama3.2).
    Falls back to a structured plain-text summary if Ollama is unavailable.
    \"\"\"
    shape    = eda.get('shape', {})
    num_cols = eda.get('numeric_cols', [])
    cat_cols = eda.get('cat_cols', [])

    context_parts = [
        f\"Dataset: {title}\",
        f\"Shape: {shape.get('rows', '?')} rows \\u00d7 {shape.get('cols', '?')} columns\",
        f\"Numeric columns: {', '.join(num_cols) if num_cols else 'none'}\",
        f\"Categorical columns: {', '.join(cat_cols) if cat_cols else 'none'}\",
    ]

    num_summary = eda.get('numeric_summary', {})
    for col, stats in list(num_summary.items())[:4]:
        context_parts.append(
            f\"  {col}: mean={stats['mean']:.2f}, std={stats['std']:.2f}, \"
            f\"min={stats['min']:.2f}, max={stats['max']:.2f}\"
        )

    if model_report and 'test_r2' in model_report:
        context_parts.append(
            f\"LinearRegression predicting {model_report['target']}: \"
            f\"CV R\\u00b2={model_report['cv_r2']['mean']:.4f} \\u00b1 {model_report['cv_r2']['std']:.4f}, \"
            f\"Test R\\u00b2={model_report['test_r2']:.4f}, \"
            f\"RMSE={model_report['test_rmse']:.2f}\"
        )
        top = sorted(model_report.get('coefficients', {}).items(),
                     key=lambda kv: abs(kv[1]), reverse=True)
        if top:
            context_parts.append(
                f\"Strongest predictor: {top[0][0]} (coef={top[0][1]:.4f})\"
            )

    context = '\\n'.join(context_parts)
    prompt  = (
        f\"You are a concise data analyst. Write a 3-sentence executive summary \"
        f\"for a non-technical stakeholder based on this analysis:\\n\\n{context}\\n\\n\"
        f\"Cover: (1) what the data contains, (2) the key pattern or insight, \"
        f\"(3) one concrete recommendation.\"
    )

    try:
        response = ollama.chat(
            model=model,
            messages=[{'role': 'user', 'content': prompt}],
        )
        return response['message']['content'].strip()
    except Exception:
        lines = [f\"Analysis of {title}: {shape.get('rows', '?')} rows, "
                 f\"{shape.get('cols', '?')} columns.\"]
        if num_cols:
            lines.append(f\"Numeric features: {', '.join(num_cols)}.\")
        if model_report and 'test_r2' in model_report:
            lines.append(
                f\"Predictive model (LinearRegression \\u2192 {model_report['target']}): \"
                f\"Test R\\u00b2={model_report['test_r2']:.4f}, "
                f\"RMSE={model_report['test_rmse']:.2f}.\"
            )
        return ' '.join(lines)"""

INSIGHT_ENGINE_IMPL = """\
class InsightEngine:
    \"\"\"
    End-to-end data insight pipeline for Section 3 capstone.

    Usage:
        engine = InsightEngine(title='Retail Sales 2023')
        result = engine.run(df_or_csv, target_col='revenue')
        engine.save_chart('dashboard.png')
        print(engine.narrative)
    \"\"\"

    def __init__(self, title: str = 'Dataset', llm_model: str = 'llama3.2'):
        self.title        = title
        self.llm_model    = llm_model
        self.df           = None
        self.eda          = None
        self.model_report = None
        self.narrative    = None

    def run(self, source, target_col: str = None) -> dict:
        \"\"\"
        Full pipeline:
          1. load_and_clean(source)
          2. run_eda(df)
          3. train_and_evaluate(df, target_col)  — if target_col provided
          4. narrate_insights(eda, model_report)

        Returns dict with keys: df, eda, model_report, narrative
        \"\"\"
        self.df           = load_and_clean(source)
        self.eda          = run_eda(self.df)
        self.model_report = {}
        if target_col and target_col in self.df.columns:
            self.model_report = train_and_evaluate(self.df, target_col)
        self.narrative = narrate_insights(
            self.eda, self.model_report, self.title, self.llm_model
        )
        return {
            'df':           self.df,
            'eda':          self.eda,
            'model_report': self.model_report,
            'narrative':    self.narrative,
        }

    def save_chart(self, out_path: str = 'insight_report.png') -> str:
        \"\"\"
        Save a 2\\u00d72 dashboard:
          - Top-left:  histogram of first numeric column
          - Top-right: correlation heatmap (numeric columns)
          - Bot-left:  horizontal bar chart of first categorical column
          - Bot-right: scatter of first two numeric columns
        \"\"\"
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt

        if self.df is None:
            raise RuntimeError('Call run() before save_chart().')

        df       = self.df
        num_cols = self.eda.get('numeric_cols', [])
        cat_cols = self.eda.get('cat_cols', [])

        fig, axes = plt.subplots(2, 2, figsize=(13, 9))
        fig.suptitle(f'{self.title} \\u2014 Insight Report', fontsize=14)

        # Top-left: distribution of first numeric column
        ax = axes[0, 0]
        if num_cols:
            col = num_cols[0]
            ax.hist(df[col].dropna(), bins=20, edgecolor='white', color='steelblue')
            ax.set_title(f'Distribution: {col}')
            ax.set_xlabel(col); ax.set_ylabel('Count')

        # Top-right: correlation heatmap
        ax = axes[0, 1]
        if len(num_cols) >= 2:
            corr = df[num_cols].corr()
            ax.imshow(corr, cmap='RdBu', vmin=-1, vmax=1)
            ticks = range(len(num_cols))
            ax.set_xticks(ticks); ax.set_xticklabels(num_cols, rotation=45, ha='right')
            ax.set_yticks(ticks); ax.set_yticklabels(num_cols)
            ax.set_title('Correlation Heatmap')
            for i in range(len(num_cols)):
                for j in range(len(num_cols)):
                    ax.text(j, i, f'{corr.iloc[i, j]:.2f}',
                            ha='center', va='center', fontsize=7)

        # Bottom-left: top category counts
        ax = axes[1, 0]
        if cat_cols:
            col = cat_cols[0]
            vc  = df[col].value_counts().head(8)
            ax.barh(vc.index.tolist()[::-1], vc.values[::-1], color='coral')
            ax.set_title(f'Counts by {col}')
            ax.set_xlabel('Count')

        # Bottom-right: scatter of first two numeric columns
        ax = axes[1, 1]
        if len(num_cols) >= 2:
            ax.scatter(df[num_cols[0]].dropna(), df[num_cols[1]].dropna(),
                       alpha=0.35, color='teal', s=18)
            ax.set_title(f'{num_cols[0]} vs {num_cols[1]}')
            ax.set_xlabel(num_cols[0]); ax.set_ylabel(num_cols[1])

        plt.tight_layout()
        fig.savefig(out_path, bbox_inches='tight', dpi=100)
        plt.close('all')
        return out_path"""

# Cumulative provided stacks
_BEFORE_EDA    = "\n\n\n".join([MAKE_DATA, LOAD_AND_CLEAN_IMPL])
_BEFORE_MODEL  = "\n\n\n".join([MAKE_DATA, LOAD_AND_CLEAN_IMPL, EDA_IMPL])
_BEFORE_NARR   = "\n\n\n".join([MAKE_DATA, LOAD_AND_CLEAN_IMPL, EDA_IMPL, MODEL_IMPL])
ALL_IMPLS      = "\n\n\n".join([MAKE_DATA, LOAD_AND_CLEAN_IMPL, EDA_IMPL,
                                 MODEL_IMPL, NARRATE_IMPL])


# ---------------------------------------------------------------------------
# Exercise 01 — load_and_clean
# ---------------------------------------------------------------------------

def ex01():
    global _cid; _cid = 0
    return [
        md(
            "# Day 050 — Exercise 1: load_and_clean\n\n"
            "**What you'll build:** `load_and_clean(source) -> pd.DataFrame` — "
            "accept a CSV string, file path, or DataFrame; parse date columns; "
            "fill numeric NaN with the column median; drop exact duplicate rows.\n\n"
            "**Why it matters:** Every real dataset is dirty. `load_and_clean` is "
            "the first stage of the Insight Engine. It standardises the input so "
            "the rest of the pipeline can assume no nulls in numeric columns and "
            "no duplicate rows."
        ),
        md("## Provided: Setup + Data Generator"),
        code(MAKE_DATA),
        md("## Your Implementation"),
        code(
            "def load_and_clean(source) -> pd.DataFrame:\n"
            '    """\n'
            "    Load from CSV string / file path / DataFrame, then:\n"
            "      1. Parse columns containing 'date' or 'time' in their name → datetime64\n"
            "      2. Fill numeric NaN with the column median\n"
            "      3. Drop exact duplicate rows\n"
            '    """\n'
            "    # Step 1 — Load\n"
            "    if isinstance(source, pd.DataFrame):\n"
            "        df = source.copy()\n"
            "    elif isinstance(source, str) and ('\\n' in source or ',' in source[:200]):\n"
            "        df = pd.read_csv(io.StringIO(source))\n"
            "    else:\n"
            "        df = pd.read_csv(source)\n"
            "\n"
            "    # Step 2 — Parse date columns (look for 'date' or 'time' in column name)\n"
            "    # TODO: for col in df.columns:\n"
            "    #     if any(kw in col.lower() for kw in ('date', 'time')):\n"
            "    #         try:\n"
            "    #             df[col] = pd.to_datetime(df[col], errors='coerce')\n"
            "    #         except Exception:\n"
            "    #             pass\n"
            "\n"
            "    # Step 3 — Fill numeric NaN with median\n"
            "    # TODO: for col in df.select_dtypes(include='number').columns:\n"
            "    #     df[col] = df[col].fillna(df[col].median())\n"
            "\n"
            "    # Step 4 — Drop duplicates\n"
            "    # TODO: df = df.drop_duplicates().reset_index(drop=True)\n"
            "\n"
            "    return df"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    raw = make_sample_data(200)\n"
            "\n"
            "    # Check 1: returns DataFrame\n"
            "    try:\n"
            "        df = load_and_clean(raw)\n"
            "        assert isinstance(df, pd.DataFrame), \\\n"
            "            f'expected DataFrame, got {type(df).__name__}'\n"
            "        passed += 1; print(f'\\u2705 Check 1: returns DataFrame with shape {df.shape}')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: no NaN in numeric columns after cleaning\n"
            "    try:\n"
            "        num_nulls = df.select_dtypes(include='number').isnull().sum().sum()\n"
            "        assert num_nulls == 0, \\\n"
            "            f'expected 0 numeric nulls after cleaning, got {num_nulls}'\n"
            "        passed += 1; print(f'\\u2705 Check 2: 0 numeric nulls after cleaning')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: no duplicate rows\n"
            "    try:\n"
            "        dupes = int(df.duplicated().sum())\n"
            "        assert dupes == 0, f'expected 0 duplicates, got {dupes}'\n"
            "        passed += 1; print(f'\\u2705 Check 3: 0 duplicate rows')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: date column is datetime64\n"
            "    try:\n"
            "        assert 'date' in df.columns, 'expected a date column'\n"
            "        assert pd.api.types.is_datetime64_any_dtype(df['date']), \\\n"
            "            f\"date column dtype is {df['date'].dtype}, expected datetime64\"\n"
            "        passed += 1; print(f'\\u2705 Check 4: date column is datetime64')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: works with CSV string input too\n"
            "    try:\n"
            "        csv_text = raw.to_csv(index=False)\n"
            "        df2 = load_and_clean(csv_text)\n"
            "        assert isinstance(df2, pd.DataFrame)\n"
            "        assert df2.select_dtypes(include='number').isnull().sum().sum() == 0\n"
            "        passed += 1; print(f'\\u2705 Check 5: CSV string input works')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 5: {e}')\n"
            "\n"
            "    if passed == total:\n"
            "        print('\\U0001f389 Exercise complete!')\n"
            "    print(f'\\nScore: {passed}/{total}')\n"
            "\n"
            "\n"
            "_run_checks()"
        ),
        md(
            "## Solution\n\n"
            "<details>\n"
            "<summary>Click to reveal</summary>\n\n"
            "```python\n"
            + LOAD_AND_CLEAN_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 02 — run_eda
# ---------------------------------------------------------------------------

def ex02():
    global _cid; _cid = 100
    return [
        md(
            "# Day 050 — Exercise 2: run_eda\n\n"
            "**What you'll build:** `run_eda(df) -> dict` — compute a comprehensive "
            "EDA summary with keys: `shape`, `columns`, `dtypes`, `null_counts`, "
            "`numeric_summary`, `correlations`, `category_counts`, `numeric_cols`, `cat_cols`.\n\n"
            "**Why it matters:** `run_eda` gives the Insight Engine a structured "
            "view of any dataset without prior knowledge of its schema. Downstream "
            "functions — narration, charting, modelling — all pull from this dict."
        ),
        md("## Provided: Setup + load_and_clean"),
        code(_BEFORE_EDA),
        md("## Your Implementation"),
        code(
            "def run_eda(df: pd.DataFrame) -> dict:\n"
            '    """\n'
            "    Compute EDA summary dict with keys:\n"
            "        shape, columns, dtypes, null_counts,\n"
            "        numeric_summary, correlations, category_counts,\n"
            "        numeric_cols, cat_cols\n"
            '    """\n'
            "    num_cols = df.select_dtypes(include='number').columns.tolist()\n"
            "    cat_cols = df.select_dtypes(include='object').columns.tolist()\n"
            "\n"
            "    # TODO: numeric_summary — dict of col → {mean, std, min, max, median}\n"
            "    numeric_summary = {}\n"
            "    # for col in num_cols:\n"
            "    #     s = df[col].dropna()\n"
            "    #     numeric_summary[col] = {\n"
            "    #         'mean':   round(float(s.mean()),   4),\n"
            "    #         'std':    round(float(s.std()),    4),\n"
            "    #         'min':    round(float(s.min()),    4),\n"
            "    #         'max':    round(float(s.max()),    4),\n"
            "    #         'median': round(float(s.median()), 4),\n"
            "    #     }\n"
            "\n"
            "    # TODO: correlations — dict of col → {other_col → pearson_r}\n"
            "    correlations = {}\n"
            "    # if len(num_cols) >= 2:\n"
            "    #     cm = df[num_cols].corr()\n"
            "    #     for col in num_cols:\n"
            "    #         correlations[col] = {\n"
            "    #             other: round(float(cm.loc[col, other]), 4)\n"
            "    #             for other in num_cols if other != col\n"
            "    #         }\n"
            "\n"
            "    # TODO: category_counts — dict of col → value_counts top 10\n"
            "    category_counts = {}\n"
            "    # for col in cat_cols:\n"
            "    #     category_counts[col] = df[col].value_counts().head(10).to_dict()\n"
            "\n"
            "    return {\n"
            "        'shape':           {'rows': int(df.shape[0]), 'cols': int(df.shape[1])},\n"
            "        'columns':         df.columns.tolist(),\n"
            "        'dtypes':          {c: str(t) for c, t in df.dtypes.items()},\n"
            "        'null_counts':     df.isnull().sum().to_dict(),\n"
            "        'numeric_summary': numeric_summary,\n"
            "        'correlations':    correlations,\n"
            "        'category_counts': category_counts,\n"
            "        'numeric_cols':    num_cols,\n"
            "        'cat_cols':        cat_cols,\n"
            "    }"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    df = load_and_clean(make_sample_data(200))\n"
            "\n"
            "    # Check 1: returns dict\n"
            "    try:\n"
            "        result = run_eda(df)\n"
            "        assert isinstance(result, dict), \\\n"
            "            f'expected dict, got {type(result).__name__}'\n"
            "        passed += 1; print(f'\\u2705 Check 1: run_eda returns dict')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: all 9 required keys present\n"
            "    try:\n"
            "        for k in ('shape', 'columns', 'dtypes', 'null_counts',\n"
            "                  'numeric_summary', 'correlations', 'category_counts',\n"
            "                  'numeric_cols', 'cat_cols'):\n"
            "            assert k in result, f'missing key: {k!r}'\n"
            "        passed += 1; print(f'\\u2705 Check 2: all 9 required keys present')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: shape matches dataframe\n"
            "    try:\n"
            "        assert result['shape']['rows'] == len(df), \\\n"
            "            f\"shape rows={result['shape']['rows']} != {len(df)}\"\n"
            "        assert result['shape']['cols'] == df.shape[1]\n"
            "        passed += 1; print(f\"\\u2705 Check 3: shape={result['shape']} matches df\")\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: numeric_summary has entries for all numeric columns\n"
            "    try:\n"
            "        ns = result['numeric_summary']\n"
            "        assert len(ns) > 0, 'numeric_summary is empty'\n"
            "        for col in result['numeric_cols']:\n"
            "            assert col in ns, f'missing numeric_summary entry for {col!r}'\n"
            "            for stat in ('mean', 'std', 'min', 'max', 'median'):\n"
            "                assert stat in ns[col], f'missing stat {stat!r} for {col!r}'\n"
            "        passed += 1; print(f'\\u2705 Check 4: numeric_summary has all stats')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: correlations is non-empty (at least 2 numeric columns)\n"
            "    try:\n"
            "        corr = result['correlations']\n"
            "        assert len(corr) > 0, 'correlations dict is empty'\n"
            "        # Values should be in [-1, 1]\n"
            "        for col, others in corr.items():\n"
            "            for other, r in others.items():\n"
            "                assert -1.0 <= r <= 1.0, f'correlation {col}-{other}={r} out of range'\n"
            "        passed += 1; print(f'\\u2705 Check 5: correlations dict populated with valid values')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 5: {e}')\n"
            "\n"
            "    if passed == total:\n"
            "        print('\\U0001f389 Exercise complete!')\n"
            "    print(f'\\nScore: {passed}/{total}')\n"
            "\n"
            "\n"
            "_run_checks()"
        ),
        md(
            "## Solution\n\n"
            "<details>\n"
            "<summary>Click to reveal</summary>\n\n"
            "```python\n"
            + EDA_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 03 — train_and_evaluate
# ---------------------------------------------------------------------------

def ex03():
    global _cid; _cid = 200
    return [
        md(
            "# Day 050 — Exercise 3: train_and_evaluate\n\n"
            "**What you'll build:** `train_and_evaluate(df, target_col, ...) -> dict` "
            "— automatically select numeric features, scale them, train LinearRegression "
            "with 5-fold CV, and evaluate on a held-out test set.\n\n"
            "**Why it matters:** The Insight Engine needs to work on any tabular "
            "dataset without the user specifying features manually. `train_and_evaluate` "
            "encodes the full Day 48+49 pipeline — feature selection, scaling, CV, "
            "evaluation — in one auto-pilot function."
        ),
        md("## Provided: Setup + load_and_clean + run_eda"),
        code(_BEFORE_MODEL),
        md("## Your Implementation"),
        code(
            "def train_and_evaluate(df: pd.DataFrame, target_col: str,\n"
            "                        test_size: float = 0.2,\n"
            "                        random_state: int = 42) -> dict:\n"
            '    """\n'
            "    Auto-select numeric features (exclude target_col), scale with\n"
            "    StandardScaler, 5-fold cross-validate, fit, and evaluate on test set.\n\n"
            "    Returns dict with keys:\n"
            "        target, features, cv_r2 (mean/std),\n"
            "        test_r2, test_rmse, test_mae,\n"
            "        coefficients (feature → value), n_train, n_test\n"
            '    """\n'
            "    if target_col not in df.columns:\n"
            "        return {'error': f'target column {target_col!r} not found'}\n"
            "\n"
            "    num_cols     = df.select_dtypes(include='number').columns.tolist()\n"
            "    feature_cols = [c for c in num_cols if c != target_col]\n"
            "\n"
            "    if not feature_cols:\n"
            "        return {'error': 'no numeric feature columns found'}\n"
            "\n"
            "    sub = df[feature_cols + [target_col]].dropna()\n"
            "    X   = sub[feature_cols]\n"
            "    y   = sub[target_col]\n"
            "\n"
            "    X_train, X_test, y_train, y_test = train_test_split(\n"
            "        X, y, test_size=test_size, random_state=random_state\n"
            "    )\n"
            "    scaler = StandardScaler()\n"
            "    X_tr_s = pd.DataFrame(scaler.fit_transform(X_train), columns=feature_cols)\n"
            "    X_te_s = pd.DataFrame(scaler.transform(X_test),      columns=feature_cols)\n"
            "\n"
            "    # TODO: 5-fold CV\n"
            "    # kf    = KFold(n_splits=5, shuffle=True, random_state=42)\n"
            "    # model = LinearRegression()\n"
            "    # cv_scores = cross_val_score(model, X_tr_s, y_train, cv=kf, scoring='r2')\n"
            "\n"
            "    # TODO: fit + evaluate\n"
            "    # model.fit(X_tr_s, y_train)\n"
            "    # y_pred = model.predict(X_te_s)\n"
            "\n"
            "    # TODO: return {\n"
            "    #     'target':    target_col,\n"
            "    #     'features':  feature_cols,\n"
            "    #     'cv_r2':     {'mean': round(float(cv_scores.mean()), 4),\n"
            "    #                   'std':  round(float(cv_scores.std()),  4)},\n"
            "    #     'test_r2':   round(float(r2_score(y_test, y_pred)), 4),\n"
            "    #     'test_rmse': round(float(np.sqrt(mean_squared_error(y_test, y_pred))), 2),\n"
            "    #     'test_mae':  round(float(mean_absolute_error(y_test, y_pred)), 2),\n"
            "    #     'coefficients': {\n"
            "    #         col: round(float(c), 4)\n"
            "    #         for col, c in zip(feature_cols, model.coef_)\n"
            "    #     },\n"
            "    #     'n_train': int(len(X_train)),\n"
            "    #     'n_test':  int(len(X_test)),\n"
            "    # }\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    df = load_and_clean(make_sample_data(200))\n"
            "\n"
            "    # Check 1: returns dict\n"
            "    try:\n"
            "        result = train_and_evaluate(df, 'revenue')\n"
            "        assert isinstance(result, dict), \\\n"
            "            f'expected dict, got {type(result).__name__}'\n"
            "        assert 'error' not in result, f\"error: {result.get('error')}\"\n"
            "        passed += 1; print(f'\\u2705 Check 1: train_and_evaluate returns dict')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: all required keys present\n"
            "    try:\n"
            "        for k in ('target', 'features', 'cv_r2', 'test_r2',\n"
            "                  'test_rmse', 'test_mae', 'coefficients', 'n_train', 'n_test'):\n"
            "            assert k in result, f'missing key: {k!r}'\n"
            "        passed += 1; print(f'\\u2705 Check 2: all 9 required keys present')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: test_r2 > 0.5 (model learns from data)\n"
            "    try:\n"
            "        r2 = result['test_r2']\n"
            "        assert r2 > 0.5, \\\n"
            "            f'test_r2 should be > 0.5 on this dataset, got {r2}'\n"
            "        passed += 1; print(f'\\u2705 Check 3: test_r2={r2} > 0.5')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: coefficients has one entry per feature\n"
            "    try:\n"
            "        coef = result['coefficients']\n"
            "        feats = result['features']\n"
            "        assert len(coef) == len(feats), \\\n"
            "            f'coefficients has {len(coef)} entries but {len(feats)} features'\n"
            "        for f in feats:\n"
            "            assert f in coef, f'missing coefficient for {f!r}'\n"
            "        passed += 1; print(f'\\u2705 Check 4: coefficients has {len(coef)} entries matching features')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: n_train + n_test == total rows used\n"
            "    try:\n"
            "        n_used = result['n_train'] + result['n_test']\n"
            "        assert n_used <= len(df), \\\n"
            "            f'n_train + n_test = {n_used} exceeds df length {len(df)}'\n"
            "        assert result['n_test'] > 0 and result['n_train'] > 0\n"
            "        passed += 1; print(f\"\\u2705 Check 5: n_train={result['n_train']}, n_test={result['n_test']}\")\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 5: {e}')\n"
            "\n"
            "    if passed == total:\n"
            "        print('\\U0001f389 Exercise complete!')\n"
            "    print(f'\\nScore: {passed}/{total}')\n"
            "\n"
            "\n"
            "_run_checks()"
        ),
        md(
            "## Solution\n\n"
            "<details>\n"
            "<summary>Click to reveal</summary>\n\n"
            "```python\n"
            + MODEL_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 04 — narrate_insights
# ---------------------------------------------------------------------------

def ex04():
    global _cid; _cid = 300
    return [
        md(
            "# Day 050 — Exercise 4: narrate_insights\n\n"
            "**What you'll build:** `narrate_insights(eda, model_report, title, "
            "model='llama3.2') -> str` — use Ollama to generate a 3-sentence "
            "executive summary from the EDA dict and model report dict. Include a "
            "try/except fallback for when Ollama is not running.\n\n"
            "**Why it matters:** This is the AI layer that transforms structured "
            "statistics into plain-English insight. A stakeholder reading the output "
            "should understand what the data contains, what the main pattern is, and "
            "what action to take — without seeing a single number."
        ),
        md("## Provided: Setup + load_and_clean + run_eda + train_and_evaluate"),
        code(_BEFORE_NARR),
        md("## Your Implementation"),
        code(
            "def narrate_insights(eda: dict, model_report: dict,\n"
            "                     title: str = 'Dataset',\n"
            "                     model: str = 'llama3.2') -> str:\n"
            '    """\n'
            "    Build a context string from eda + model_report, then call\n"
            "    ollama.chat to produce a 3-sentence executive summary.\n\n"
            "    If Ollama is unavailable, return a plain-text fallback summary.\n"
            '    """\n'
            "    shape    = eda.get('shape', {})\n"
            "    num_cols = eda.get('numeric_cols', [])\n"
            "    cat_cols = eda.get('cat_cols', [])\n"
            "\n"
            "    # TODO: Build context string from EDA + model_report\n"
            "    # context = ...\n"
            "\n"
            "    # TODO: Build a user prompt asking for a 3-sentence executive summary\n"
            "    # prompt = ...\n"
            "\n"
            "    # TODO: Call ollama.chat(model=model, messages=[{'role':'user','content':prompt}])\n"
            "    # Return response['message']['content'].strip()\n"
            "    # Wrap in try/except — return a fallback string if Ollama is unavailable\n"
            "\n"
            "    try:\n"
            "        # TODO: response = ollama.chat(model=model, messages=[...])\n"
            "        # TODO: return response['message']['content'].strip()\n"
            "        pass\n"
            "    except Exception:\n"
            "        # Fallback: return a structured plain-text summary\n"
            "        lines = [f'Analysis of {title}: '\n"
            "                 f\"{shape.get('rows', '?')} rows, {shape.get('cols', '?')} columns.\"]\n"
            "        if num_cols:\n"
            "            lines.append(f'Numeric features: {\", \".join(num_cols)}.')\n"
            "        if model_report and 'test_r2' in model_report:\n"
            "            lines.append(\n"
            "                f\"Predictive model (LinearRegression \\u2192 {model_report['target']}): \"\n"
            "                f\"Test R\\u00b2={model_report['test_r2']:.4f}, \"\n"
            "                f\"RMSE={model_report['test_rmse']:.2f}.\"\n"
            "            )\n"
            "        return ' '.join(lines)"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    df    = load_and_clean(make_sample_data(200))\n"
            "    eda   = run_eda(df)\n"
            "    mr    = train_and_evaluate(df, 'revenue')\n"
            "\n"
            "    # Check 1: returns a string\n"
            "    try:\n"
            "        result = narrate_insights(eda, mr, title='Retail Sales')\n"
            "        assert isinstance(result, str), \\\n"
            "            f'expected str, got {type(result).__name__}'\n"
            "        passed += 1; print(f'\\u2705 Check 1: narrate_insights returns str')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: string is non-empty (> 20 chars)\n"
            "    try:\n"
            "        assert len(result) > 20, \\\n"
            "            f'narrative is too short ({len(result)} chars)'\n"
            "        passed += 1; print(f'\\u2705 Check 2: narrative length={len(result)} > 20')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: works with empty model_report (no model run)\n"
            "    try:\n"
            "        fallback = narrate_insights(eda, {}, title='Test')\n"
            "        assert isinstance(fallback, str) and len(fallback) > 10\n"
            "        passed += 1; print(f'\\u2705 Check 3: works with empty model_report')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: does not raise on minimal EDA dict\n"
            "    try:\n"
            "        minimal_eda = {'shape': {'rows': 10, 'cols': 3},\n"
            "                       'numeric_cols': ['a'], 'cat_cols': [],\n"
            "                       'numeric_summary': {}, 'correlations': {},\n"
            "                       'category_counts': {}}\n"
            "        out = narrate_insights(minimal_eda, {}, title='Min')\n"
            "        assert isinstance(out, str)\n"
            "        passed += 1; print(f'\\u2705 Check 4: handles minimal EDA dict')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: narrative printed for inspection\n"
            "    try:\n"
            "        print(f'\\n--- Narrative ({len(result)} chars) ---')\n"
            "        print(result[:500])\n"
            "        passed += 1; print(f'\\n\\u2705 Check 5: narrative displayed')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 5: {e}')\n"
            "\n"
            "    if passed == total:\n"
            "        print('\\U0001f389 Exercise complete!')\n"
            "    print(f'\\nScore: {passed}/{total}')\n"
            "\n"
            "\n"
            "_run_checks()"
        ),
        md(
            "## Solution\n\n"
            "<details>\n"
            "<summary>Click to reveal</summary>\n\n"
            "```python\n"
            + NARRATE_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 05 — InsightEngine class
# ---------------------------------------------------------------------------

def ex05():
    global _cid; _cid = 400
    return [
        md(
            "# Day 050 — Exercise 5: InsightEngine Class\n\n"
            "**What you'll build:** The `InsightEngine` class — the Section 3 capstone:\n"
            "- `__init__(title, llm_model='llama3.2')` — store config, init state\n"
            "- `run(source, target_col=None) -> dict` — load → clean → EDA → [model] → narrate\n"
            "- `save_chart(out_path='insight_report.png') -> str` — 2×2 matplotlib dashboard\n\n"
            "**Why it matters:** This is the complete Section 3 pipeline in one object. "
            "A user hands it any CSV and a target column and gets back a cleaned DataFrame, "
            "EDA report, model metrics, an AI narrative, and a chart — automatically."
        ),
        md("## Provided: All Helper Functions"),
        code(ALL_IMPLS),
        md("## Your Implementation"),
        code(
            "import matplotlib\n"
            "matplotlib.use('Agg')\n"
            "import matplotlib.pyplot as plt\n"
            "\n"
            "\n"
            "class InsightEngine:\n"
            '    """\n'
            "    End-to-end data insight pipeline.\n\n"
            "    Usage:\n"
            "        engine = InsightEngine(title='Retail Sales 2023')\n"
            "        result = engine.run(df_or_csv, target_col='revenue')\n"
            "        engine.save_chart('dashboard.png')\n"
            "        print(engine.narrative)\n"
            '    """\n'
            "\n"
            "    def __init__(self, title: str = 'Dataset', llm_model: str = 'llama3.2'):\n"
            "        # TODO: self.title, self.llm_model, self.df, self.eda,\n"
            "        #       self.model_report, self.narrative — all initialised here\n"
            "        pass\n"
            "\n"
            "    def run(self, source, target_col: str = None) -> dict:\n"
            '        """\n'
            "        Full pipeline:\n"
            "          1. self.df     = load_and_clean(source)\n"
            "          2. self.eda    = run_eda(self.df)\n"
            "          3. self.model_report = train_and_evaluate(self.df, target_col)\n"
            "             (only if target_col is provided and exists in df)\n"
            "          4. self.narrative = narrate_insights(self.eda, self.model_report, ...)\n"
            "        Returns dict with keys: df, eda, model_report, narrative\n"
            '        """\n'
            "        # TODO: implement all 4 steps\n"
            "        pass\n"
            "\n"
            "    def save_chart(self, out_path: str = 'insight_report.png') -> str:\n"
            '        """\n'
            "        Save a 2x2 dashboard PNG.\n"
            "        Panels: [distribution, correlation heatmap]\n"
            "                [top-category bar, scatter of first 2 numeric cols]\n"
            "        Must raise RuntimeError if run() has not been called.\n"
            '        """\n'
            "        if self.df is None:\n"
            "            raise RuntimeError('Call run() before save_chart().')\n"
            "\n"
            "        # TODO: create 2x2 figure and fill each panel\n"
            "        # TODO: fig.savefig(out_path, bbox_inches='tight', dpi=100)\n"
            "        # TODO: plt.close('all')\n"
            "        # TODO: return out_path\n"
            "        pass"
        ),
        md("## Check Your Work"),
        code(
            "import os\n"
            "\n"
            "\n"
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: class defined with run and save_chart\n"
            "    try:\n"
            "        assert 'InsightEngine' in globals()\n"
            "        for m in ('run', 'save_chart'):\n"
            "            assert hasattr(InsightEngine, m), f'missing method: {m}'\n"
            "        passed += 1; print('\\u2705 Check 1: InsightEngine has run and save_chart')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: run() returns dict with 4 keys\n"
            "    try:\n"
            "        engine = InsightEngine(title='Test Dataset')\n"
            "        result = engine.run(make_sample_data(200), target_col='revenue')\n"
            "        assert isinstance(result, dict), \\\n"
            "            f'run() must return dict, got {type(result).__name__}'\n"
            "        for k in ('df', 'eda', 'model_report', 'narrative'):\n"
            "            assert k in result, f'missing key: {k!r}'\n"
            "        passed += 1; print('\\u2705 Check 2: run() returns dict with 4 keys')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 3: engine.df is a cleaned DataFrame (no numeric nulls)\n"
            "    try:\n"
            "        assert isinstance(engine.df, pd.DataFrame), \\\n"
            "            'engine.df must be a DataFrame'\n"
            "        num_nulls = engine.df.select_dtypes(include='number').isnull().sum().sum()\n"
            "        assert num_nulls == 0, f'engine.df has {num_nulls} numeric nulls'\n"
            "        passed += 1; print(f'\\u2705 Check 3: engine.df is cleaned DataFrame, shape={engine.df.shape}')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: engine.narrative is a non-empty string\n"
            "    try:\n"
            "        assert isinstance(engine.narrative, str) and len(engine.narrative) > 20, \\\n"
            "            f'engine.narrative must be a non-empty string, got {engine.narrative!r}'\n"
            "        passed += 1; print(f'\\u2705 Check 4: narrative length={len(engine.narrative)}')\n"
            "        print('\\n--- Narrative ---')\n"
            "        print(engine.narrative[:400])\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: save_chart() writes a PNG file\n"
            "    try:\n"
            "        out = engine.save_chart('test_chart.png')\n"
            "        assert out == 'test_chart.png' or os.path.exists('test_chart.png'), \\\n"
            "            'save_chart must save a PNG file'\n"
            "        assert os.path.getsize('test_chart.png') > 1000, 'PNG is too small'\n"
            "        passed += 1; print(f'\\u2705 Check 5: test_chart.png saved ({os.path.getsize(\"test_chart.png\")} bytes)')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 5: {e}')\n"
            "\n"
            "    if passed == total:\n"
            "        print('\\n\\U0001f389 Exercise complete!')\n"
            "    print(f'\\nScore: {passed}/{total}')\n"
            "\n"
            "\n"
            "_run_checks()"
        ),
        md(
            "## Solution\n\n"
            "<details>\n"
            "<summary>Click to reveal</summary>\n\n"
            "```python\n"
            + INSIGHT_ENGINE_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Project notebook
# ---------------------------------------------------------------------------

def project_nb():
    global _cid; _cid = 500
    all_code = ALL_IMPLS + "\n\n\n" + INSIGHT_ENGINE_IMPL
    return [
        md(
            "# Day 050 Project: Build the Insight Engine\n\n"
            "## What You're Building\n\n"
            "The Section 3 capstone: run the complete InsightEngine on the retail "
            "sales dataset and produce a full AI-narrated report.\n\n"
            "## Project Requirements\n\n"
            "1. Create `engine = InsightEngine(title='Retail Sales 2023')`\n"
            "2. Call `result = engine.run(df, target_col='revenue')` "
            "   where `df = make_sample_data(300)`\n"
            "3. Save a 2×2 dashboard to `insight_report.png`\n"
            "4. Print `engine.narrative` (the AI executive summary)\n"
            "5. Print the model report (CV R², test R², RMSE, top feature)\n"
            "6. Run `_run_project_checks()` to verify\n\n"
            "## Bonus Challenges\n\n"
            "- Try the engine on a real CSV you have (or download one from Kaggle)\n"
            "- Extend `save_chart` with a 5th panel: time series of revenue by week "
            "  (requires the date column to be set as the index with `parse_time_series`)\n"
            "- Add a `compare_models` method that trains both LinearRegression and "
            "  a DecisionTreeRegressor and returns the better one by CV R²"
        ),
        md("## Provided: All Implementations"),
        code(all_code),
        md("## Your Pipeline"),
        code(
            "import matplotlib\n"
            "matplotlib.use('Agg')\n"
            "import matplotlib.pyplot as plt\n"
            "\n"
            "# TODO: engine = InsightEngine(title='Retail Sales 2023')\n"
            "# TODO: result = engine.run(make_sample_data(300), target_col='revenue')\n"
            "# TODO: engine.save_chart('insight_report.png')\n"
            "\n"
            "# TODO: print('=== AI Executive Summary ===')\n"
            "# TODO: print(engine.narrative)\n"
            "\n"
            "# TODO: print('\\n=== Model Report ===')\n"
            "# TODO: mr = engine.model_report\n"
            "# TODO: print(f\"Target: {mr['target']}\")\n"
            "# TODO: print(f\"CV R\\u00b2: {mr['cv_r2']['mean']:.4f} \\u00b1 {mr['cv_r2']['std']:.4f}\")\n"
            "# TODO: print(f\"Test R\\u00b2: {mr['test_r2']:.4f}   RMSE: {mr['test_rmse']:.2f}\")\n"
            "# TODO: top = sorted(mr['coefficients'].items(), key=lambda kv: abs(kv[1]), reverse=True)[0]\n"
            "# TODO: print(f\"Strongest predictor: {top[0]} (coef={top[1]:.4f})\")"
        ),
        md("## Checks"),
        code(
            "import os\n"
            "\n"
            "\n"
            "def _run_project_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: engine exists and has been run\n"
            "    try:\n"
            "        assert 'engine' in globals(), 'engine not defined'\n"
            "        assert isinstance(engine, InsightEngine), \\\n"
            "            'engine must be an InsightEngine instance'\n"
            "        assert engine.df is not None, 'engine.df is None — call engine.run() first'\n"
            "        passed += 1; print(f'\\u2705 Check 1: InsightEngine created and run()')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: cleaned DataFrame has 300 rows (approx) and no numeric nulls\n"
            "    try:\n"
            "        assert len(engine.df) >= 290, \\\n"
            "            f'expected ~300 rows, got {len(engine.df)}'\n"
            "        num_nulls = engine.df.select_dtypes(include='number').isnull().sum().sum()\n"
            "        assert num_nulls == 0, f'{num_nulls} numeric nulls remain after cleaning'\n"
            "        passed += 1; print(f'\\u2705 Check 2: df has {len(engine.df)} rows, 0 numeric nulls')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: model trained on revenue — test_r2 > 0.5\n"
            "    try:\n"
            "        mr = engine.model_report\n"
            "        assert 'test_r2' in mr, \"model_report missing 'test_r2'\"\n"
            "        assert mr['test_r2'] > 0.5, \\\n"
            "            f\"test_r2={mr['test_r2']} should be > 0.5\"\n"
            "        passed += 1; print(f\"\\u2705 Check 3: test_r2={mr['test_r2']} > 0.5\")\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: narrative is a non-empty string\n"
            "    try:\n"
            "        assert isinstance(engine.narrative, str) and len(engine.narrative) > 20\n"
            "        passed += 1; print(f'\\u2705 Check 4: narrative ({len(engine.narrative)} chars)')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: insight_report.png saved\n"
            "    try:\n"
            "        assert os.path.exists('insight_report.png'), \\\n"
            "            'insight_report.png not found — call engine.save_chart()'\n"
            "        assert os.path.getsize('insight_report.png') > 1000\n"
            "        passed += 1; print(f'\\u2705 Check 5: insight_report.png saved')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 5: {e}')\n"
            "\n"
            "    if passed == total:\n"
            "        print('\\U0001f389 Project complete! Section 3 done.')\n"
            "    print(f'\\nScore: {passed}/{total}')\n"
            "\n"
            "\n"
            "_run_project_checks()"
        ),
    ]


# ---------------------------------------------------------------------------
# Solution notebook
# ---------------------------------------------------------------------------

def solution_nb():
    global _cid; _cid = 600
    all_code = ALL_IMPLS + "\n\n\n" + INSIGHT_ENGINE_IMPL
    return [
        md(
            "# Day 050 Solution — Capstone: Insight Engine\n\n"
            "Section 3 capstone. Demonstrates the full pipeline:\n"
            "load → clean → EDA → model (CV + evaluation) → AI narration → dashboard PNG."
        ),
        code(
            "import matplotlib\n"
            "matplotlib.use('Agg')\n"
            "import matplotlib.pyplot as plt\n"
            "import os\n"
        ),
        code(all_code),
        md("## Step 1 — Run the Full Pipeline"),
        code(
            "df_raw = make_sample_data(300)\n"
            "print('Raw data shape:', df_raw.shape)\n"
            "print('Null counts:\\n', df_raw.isnull().sum())\n"
            "print(df_raw.head(3))"
        ),
        code(
            "engine = InsightEngine(title='Retail Sales 2023')\n"
            "result = engine.run(df_raw, target_col='revenue')\n"
            "\n"
            "print('Cleaned shape:', engine.df.shape)\n"
            "print('Numeric nulls:', engine.df.select_dtypes(include='number').isnull().sum().sum())"
        ),
        md("## Step 2 — EDA Summary"),
        code(
            "eda = engine.eda\n"
            "print(f\"Shape: {eda['shape']}\")\n"
            "print(f\"Numeric columns: {eda['numeric_cols']}\")\n"
            "print(f\"Categorical columns: {eda['cat_cols']}\")\n"
            "print('\\nNumeric summary:')\n"
            "for col, stats in eda['numeric_summary'].items():\n"
            "    print(f\"  {col}: mean={stats['mean']:.2f}, std={stats['std']:.2f}, \"\n"
            "          f\"min={stats['min']:.2f}, max={stats['max']:.2f}\")\n"
            "print('\\nCorrelations with revenue:')\n"
            "for col, corrs in eda['correlations'].items():\n"
            "    if 'revenue' in corrs:\n"
            "        print(f\"  {col} ↔ revenue: {corrs['revenue']:.4f}\")"
        ),
        md("## Step 3 — Model Report"),
        code(
            "mr = engine.model_report\n"
            "print(f\"Target:      {mr['target']}\")\n"
            "print(f\"Features:    {mr['features']}\")\n"
            "print(f\"CV R\\u00b2:     {mr['cv_r2']['mean']:.4f} \\u00b1 {mr['cv_r2']['std']:.4f}\")\n"
            "print(f\"Test R\\u00b2:   {mr['test_r2']:.4f}\")\n"
            "print(f\"Test RMSE:   {mr['test_rmse']:.2f}\")\n"
            "print(f\"Test MAE:    {mr['test_mae']:.2f}\")\n"
            "print('\\nCoefficients (scaled):')\n"
            "for col, c in sorted(mr['coefficients'].items(), key=lambda kv: abs(kv[1]), reverse=True):\n"
            "    print(f'  {col}: {c:.4f}')\n"
            "\n"
            "assert mr['test_r2'] > 0.5, f\"R\\u00b2={mr['test_r2']} too low\""
        ),
        md("## Step 4 — AI Narrative"),
        code(
            "print('=== AI Executive Summary ===')\n"
            "print(engine.narrative)\n"
            "\n"
            "assert isinstance(engine.narrative, str) and len(engine.narrative) > 20"
        ),
        md("## Step 5 — Dashboard Chart"),
        code(
            "out = engine.save_chart('insight_report.png')\n"
            "print(f'Dashboard saved: {out}')\n"
            "print(f'File size: {os.path.getsize(out)} bytes')\n"
            "\n"
            "assert os.path.exists('insight_report.png')\n"
            "assert os.path.getsize('insight_report.png') > 1000\n"
            "\n"
            "print('\\nInsight Engine complete! \\U0001f389')\n"
            "print('Section 3 \\u2014 Data & Analysis \\u2014 DONE.')"
        ),
    ]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Generating Day 050 notebooks...")
    ex_dir   = DAY_DIR / "exercises"
    proj_dir = DAY_DIR / "project"
    sol_dir  = proj_dir / "solution"
    for d in (ex_dir, proj_dir, sol_dir):
        d.mkdir(parents=True, exist_ok=True)

    write_nb(ex_dir   / "exercise_01.ipynb", ex01())
    write_nb(ex_dir   / "exercise_02.ipynb", ex02())
    write_nb(ex_dir   / "exercise_03.ipynb", ex03())
    write_nb(ex_dir   / "exercise_04.ipynb", ex04())
    write_nb(ex_dir   / "exercise_05.ipynb", ex05())
    write_nb(proj_dir / "project.ipynb",     project_nb())
    write_nb(sol_dir  / "solution.ipynb",    solution_nb())
    print("Done.")


if __name__ == "__main__":
    main()
