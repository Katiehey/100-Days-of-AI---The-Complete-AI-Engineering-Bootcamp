#!/usr/bin/env python3
"""Generate all Day 048 notebooks: exercises 1-5, project, solution."""
import json
from pathlib import Path

ROOT    = Path(__file__).resolve().parent.parent
DAY_DIR = ROOT / "03_data_analysis" / "day_048"

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

MAKE_REGRESSION_DATA = """\
import pandas as pd
import numpy as np
import warnings
from sklearn.model_selection import train_test_split
warnings.filterwarnings('ignore')


def make_regression_data(n: int = 200, seed: int = 42) -> pd.DataFrame:
    \"\"\"Synthetic housing dataset with one categorical column (neighborhood).\"\"\"
    rng = np.random.default_rng(seed)
    area         = rng.uniform(500, 3000, n).round(0)
    bedrooms     = rng.integers(1, 6, n)
    age          = rng.uniform(0, 50, n).round(1)
    neighborhood = rng.choice(['downtown', 'suburb', 'rural'], n)
    price = (
        area * 150
        + bedrooms * 10_000
        - age * 1_000
        + np.where(neighborhood == 'downtown', 50_000, 0)
        + np.where(neighborhood == 'suburb',   20_000, 0)
        + rng.standard_normal(n) * 10_000
    ).round(-2)
    return pd.DataFrame({
        'area':         area.astype(int),
        'bedrooms':     bedrooms,
        'age':          age,
        'neighborhood': neighborhood,
        'price':        price.astype(int),
    })"""

# ---------------------------------------------------------------------------
# Implementations
# ---------------------------------------------------------------------------

SPLIT_IMPL = """\
def prepare_features(df: pd.DataFrame, target_col: str,
                     numeric_only: bool = True):
    \"\"\"Return (X, y) separating features from target.\"\"\"
    X = df.drop(columns=[target_col])
    if numeric_only:
        X = X.select_dtypes(include='number')
    y = df[target_col]
    return X, y


def split_data(X: pd.DataFrame, y: pd.Series,
               test_size: float = 0.2,
               random_state: int = 42) -> dict:
    \"\"\"Wrap train_test_split, return a result dict.\"\"\"
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state
    )
    return {
        'X_train':    X_train,
        'X_test':     X_test,
        'y_train':    y_train,
        'y_test':     y_test,
        'n_train':    len(X_train),
        'n_test':     len(X_test),
        'n_features': X_train.shape[1],
    }"""

ENCODE_IMPL = """\
def encode_categoricals(df: pd.DataFrame,
                         cat_cols: list | None = None,
                         drop_first: bool = False) -> pd.DataFrame:
    \"\"\"One-hot encode categorical columns with pd.get_dummies.\"\"\"
    if cat_cols is None:
        cat_cols = df.select_dtypes(include='object').columns.tolist()
    if not cat_cols:
        return df.copy()
    encoded = pd.get_dummies(df, columns=cat_cols, drop_first=drop_first)
    # pandas 2.x returns bool dtype for dummy columns; convert to int
    bool_cols = encoded.select_dtypes(include='bool').columns.tolist()
    for c in bool_cols:
        encoded[c] = encoded[c].astype(int)
    return encoded"""

SCALE_IMPL = """\
from sklearn.preprocessing import StandardScaler


def fit_scaler(X_train: pd.DataFrame) -> StandardScaler:
    \"\"\"Fit a StandardScaler on training data only.\"\"\"
    scaler = StandardScaler()
    scaler.fit(X_train)
    return scaler


def scale_features(scaler: StandardScaler,
                   X: pd.DataFrame) -> pd.DataFrame:
    \"\"\"Transform X using a fitted scaler; return DataFrame with same columns.\"\"\"
    scaled = scaler.transform(X)
    return pd.DataFrame(scaled, columns=X.columns, index=X.index)"""

MODEL_IMPL = """\
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score


def train_model(X_train: pd.DataFrame,
                y_train: pd.Series) -> LinearRegression:
    \"\"\"Fit LinearRegression on training data.\"\"\"
    model = LinearRegression()
    model.fit(X_train, y_train)
    return model


def evaluate_model(model: LinearRegression,
                   X_test: pd.DataFrame,
                   y_test: pd.Series) -> dict:
    \"\"\"Return R², RMSE, n_test, and predictions array.\"\"\"
    y_pred = model.predict(X_test)
    r2     = r2_score(y_test, y_pred)
    rmse   = float(np.sqrt(mean_squared_error(y_test, y_pred)))
    return {
        'r2':          round(float(r2), 4),
        'rmse':        round(rmse, 2),
        'n_test':      len(y_test),
        'predictions': y_pred,
    }"""

FEATURE_ENGINEER_IMPL = """\
class FeatureEngineer:
    \"\"\"
    End-to-end preprocessing pipeline: encode → scale → split.

    Usage:
        fe    = FeatureEngineer(target_col='price')
        split = fe.fit_transform(df)
        X_new = fe.transform(new_df)
    \"\"\"

    def __init__(self, target_col: str,
                 cat_cols: list | None = None,
                 scale: bool = True):
        self.target_col   = target_col
        self.cat_cols     = cat_cols
        self.scale        = scale
        self._scaler      = None
        self._feature_cols = None

    def fit_transform(self, df: pd.DataFrame,
                      test_size: float = 0.2,
                      random_state: int = 42) -> dict:
        \"\"\"Encode, scale (fit on train), split. Return split dict.\"\"\"
        encoded             = encode_categoricals(df, cat_cols=self.cat_cols)
        X, y                = prepare_features(encoded, self.target_col,
                                               numeric_only=False)
        self._feature_cols  = X.columns.tolist()
        if self.scale:
            self._scaler = fit_scaler(X)
            X            = scale_features(self._scaler, X)
        return split_data(X, y, test_size=test_size,
                          random_state=random_state)

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        \"\"\"Apply fitted encoding + scaling to new data.\"\"\"
        encoded = encode_categoricals(df, cat_cols=self.cat_cols)
        X       = encoded.reindex(columns=self._feature_cols, fill_value=0)
        if self.scale and self._scaler is not None:
            X = scale_features(self._scaler, X)
        return X"""

# Cumulative provided code stacks
_BEFORE_ENCODE  = "\n\n\n".join([MAKE_REGRESSION_DATA, SPLIT_IMPL])
_BEFORE_SCALE   = "\n\n\n".join([MAKE_REGRESSION_DATA, SPLIT_IMPL, ENCODE_IMPL])
_BEFORE_MODEL   = "\n\n\n".join([MAKE_REGRESSION_DATA, SPLIT_IMPL, ENCODE_IMPL,
                                  SCALE_IMPL])
ALL_IMPLS       = "\n\n\n".join([MAKE_REGRESSION_DATA, SPLIT_IMPL, ENCODE_IMPL,
                                  SCALE_IMPL, MODEL_IMPL])


# ---------------------------------------------------------------------------
# Exercise 01 — prepare_features + split_data
# ---------------------------------------------------------------------------

def ex01():
    global _cid; _cid = 0
    return [
        md(
            "# Day 048 — Exercise 1: prepare_features + split_data\n\n"
            "**What you'll build:** Two functions that start every ML pipeline:\n"
            "- `prepare_features(df, target_col, numeric_only=True) -> (X, y)` — "
            "separate features from the target column\n"
            "- `split_data(X, y, test_size=0.2, random_state=42) -> dict` — "
            "wrap `train_test_split` and return a labelled result dict\n\n"
            "**Why it matters:** The first rule of ML: never let the model see test data "
            "during training. `split_data` enforces that boundary. `prepare_features` "
            "enforces the X/y interface that every sklearn estimator expects — a 2D "
            "feature matrix and a 1D target vector."
        ),
        md("## Provided: Setup + Sample Data"),
        code(MAKE_REGRESSION_DATA),
        md("## Your Implementation"),
        code(
            "def prepare_features(df: pd.DataFrame, target_col: str,\n"
            "                     numeric_only: bool = True):\n"
            '    """\n'
            "    Separate features (X) from the target (y).\n\n"
            "    Args:\n"
            "        df:           input DataFrame\n"
            "        target_col:   name of the column to predict\n"
            "        numeric_only: if True, keep only numeric feature columns\n"
            "    Returns:\n"
            "        (X, y) — feature DataFrame and target Series\n"
            '    """\n'
            "    # TODO: X = df.drop(columns=[target_col])\n"
            "    # TODO: if numeric_only:\n"
            "    #     X = X.select_dtypes(include='number')\n"
            "    # TODO: y = df[target_col]\n"
            "    # TODO: return X, y\n"
            "    pass\n"
            "\n"
            "\n"
            "def split_data(X: pd.DataFrame, y: pd.Series,\n"
            "               test_size: float = 0.2,\n"
            "               random_state: int = 42) -> dict:\n"
            '    """\n'
            "    Split X and y into train and test sets.\n\n"
            "    Returns a dict with keys:\n"
            "        X_train, X_test, y_train, y_test, n_train, n_test, n_features\n"
            '    """\n'
            "    # TODO: X_train, X_test, y_train, y_test = train_test_split(\n"
            "    #     X, y, test_size=test_size, random_state=random_state\n"
            "    # )\n"
            "    # TODO: return {\n"
            "    #     'X_train': X_train, 'X_test': X_test,\n"
            "    #     'y_train': y_train, 'y_test': y_test,\n"
            "    #     'n_train': len(X_train), 'n_test': len(X_test),\n"
            "    #     'n_features': X_train.shape[1],\n"
            "    # }\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    df = make_regression_data(100)\n"
            "\n"
            "    # Check 1: prepare_features defined, returns 2-tuple\n"
            "    try:\n"
            "        assert 'prepare_features' in globals()\n"
            "        result = prepare_features(df, 'price')\n"
            "        assert isinstance(result, tuple) and len(result) == 2, \\\n"
            "            f'expected 2-tuple, got {type(result).__name__}'\n"
            "        passed += 1; print('\\u2705 Check 1: prepare_features returns (X, y) tuple')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: X is DataFrame, y is Series\n"
            "    try:\n"
            "        X, y = prepare_features(df, 'price')\n"
            "        assert isinstance(X, pd.DataFrame), \\\n"
            "            f'X must be DataFrame, got {type(X).__name__}'\n"
            "        assert isinstance(y, pd.Series), \\\n"
            "            f'y must be Series, got {type(y).__name__}'\n"
            "        passed += 1; print(f'\\u2705 Check 2: X is DataFrame ({X.shape}), y is Series (len={len(y)})')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: target_col not in X.columns\n"
            "    try:\n"
            "        assert 'price' not in X.columns, \\\n"
            "            'target column should not appear in X'\n"
            "        passed += 1; print(f'\\u2705 Check 3: target col excluded from X (X cols: {X.columns.tolist()})')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: split_data returns dict with all required keys\n"
            "    try:\n"
            "        assert 'split_data' in globals()\n"
            "        split = split_data(X, y)\n"
            "        assert isinstance(split, dict), \\\n"
            "            f'split_data must return dict, got {type(split).__name__}'\n"
            "        for k in ('X_train', 'X_test', 'y_train', 'y_test',\n"
            "                  'n_train', 'n_test', 'n_features'):\n"
            "            assert k in split, f'missing key: {k!r}'\n"
            "        passed += 1; print(f'\\u2705 Check 4: split_data returns dict with all 7 keys')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 5: n_train + n_test == len(X) — no rows lost\n"
            "    try:\n"
            "        total_rows = split['n_train'] + split['n_test']\n"
            "        assert total_rows == len(X), \\\n"
            "            f'n_train + n_test should be {len(X)}, got {total_rows}'\n"
            "        passed += 1; print(f'\\u2705 Check 5: n_train={split[\"n_train\"]} + n_test={split[\"n_test\"]} = {len(X)} (no rows lost)')\n"
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
            + SPLIT_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 02 — encode_categoricals
# ---------------------------------------------------------------------------

def ex02():
    global _cid; _cid = 100
    return [
        md(
            "# Day 048 — Exercise 2: encode_categoricals\n\n"
            "**What you'll build:** `encode_categoricals(df, cat_cols=None, drop_first=False) "
            "-> pd.DataFrame` — one-hot encode string columns with `pd.get_dummies` and "
            "convert the resulting bool columns to int so sklearn's estimators see numbers.\n\n"
            "**Why it matters:** Most ML models can't handle string data — only numbers. "
            "One-hot encoding converts a column like `neighborhood` with values "
            "`'downtown'`, `'suburb'`, `'rural'` into three binary columns. "
            "`drop_first=True` drops one column to avoid multicollinearity (the dummy "
            "variable trap) when using linear models."
        ),
        md("## Provided: Setup + prepare_features + split_data"),
        code(_BEFORE_ENCODE),
        md("## Your Implementation"),
        code(
            "def encode_categoricals(df: pd.DataFrame,\n"
            "                         cat_cols: list | None = None,\n"
            "                         drop_first: bool = False) -> pd.DataFrame:\n"
            '    """\n'
            "    One-hot encode categorical (object dtype) columns.\n\n"
            "    Args:\n"
            "        df:         input DataFrame\n"
            "        cat_cols:   list of columns to encode; if None, auto-detect\n"
            "                    all columns with dtype 'object'\n"
            "        drop_first: if True, drop one dummy per category (avoids\n"
            "                    multicollinearity in linear models)\n"
            "    Returns:\n"
            "        New DataFrame with cat_cols replaced by integer dummy columns.\n"
            "        Original numeric columns are unchanged.\n"
            '    """\n'
            "    if cat_cols is None:\n"
            "        cat_cols = df.select_dtypes(include='object').columns.tolist()\n"
            "    if not cat_cols:\n"
            "        return df.copy()\n"
            "    # TODO: encoded = pd.get_dummies(df, columns=cat_cols, drop_first=drop_first)\n"
            "    # TODO: # pandas 2.x returns bool dtype for dummies — convert to int\n"
            "    # TODO: bool_cols = encoded.select_dtypes(include='bool').columns.tolist()\n"
            "    # TODO: for c in bool_cols:\n"
            "    #     encoded[c] = encoded[c].astype(int)\n"
            "    # TODO: return encoded\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    df = make_regression_data(100)\n"
            "\n"
            "    # Check 1: defined, returns DataFrame\n"
            "    try:\n"
            "        assert 'encode_categoricals' in globals()\n"
            "        encoded = encode_categoricals(df)\n"
            "        assert isinstance(encoded, pd.DataFrame), \\\n"
            "            f'expected DataFrame, got {type(encoded).__name__}'\n"
            "        passed += 1; print(f'\\u2705 Check 1: encode_categoricals returns DataFrame ({encoded.shape[1]} cols)')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: original cat column removed\n"
            "    try:\n"
            "        assert 'neighborhood' not in encoded.columns, \\\n"
            "            'neighborhood should be gone after encoding'\n"
            "        passed += 1; print('\\u2705 Check 2: original categorical column removed')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: dummy columns created for each category value\n"
            "    try:\n"
            "        dummy_cols = [c for c in encoded.columns if c.startswith('neighborhood_')]\n"
            "        assert len(dummy_cols) == 3, \\\n"
            "            f'expected 3 neighborhood_ columns, got {len(dummy_cols)}: {dummy_cols}'\n"
            "        passed += 1; print(f'\\u2705 Check 3: 3 dummy columns created: {dummy_cols}')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: dummy columns are numeric (int), not bool\n"
            "    try:\n"
            "        for c in [col for col in encoded.columns if col.startswith('neighborhood_')]:\n"
            "            assert encoded[c].dtype != bool, \\\n"
            "                f'{c} should not be bool; convert to int'\n"
            "            assert pd.api.types.is_numeric_dtype(encoded[c]), \\\n"
            "                f'{c} should be numeric'\n"
            "        passed += 1; print('\\u2705 Check 4: dummy columns are numeric (int), not bool')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: drop_first=True produces one fewer column\n"
            "    try:\n"
            "        enc_drop = encode_categoricals(df, drop_first=True)\n"
            "        assert enc_drop.shape[1] < encoded.shape[1], \\\n"
            "            f'drop_first=True should reduce columns ({enc_drop.shape[1]} < {encoded.shape[1]})'\n"
            "        passed += 1; print(f'\\u2705 Check 5: drop_first=True → {enc_drop.shape[1]} cols (vs {encoded.shape[1]})')\n"
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
            + ENCODE_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 03 — fit_scaler + scale_features
# ---------------------------------------------------------------------------

def ex03():
    global _cid; _cid = 200
    return [
        md(
            "# Day 048 — Exercise 3: fit_scaler + scale_features\n\n"
            "**What you'll build:**\n"
            "- `fit_scaler(X_train) -> StandardScaler` — fit a scaler on **training** "
            "data only\n"
            "- `scale_features(scaler, X) -> pd.DataFrame` — apply the fitted scaler, "
            "return a DataFrame preserving column names and index\n\n"
            "**Why it matters:** Features on different scales bias distance-based models "
            "and slow down gradient descent. After scaling, `area` (500–3000) and "
            "`bedrooms` (1–5) both have mean 0 and std 1, so neither dominates. "
            "Critical rule: **fit on training data only**, then apply the same transform "
            "to test data. Fitting on test data leaks information."
        ),
        md("## Provided: Setup + prior functions"),
        code(_BEFORE_SCALE),
        md("## Your Implementation"),
        code(
            "from sklearn.preprocessing import StandardScaler\n"
            "\n"
            "\n"
            "def fit_scaler(X_train: pd.DataFrame) -> StandardScaler:\n"
            '    """\n'
            "    Fit a StandardScaler on training data only.\n"
            "    Returns the fitted scaler (use it later to transform test data).\n"
            '    """\n'
            "    # TODO: scaler = StandardScaler()\n"
            "    # TODO: scaler.fit(X_train)\n"
            "    # TODO: return scaler\n"
            "    pass\n"
            "\n"
            "\n"
            "def scale_features(scaler: StandardScaler,\n"
            "                   X: pd.DataFrame) -> pd.DataFrame:\n"
            '    """\n'
            "    Transform X using a fitted StandardScaler.\n"
            "    Returns a DataFrame with the same column names and index as X.\n"
            '    """\n'
            "    # TODO: scaled = scaler.transform(X)\n"
            "    # TODO: return pd.DataFrame(scaled, columns=X.columns, index=X.index)\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    df      = make_regression_data(100)\n"
            "    encoded = encode_categoricals(df)\n"
            "    X, y    = prepare_features(encoded, 'price', numeric_only=False)\n"
            "    split   = split_data(X, y)\n"
            "    X_train = split['X_train']\n"
            "    X_test  = split['X_test']\n"
            "\n"
            "    # Check 1: fit_scaler returns StandardScaler\n"
            "    try:\n"
            "        assert 'fit_scaler' in globals()\n"
            "        scaler = fit_scaler(X_train)\n"
            "        assert isinstance(scaler, StandardScaler), \\\n"
            "            f'expected StandardScaler, got {type(scaler).__name__}'\n"
            "        assert hasattr(scaler, 'mean_'), 'scaler must be fitted (has mean_ attribute)'\n"
            "        passed += 1; print('\\u2705 Check 1: fit_scaler returns fitted StandardScaler')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: scale_features returns DataFrame with same columns\n"
            "    try:\n"
            "        assert 'scale_features' in globals()\n"
            "        X_scaled = scale_features(scaler, X_train)\n"
            "        assert isinstance(X_scaled, pd.DataFrame), \\\n"
            "            f'expected DataFrame, got {type(X_scaled).__name__}'\n"
            "        assert list(X_scaled.columns) == list(X_train.columns), \\\n"
            "            'column names must be preserved after scaling'\n"
            "        passed += 1; print(f'\\u2705 Check 2: scale_features returns DataFrame with {len(X_scaled.columns)} cols')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 3: training features have mean ≈ 0 after scaling\n"
            "    try:\n"
            "        col_means = X_scaled.mean()\n"
            "        max_mean  = col_means.abs().max()\n"
            "        assert max_mean < 1e-9, \\\n"
            "            f'scaled train means should be ≈0; max abs mean = {max_mean:.2e}'\n"
            "        passed += 1; print(f'\\u2705 Check 3: scaled training means ≈ 0 (max abs = {max_mean:.2e})')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: training features have std ≈ 1 after scaling\n"
            "    try:\n"
            "        col_stds = X_scaled.std(ddof=0)  # population std matches scaler\n"
            "        max_err  = (col_stds - 1).abs().max()\n"
            "        assert max_err < 1e-9, \\\n"
            "            f'scaled train stds should be ≈1; max abs error = {max_err:.2e}'\n"
            "        passed += 1; print(f'\\u2705 Check 4: scaled training stds ≈ 1 (max err = {max_err:.2e})')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: test set can be transformed with the same scaler\n"
            "    try:\n"
            "        X_test_scaled = scale_features(scaler, X_test)\n"
            "        assert list(X_test_scaled.columns) == list(X_train.columns), \\\n"
            "            'test scaled columns must match train columns'\n"
            "        assert X_test_scaled.shape == X_test.shape, \\\n"
            "            f'shape mismatch: {X_test_scaled.shape} vs {X_test.shape}'\n"
            "        passed += 1; print(f'\\u2705 Check 5: test set transformed, shape={X_test_scaled.shape}')\n"
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
            + SCALE_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 04 — train_model + evaluate_model
# ---------------------------------------------------------------------------

def ex04():
    global _cid; _cid = 300
    return [
        md(
            "# Day 048 — Exercise 4: train_model + evaluate_model\n\n"
            "**What you'll build:**\n"
            "- `train_model(X_train, y_train) -> LinearRegression` — fit a linear model\n"
            "- `evaluate_model(model, X_test, y_test) -> dict` — compute R² and RMSE\n\n"
            "**Why it matters:** R² (coefficient of determination) tells you what fraction "
            "of variance in y the model explains — 1.0 is perfect, 0.0 is as good as "
            "predicting the mean, negative means worse than the mean. RMSE (root mean "
            "squared error) tells you the typical prediction error in the same units as y, "
            "so '$9,500 RMSE on house prices' is immediately interpretable."
        ),
        md("## Provided: Setup + all prior functions"),
        code(_BEFORE_MODEL),
        md("## Your Implementation"),
        code(
            "from sklearn.linear_model import LinearRegression\n"
            "from sklearn.metrics import mean_squared_error, r2_score\n"
            "\n"
            "\n"
            "def train_model(X_train: pd.DataFrame,\n"
            "                y_train: pd.Series) -> LinearRegression:\n"
            '    """\n'
            "    Fit a LinearRegression model on training data.\n"
            "    Returns the fitted model.\n"
            '    """\n'
            "    # TODO: model = LinearRegression()\n"
            "    # TODO: model.fit(X_train, y_train)\n"
            "    # TODO: return model\n"
            "    pass\n"
            "\n"
            "\n"
            "def evaluate_model(model: LinearRegression,\n"
            "                   X_test: pd.DataFrame,\n"
            "                   y_test: pd.Series) -> dict:\n"
            '    """\n'
            "    Evaluate a fitted model on test data.\n\n"
            "    Returns dict with keys:\n"
            "        r2          — coefficient of determination (higher = better)\n"
            "        rmse        — root mean squared error (lower = better)\n"
            "        n_test      — number of test samples\n"
            "        predictions — numpy array of predicted values\n"
            '    """\n'
            "    # TODO: y_pred = model.predict(X_test)\n"
            "    # TODO: r2   = r2_score(y_test, y_pred)\n"
            "    # TODO: rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))\n"
            "    # TODO: return {\n"
            "    #     'r2':          round(float(r2), 4),\n"
            "    #     'rmse':        round(rmse, 2),\n"
            "    #     'n_test':      len(y_test),\n"
            "    #     'predictions': y_pred,\n"
            "    # }\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Use clean synthetic data for deterministic R²\n"
            "    rng    = np.random.default_rng(0)\n"
            "    n      = 200\n"
            "    X_clean = pd.DataFrame({\n"
            "        'a': rng.uniform(0, 10, n),\n"
            "        'b': rng.uniform(0, 5,  n),\n"
            "    })\n"
            "    y_clean = pd.Series(5 * X_clean['a'] + 2 * X_clean['b']\n"
            "                        + rng.standard_normal(n) * 0.01)\n"
            "    split   = split_data(X_clean, y_clean, test_size=0.2, random_state=42)\n"
            "\n"
            "    # Check 1: train_model returns fitted LinearRegression\n"
            "    try:\n"
            "        assert 'train_model' in globals()\n"
            "        model = train_model(split['X_train'], split['y_train'])\n"
            "        assert isinstance(model, LinearRegression), \\\n"
            "            f'expected LinearRegression, got {type(model).__name__}'\n"
            "        assert hasattr(model, 'coef_'), 'model must be fitted (has coef_ attribute)'\n"
            "        passed += 1; print('\\u2705 Check 1: train_model returns fitted LinearRegression')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: coef_ length == n_features\n"
            "    try:\n"
            "        assert len(model.coef_) == split['n_features'], \\\n"
            "            f'coef_ length {len(model.coef_)} != n_features {split[\"n_features\"]}'\n"
            "        passed += 1; print(f'\\u2705 Check 2: coef_ has {len(model.coef_)} entries (one per feature)')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: evaluate_model returns dict with required keys\n"
            "    try:\n"
            "        assert 'evaluate_model' in globals()\n"
            "        result = evaluate_model(model, split['X_test'], split['y_test'])\n"
            "        assert isinstance(result, dict), \\\n"
            "            f'expected dict, got {type(result).__name__}'\n"
            "        for k in ('r2', 'rmse', 'n_test', 'predictions'):\n"
            "            assert k in result, f'missing key: {k!r}'\n"
            "        passed += 1; print('\\u2705 Check 3: evaluate_model returns dict with all 4 keys')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 4: R² > 0.99 on clean linear data\n"
            "    try:\n"
            "        assert result['r2'] > 0.99, \\\n"
            "            f'R² on near-perfect linear data should be > 0.99, got {result[\"r2\"]}'\n"
            "        passed += 1; print(f'\\u2705 Check 4: R²={result[\"r2\"]} > 0.99 on clean data')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: RMSE > 0 (not identically perfect)\n"
            "    try:\n"
            "        assert result['rmse'] > 0, \\\n"
            "            f'rmse should be > 0, got {result[\"rmse\"]}'\n"
            "        passed += 1; print(f'\\u2705 Check 5: rmse={result[\"rmse\"]:.4f} > 0')\n"
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
# Exercise 05 — FeatureEngineer class
# ---------------------------------------------------------------------------

def ex05():
    global _cid; _cid = 400
    return [
        md(
            "# Day 048 — Exercise 5: FeatureEngineer Class\n\n"
            "**What you'll build:** The `FeatureEngineer` class — a preprocessing "
            "pipeline that composes `encode_categoricals`, `prepare_features`, "
            "`fit_scaler`, `scale_features`, and `split_data` behind two methods:\n"
            "- `fit_transform(df, test_size=0.2, random_state=42) -> dict` — encode, "
            "scale (fit on train), split\n"
            "- `transform(df) -> pd.DataFrame` — apply fitted encoding and scaling to "
            "new data using the same scaler learned during `fit_transform`\n\n"
            "**Why it matters:** The same preprocessing pipeline must be applied "
            "identically to training and production data. By storing the scaler and "
            "feature column order, `FeatureEngineer` guarantees that new data is "
            "transformed the same way as the training data — no leakage, no column "
            "mismatch."
        ),
        md("## Provided: All Helper Functions"),
        code(ALL_IMPLS),
        md("## Your Implementation"),
        code(
            "class FeatureEngineer:\n"
            '    """\n'
            "    End-to-end preprocessing pipeline: encode → scale → split.\n\n"
            "    Usage:\n"
            "        fe    = FeatureEngineer(target_col='price')\n"
            "        split = fe.fit_transform(df)\n"
            "        X_new = fe.transform(new_df)\n"
            '    """\n'
            "\n"
            "    def __init__(self, target_col: str,\n"
            "                 cat_cols: list | None = None,\n"
            "                 scale: bool = True):\n"
            "        # TODO: self.target_col = target_col\n"
            "        # TODO: self.cat_cols   = cat_cols\n"
            "        # TODO: self.scale      = scale\n"
            "        # TODO: self._scaler         = None\n"
            "        # TODO: self._feature_cols   = None\n"
            "        pass\n"
            "\n"
            "    def fit_transform(self, df: pd.DataFrame,\n"
            "                      test_size: float = 0.2,\n"
            "                      random_state: int = 42) -> dict:\n"
            '        """\n'
            "        Encode categoricals, fit scaler on train, split.\n"
            "        Stores feature column order and fitted scaler for transform().\n"
            "        Returns the same split dict as split_data().\n"
            '        """\n'
            "        # TODO: encoded = encode_categoricals(df, cat_cols=self.cat_cols)\n"
            "        # TODO: X, y   = prepare_features(encoded, self.target_col, numeric_only=False)\n"
            "        # TODO: self._feature_cols = X.columns.tolist()\n"
            "        # TODO: if self.scale:\n"
            "        #     self._scaler = fit_scaler(X)\n"
            "        #     X = scale_features(self._scaler, X)\n"
            "        # TODO: return split_data(X, y, test_size=test_size, random_state=random_state)\n"
            "        pass\n"
            "\n"
            "    def transform(self, df: pd.DataFrame) -> pd.DataFrame:\n"
            '        """\n'
            "        Apply fitted encoding + scaling to new data.\n"
            "        Uses reindex to handle unseen categories gracefully.\n"
            '        """\n'
            "        # TODO: encoded = encode_categoricals(df, cat_cols=self.cat_cols)\n"
            "        # TODO: X       = encoded.reindex(columns=self._feature_cols, fill_value=0)\n"
            "        # TODO: if self.scale and self._scaler is not None:\n"
            "        #     X = scale_features(self._scaler, X)\n"
            "        # TODO: return X\n"
            "        pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    df = make_regression_data(100)\n"
            "\n"
            "    # Check 1: class defined with fit_transform and transform\n"
            "    try:\n"
            "        assert 'FeatureEngineer' in globals()\n"
            "        for m in ('fit_transform', 'transform'):\n"
            "            assert hasattr(FeatureEngineer, m), f'missing method: {m}'\n"
            "        passed += 1; print('\\u2705 Check 1: FeatureEngineer has fit_transform and transform')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: fit_transform returns dict with split keys\n"
            "    try:\n"
            "        fe    = FeatureEngineer(target_col='price')\n"
            "        split = fe.fit_transform(df)\n"
            "        assert isinstance(split, dict), \\\n"
            "            f'fit_transform must return dict, got {type(split).__name__}'\n"
            "        for k in ('X_train', 'X_test', 'y_train', 'y_test'):\n"
            "            assert k in split, f'missing key: {k!r}'\n"
            "        passed += 1; print(f'\\u2705 Check 2: fit_transform returns split dict with X_train, X_test, y_train, y_test')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 3: n_train + n_test == len(df)\n"
            "    try:\n"
            "        total_rows = split['n_train'] + split['n_test']\n"
            "        assert total_rows == len(df), \\\n"
            "            f'n_train + n_test = {total_rows}, expected {len(df)}'\n"
            "        passed += 1; print(f'\\u2705 Check 3: n_train={split[\"n_train\"]} + n_test={split[\"n_test\"]} = {len(df)}')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: target_col not in X_train columns\n"
            "    try:\n"
            "        assert 'price' not in split['X_train'].columns, \\\n"
            "            'price should not appear in X_train'\n"
            "        passed += 1; print(f'\\u2705 Check 4: target col excluded from X_train')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: transform returns DataFrame with same columns as X_train\n"
            "    try:\n"
            "        new_df  = make_regression_data(10, seed=99)\n"
            "        X_new   = fe.transform(new_df.drop(columns=['price']))\n"
            "        assert isinstance(X_new, pd.DataFrame), \\\n"
            "            f'transform must return DataFrame, got {type(X_new).__name__}'\n"
            "        assert list(X_new.columns) == list(split['X_train'].columns), \\\n"
            "            'transform output columns must match X_train columns'\n"
            "        passed += 1; print(f'\\u2705 Check 5: transform returns {X_new.shape} matching X_train columns')\n"
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
            + FEATURE_ENGINEER_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Project notebook
# ---------------------------------------------------------------------------

def project_nb():
    global _cid; _cid = 500
    all_code = ALL_IMPLS + "\n\n\n" + FEATURE_ENGINEER_IMPL
    return [
        md(
            "# Day 048 Project: Predictive Model\n\n"
            "## What You're Building\n\n"
            "A full ML pipeline — from raw housing data to a trained, evaluated "
            "LinearRegression model with a saved visualisation.\n\n"
            "## Project Requirements\n\n"
            "1. Generate the housing dataset with `make_regression_data(200)`\n"
            "2. Use `FeatureEngineer(target_col='price').fit_transform(df)` to preprocess\n"
            "3. Train a model with `train_model()` and evaluate with `evaluate_model()`\n"
            "4. Store results as `r2` and `rmse` variables (floats)\n"
            "5. Build a coefficient table: which features matter most?\n"
            "6. Save a scatter plot of actual vs predicted prices to `predictive_model.png`\n"
            "7. Run `_run_project_checks()` to verify\n\n"
            "The deliverable: a saved chart + printed evaluation metrics."
        ),
        md("## Provided: All Implementations"),
        code(all_code),
        md("## Your Pipeline"),
        code(
            "import matplotlib\n"
            "matplotlib.use('Agg')\n"
            "import matplotlib.pyplot as plt\n"
            "\n"
            "df = make_regression_data(200)\n"
            "\n"
            "# TODO: fe    = FeatureEngineer(target_col='price')\n"
            "# TODO: split = fe.fit_transform(df)\n"
            "\n"
            "# TODO: model  = train_model(split['X_train'], split['y_train'])\n"
            "# TODO: result = evaluate_model(model, split['X_test'], split['y_test'])\n"
            "\n"
            "# TODO: r2   = result['r2']\n"
            "# TODO: rmse = result['rmse']\n"
            "# TODO: print(f'R\\u00b2 = {r2:.4f}')\n"
            "# TODO: print(f'RMSE = ${rmse:,.2f}')\n"
            "\n"
            "# TODO: # Feature coefficients\n"
            "# TODO: coef_df = pd.DataFrame({\n"
            "#     'feature': split['X_train'].columns.tolist(),\n"
            "#     'coefficient': model.coef_,\n"
            "# }).sort_values('coefficient', key=abs, ascending=False)\n"
            "# TODO: print(coef_df.to_string(index=False))\n"
            "\n"
            "# TODO: # Save scatter: actual vs predicted\n"
            "# TODO: fig, ax = plt.subplots(figsize=(7, 5))\n"
            "# TODO: ax.scatter(split['y_test'], result['predictions'], alpha=0.7)\n"
            "# TODO: lo = min(split['y_test'].min(), result['predictions'].min())\n"
            "# TODO: hi = max(split['y_test'].max(), result['predictions'].max())\n"
            "# TODO: ax.plot([lo, hi], [lo, hi], 'r--', label='perfect fit')\n"
            "# TODO: ax.set_xlabel('Actual Price ($)')\n"
            "# TODO: ax.set_ylabel('Predicted Price ($)')\n"
            "# TODO: ax.set_title(f'Actual vs Predicted  R\\u00b2={r2:.3f}  RMSE=${rmse:,.0f}')\n"
            "# TODO: ax.legend()\n"
            "# TODO: fig.savefig('predictive_model.png', bbox_inches='tight', dpi=100)\n"
            "# TODO: plt.close('all')\n"
            "# TODO: print('Chart saved: predictive_model.png')"
        ),
        md("## Checks"),
        code(
            "import os\n"
            "\n"
            "def _run_project_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: r2 defined\n"
            "    try:\n"
            "        assert 'r2' in globals(), 'r2 not defined — run evaluate_model'\n"
            "        assert isinstance(r2, (int, float)), f'r2 must be numeric, got {type(r2).__name__}'\n"
            "        passed += 1; print(f'\\u2705 Check 1: r2 = {r2:.4f}')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: r2 > 0.9 on housing data\n"
            "    try:\n"
            "        assert r2 > 0.9, f'R\\u00b2 should be > 0.9 on housing data, got {r2:.4f}'\n"
            "        passed += 1; print(f'\\u2705 Check 2: R\\u00b2={r2:.4f} > 0.90')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: rmse defined and positive\n"
            "    try:\n"
            "        assert 'rmse' in globals(), 'rmse not defined — run evaluate_model'\n"
            "        assert isinstance(rmse, (int, float)) and rmse > 0, \\\n"
            "            f'rmse must be a positive number, got {rmse}'\n"
            "        passed += 1; print(f'\\u2705 Check 3: rmse = ${rmse:,.2f}')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: coef_df defined\n"
            "    try:\n"
            "        assert 'coef_df' in globals(), 'coef_df not defined — build coefficient table'\n"
            "        assert isinstance(coef_df, pd.DataFrame)\n"
            "        assert 'feature' in coef_df.columns and 'coefficient' in coef_df.columns\n"
            "        passed += 1; print(f'\\u2705 Check 4: coef_df with {len(coef_df)} features')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: chart saved\n"
            "    try:\n"
            "        assert os.path.exists('predictive_model.png'), \\\n"
            "            'predictive_model.png not found — save with fig.savefig()'\n"
            "        assert os.path.getsize('predictive_model.png') > 1000, \\\n"
            "            'predictive_model.png looks empty'\n"
            "        passed += 1; print('\\u2705 Check 5: predictive_model.png saved')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 5: {e}')\n"
            "\n"
            "    if passed == total:\n"
            "        print('\\U0001f389 Project complete!')\n"
            "    print(f'\\nScore: {passed}/{total}')\n"
            "\n"
            "\n"
            "_run_project_checks()"
        ),
        md(
            "## Bonus Challenges\n\n"
            "- Try `drop_first=True` in the FeatureEngineer and see if R² changes\n"
            "- Try `scale=False` — does scaling affect LinearRegression accuracy?\n"
            "- Add a new synthetic feature: `area_per_bedroom = area / bedrooms` before "
            "calling fit_transform\n"
            "- Use `ollama.chat` (Day 40 pattern) to narrate the model performance: "
            "pass R², RMSE, and the top 3 features by coefficient into a prompt\n"
            "- Replace LinearRegression with "
            "`sklearn.tree.DecisionTreeRegressor(max_depth=5)` — same interface, does R² improve?"
        ),
    ]


# ---------------------------------------------------------------------------
# Solution notebook
# ---------------------------------------------------------------------------

def solution_nb():
    global _cid; _cid = 600
    all_code = ALL_IMPLS + "\n\n\n" + FEATURE_ENGINEER_IMPL
    return [
        md(
            "# Day 048 Solution — Feature Engineering & Intro ML\n\n"
            "Demonstrates: one-hot encoding, StandardScaler (fit on train only), "
            "LinearRegression, R² + RMSE, feature coefficient analysis, "
            "and a saved actual-vs-predicted scatter plot."
        ),
        code(
            "import matplotlib\n"
            "matplotlib.use('Agg')\n"
            "import matplotlib.pyplot as plt\n"
            "import os\n"
        ),
        code(all_code),
        md("## Step 1 — Dataset"),
        code(
            "df = make_regression_data(200)\n"
            "print('Shape:', df.shape)\n"
            "print('Columns:', df.columns.tolist())\n"
            "print(df.head())\n"
            "print('\\nprice stats:')\n"
            "print(df['price'].describe().round(0))"
        ),
        md("## Step 2 — Encode + Scale + Split"),
        code(
            "fe    = FeatureEngineer(target_col='price')\n"
            "split = fe.fit_transform(df)\n"
            "\n"
            "print(f'Train: {split[\"n_train\"]} rows  Test: {split[\"n_test\"]} rows')\n"
            "print(f'Features ({split[\"n_features\"]}): {split[\"X_train\"].columns.tolist()}')\n"
            "print(f'\\nX_train stats (scaled):')\n"
            "print(split['X_train'].describe().round(4))\n"
            "\n"
            "assert split['n_train'] + split['n_test'] == len(df)\n"
            "assert 'price' not in split['X_train'].columns"
        ),
        md("## Step 3 — Train"),
        code(
            "model = train_model(split['X_train'], split['y_train'])\n"
            "print('Model trained.')\n"
            "print('Intercept:', round(model.intercept_, 2))\n"
            "\n"
            "assert hasattr(model, 'coef_')\n"
            "assert len(model.coef_) == split['n_features']"
        ),
        md("## Step 4 — Evaluate"),
        code(
            "result = evaluate_model(model, split['X_test'], split['y_test'])\n"
            "\n"
            "r2   = result['r2']\n"
            "rmse = result['rmse']\n"
            "print(f'R\\u00b2  = {r2:.4f}')\n"
            "print(f'RMSE = ${rmse:,.2f}')\n"
            "print(f'Test samples: {result[\"n_test\"]}')\n"
            "\n"
            "assert r2 > 0.9, f'expected R\\u00b2 > 0.9, got {r2}'"
        ),
        md("## Step 5 — Feature Importance"),
        code(
            "coef_df = pd.DataFrame({\n"
            "    'feature':     split['X_train'].columns.tolist(),\n"
            "    'coefficient': model.coef_,\n"
            "}).sort_values('coefficient', key=abs, ascending=False)\n"
            "\n"
            "print('Feature Coefficients (scaled units):')\n"
            "print(coef_df.to_string(index=False))\n"
            "print('\\nLargest positive driver:', coef_df.iloc[0]['feature'])"
        ),
        md("## Step 6 — Save Visualisation"),
        code(
            "fig, axes = plt.subplots(1, 2, figsize=(13, 5))\n"
            "\n"
            "# Panel 1: actual vs predicted scatter\n"
            "lo = min(float(split['y_test'].min()), float(result['predictions'].min()))\n"
            "hi = max(float(split['y_test'].max()), float(result['predictions'].max()))\n"
            "axes[0].scatter(split['y_test'], result['predictions'],\n"
            "                alpha=0.65, edgecolors='white', linewidths=0.3)\n"
            "axes[0].plot([lo, hi], [lo, hi], 'r--', linewidth=1.5, label='perfect fit')\n"
            "axes[0].set_xlabel('Actual Price ($)')\n"
            "axes[0].set_ylabel('Predicted Price ($)')\n"
            "axes[0].set_title(f'Actual vs Predicted  R\\u00b2={r2:.3f}  RMSE=${rmse:,.0f}')\n"
            "axes[0].legend()\n"
            "\n"
            "# Panel 2: feature coefficients bar chart\n"
            "colors = ['steelblue' if c > 0 else 'tomato' for c in coef_df['coefficient']]\n"
            "axes[1].barh(coef_df['feature'], coef_df['coefficient'], color=colors)\n"
            "axes[1].axvline(0, color='black', linewidth=0.8)\n"
            "axes[1].set_xlabel('Coefficient (std-unit impact on price)')\n"
            "axes[1].set_title('Feature Coefficients')\n"
            "\n"
            "plt.tight_layout()\n"
            "fig.savefig('predictive_model.png', bbox_inches='tight', dpi=100)\n"
            "plt.close('all')\n"
            "print('Chart saved: predictive_model.png')\n"
            "\n"
            "assert os.path.exists('predictive_model.png')\n"
            "assert os.path.getsize('predictive_model.png') > 1000\n"
            "\n"
            "print('\\nFeature Engineering & Intro ML complete!')"
        ),
    ]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Generating Day 048 notebooks...")
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
