#!/usr/bin/env python3
"""Generate all Day 049 notebooks: exercises 1-5, project, solution."""
import json
from pathlib import Path

ROOT    = Path(__file__).resolve().parent.parent
DAY_DIR = ROOT / "03_data_analysis" / "day_049"

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
import pandas as pd
import numpy as np
import warnings
from sklearn.model_selection import train_test_split, cross_val_score, KFold
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.tree import DecisionTreeRegressor
from sklearn.metrics import (r2_score, mean_squared_error, mean_absolute_error,
                              accuracy_score, precision_score, recall_score,
                              f1_score, confusion_matrix, classification_report)
from sklearn.preprocessing import StandardScaler
warnings.filterwarnings('ignore')


def make_regression_data(n: int = 200, seed: int = 42) -> pd.DataFrame:
    \"\"\"Numeric-only housing dataset (area, bedrooms, age → price).\"\"\"
    rng = np.random.default_rng(seed)
    area     = rng.uniform(500, 3000, n).round(0)
    bedrooms = rng.integers(1, 6, n)
    age      = rng.uniform(0, 50, n).round(1)
    price    = (area * 150 + bedrooms * 10_000 - age * 1_000
                + rng.standard_normal(n) * 10_000).round(-2)
    return pd.DataFrame({'area': area.astype(int), 'bedrooms': bedrooms,
                         'age': age, 'price': price.astype(int)})


def make_classification_data(n: int = 200, seed: int = 42) -> pd.DataFrame:
    \"\"\"Student exam dataset: hours_studied + hours_sleep → passed (0/1).\"\"\"
    rng          = np.random.default_rng(seed)
    hours_studied = rng.uniform(0, 10, n).round(1)
    hours_sleep   = rng.uniform(4, 10, n).round(1)
    noise         = rng.standard_normal(n)
    score         = 1.5 * hours_studied + 0.5 * hours_sleep + noise
    passed        = (score > 9.0).astype(int)
    return pd.DataFrame({'hours_studied': hours_studied,
                         'hours_sleep':   hours_sleep,
                         'passed':        passed})"""

# ---------------------------------------------------------------------------
# Implementations
# ---------------------------------------------------------------------------

CROSS_VAL_IMPL = """\
def cross_validate_model(model, X: pd.DataFrame, y: pd.Series,
                          cv: int = 5,
                          scoring: str = 'r2') -> dict:
    \"\"\"K-fold cross-validation returning per-fold scores and summary stats.\"\"\"
    kf     = KFold(n_splits=cv, shuffle=True, random_state=42)
    scores = cross_val_score(model, X, y, cv=kf, scoring=scoring)
    return {
        'scores':   scores,
        'mean':     round(float(scores.mean()), 4),
        'std':      round(float(scores.std()),  4),
        'min':      round(float(scores.min()),  4),
        'max':      round(float(scores.max()),  4),
        'cv_folds': cv,
        'scoring':  scoring,
    }"""

OVERFITTING_IMPL = """\
def overfitting_report(X: pd.DataFrame, y: pd.Series,
                        max_depths=range(1, 11),
                        test_size: float = 0.2,
                        random_state: int = 42) -> pd.DataFrame:
    \"\"\"Train DecisionTreeRegressors at each depth; return train vs test R² table.\"\"\"
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state
    )
    records = []
    for depth in max_depths:
        m = DecisionTreeRegressor(max_depth=depth, random_state=42)
        m.fit(X_train, y_train)
        tr_r2 = float(r2_score(y_train, m.predict(X_train)))
        te_r2 = float(r2_score(y_test,  m.predict(X_test)))
        gap   = round(tr_r2 - te_r2, 4)
        records.append({
            'max_depth': depth,
            'train_r2':  round(tr_r2, 4),
            'test_r2':   round(te_r2, 4),
            'gap':       gap,
            'overfit':   bool(gap > 0.1),
        })
    return pd.DataFrame(records)"""

CLASSIFIER_IMPL = """\
def train_classifier(X_train: pd.DataFrame,
                     y_train: pd.Series,
                     max_iter: int = 1000) -> LogisticRegression:
    \"\"\"Fit LogisticRegression and return the fitted model.\"\"\"
    model = LogisticRegression(random_state=42, max_iter=max_iter)
    model.fit(X_train, y_train)
    return model"""

METRICS_IMPL = """\
def classification_metrics(model, X_test: pd.DataFrame,
                            y_test: pd.Series) -> dict:
    \"\"\"Full classification evaluation: accuracy, precision, recall, F1, matrix, report.\"\"\"
    y_pred = model.predict(X_test)
    return {
        'accuracy':         round(float(accuracy_score(y_test, y_pred)), 4),
        'precision':        round(float(precision_score(y_test, y_pred,
                                                         zero_division=0)), 4),
        'recall':           round(float(recall_score(y_test, y_pred,
                                                      zero_division=0)), 4),
        'f1':               round(float(f1_score(y_test, y_pred,
                                                  zero_division=0)), 4),
        'confusion_matrix': confusion_matrix(y_test, y_pred),
        'report':           classification_report(y_test, y_pred),
    }"""

MODEL_EVALUATOR_IMPL = """\
class ModelEvaluator:
    \"\"\"
    Unified evaluator for regression and classification models.

    Usage (regression):
        ev     = ModelEvaluator(task='regression')
        result = ev.evaluate(LinearRegression(), X_train, X_test, y_train, y_test)
        print(ev.summary())

    Usage (classification):
        ev     = ModelEvaluator(task='classification')
        result = ev.evaluate(LogisticRegression(), X_train, X_test, y_train, y_test)
    \"\"\"

    def __init__(self, task: str = 'regression'):
        assert task in ('regression', 'classification'), \\
            f\"task must be 'regression' or 'classification', got {task!r}\"
        self.task     = task
        self._results = {}

    def evaluate(self, model, X_train: pd.DataFrame, X_test: pd.DataFrame,
                 y_train: pd.Series, y_test: pd.Series, cv: int = 5) -> dict:
        \"\"\"Cross-validate on train, fit, then evaluate on test.\"\"\"
        scoring   = 'r2' if self.task == 'regression' else 'accuracy'
        cv_result = cross_validate_model(model, X_train, y_train,
                                         cv=cv, scoring=scoring)
        model.fit(X_train, y_train)
        if self.task == 'regression':
            y_pred  = model.predict(X_test)
            r2      = float(r2_score(y_test, y_pred))
            rmse    = float(np.sqrt(mean_squared_error(y_test, y_pred)))
            mae     = float(mean_absolute_error(y_test, y_pred))
            metrics = {'r2': round(r2, 4),
                       'rmse': round(rmse, 2),
                       'mae':  round(mae,  2)}
        else:
            metrics = classification_metrics(model, X_test, y_test)
        self._results = {'task': self.task, 'cv': cv_result, 'metrics': metrics}
        return self._results

    def summary(self) -> str:
        \"\"\"Return a formatted multi-line summary string.\"\"\"
        if not self._results:
            return 'No evaluation run yet.'
        cv = self._results['cv']
        m  = self._results['metrics']
        lines = [
            f\"Task: {self.task}\",
            f\"Cross-val {cv['scoring']} ({cv['cv_folds']}-fold): \"
            f\"{cv['mean']:.4f} \\u00b1 {cv['std']:.4f}\",
        ]
        if self.task == 'regression':
            lines.append(f\"Test  R\\u00b2={m['r2']:.4f}  \"
                         f\"RMSE={m['rmse']:.2f}  MAE={m['mae']:.2f}\")
        else:
            lines.append(f\"Test  Acc={m['accuracy']:.4f}  F1={m['f1']:.4f}\")
        return '\\n'.join(lines)"""

# Cumulative provided stacks
_BEFORE_OVERFIT   = "\n\n\n".join([MAKE_DATA, CROSS_VAL_IMPL])
_BEFORE_CLASSIF   = "\n\n\n".join([MAKE_DATA, CROSS_VAL_IMPL, OVERFITTING_IMPL])
_BEFORE_METRICS   = "\n\n\n".join([MAKE_DATA, CROSS_VAL_IMPL, OVERFITTING_IMPL,
                                    CLASSIFIER_IMPL])
ALL_IMPLS         = "\n\n\n".join([MAKE_DATA, CROSS_VAL_IMPL, OVERFITTING_IMPL,
                                    CLASSIFIER_IMPL, METRICS_IMPL])


# ---------------------------------------------------------------------------
# Exercise 01 — cross_validate_model
# ---------------------------------------------------------------------------

def ex01():
    global _cid; _cid = 0
    return [
        md(
            "# Day 049 — Exercise 1: cross_validate_model\n\n"
            "**What you'll build:** `cross_validate_model(model, X, y, cv=5, "
            "scoring='r2') -> dict` — run k-fold cross-validation and return "
            "per-fold scores plus summary statistics (mean, std, min, max).\n\n"
            "**Why it matters:** A single train/test split is sensitive to which "
            "80% you happened to train on. With k-fold CV, the model is trained "
            "and evaluated k times on different subsets — the mean score is a far "
            "more reliable estimate of real-world performance."
        ),
        md("## Provided: Setup + Data Generators"),
        code(MAKE_DATA),
        md("## Your Implementation"),
        code(
            "def cross_validate_model(model, X: pd.DataFrame, y: pd.Series,\n"
            "                          cv: int = 5,\n"
            "                          scoring: str = 'r2') -> dict:\n"
            '    """\n'
            "    K-fold cross-validation.\n\n"
            "    Args:\n"
            "        model:   unfitted sklearn estimator\n"
            "        X, y:    full feature matrix and target (unsplit)\n"
            "        cv:      number of folds (default 5)\n"
            "        scoring: sklearn scoring string ('r2', 'accuracy', etc.)\n"
            "    Returns:\n"
            "        dict with keys: scores, mean, std, min, max, cv_folds, scoring\n"
            '    """\n'
            "    # TODO: kf     = KFold(n_splits=cv, shuffle=True, random_state=42)\n"
            "    # TODO: scores = cross_val_score(model, X, y, cv=kf, scoring=scoring)\n"
            "    # TODO: return {\n"
            "    #     'scores':   scores,\n"
            "    #     'mean':     round(float(scores.mean()), 4),\n"
            "    #     'std':      round(float(scores.std()),  4),\n"
            "    #     'min':      round(float(scores.min()),  4),\n"
            "    #     'max':      round(float(scores.max()),  4),\n"
            "    #     'cv_folds': cv,\n"
            "    #     'scoring':  scoring,\n"
            "    # }\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    df = make_regression_data(200)\n"
            "    X  = df.drop(columns=['price'])\n"
            "    y  = df['price']\n"
            "\n"
            "    # Check 1: defined, returns dict\n"
            "    try:\n"
            "        assert 'cross_validate_model' in globals()\n"
            "        result = cross_validate_model(LinearRegression(), X, y)\n"
            "        assert isinstance(result, dict), \\\n"
            "            f'expected dict, got {type(result).__name__}'\n"
            "        passed += 1; print('\\u2705 Check 1: cross_validate_model returns dict')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: all 7 keys present\n"
            "    try:\n"
            "        for k in ('scores', 'mean', 'std', 'min', 'max', 'cv_folds', 'scoring'):\n"
            "            assert k in result, f'missing key: {k!r}'\n"
            "        passed += 1; print('\\u2705 Check 2: all 7 keys present')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: len(scores) == cv (default 5)\n"
            "    try:\n"
            "        assert len(result['scores']) == 5, \\\n"
            "            f'expected 5 scores (one per fold), got {len(result[\"scores\"])}'\n"
            "        assert result['cv_folds'] == 5\n"
            "        passed += 1; print(f'\\u2705 Check 3: {len(result[\"scores\"])} scores (5 folds)')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: mean R² > 0.9 on housing data\n"
            "    try:\n"
            "        assert result['mean'] > 0.9, \\\n"
            "            f'mean R\\u00b2 should be > 0.9 on housing data, got {result[\"mean\"]}'\n"
            "        passed += 1; print(f'\\u2705 Check 4: mean R\\u00b2={result[\"mean\"]} > 0.9')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: std < 0.1 (consistent across folds)\n"
            "    try:\n"
            "        assert result['std'] < 0.1, \\\n"
            "            f'std should be < 0.1 (consistent model), got {result[\"std\"]}'\n"
            "        passed += 1; print(f'\\u2705 Check 5: std={result[\"std\"]} < 0.1 (stable CV)')\n"
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
            + CROSS_VAL_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 02 — overfitting_report
# ---------------------------------------------------------------------------

def ex02():
    global _cid; _cid = 100
    return [
        md(
            "# Day 049 — Exercise 2: overfitting_report\n\n"
            "**What you'll build:** `overfitting_report(X, y, max_depths=range(1, 11), "
            "...) -> pd.DataFrame` — train `DecisionTreeRegressor` at each depth, "
            "record train R² and test R², and flag rows where the gap exceeds 0.1 "
            "as overfitting.\n\n"
            "**Why it matters:** The bias-variance tradeoff shows up clearly in decision "
            "trees: a depth-1 tree underfits (both scores are low); a depth-20 tree "
            "memorises the training data (train R² = 1.0) but generalises poorly. "
            "Plotting the gap as a function of depth is the classic *overfitting curve*."
        ),
        md("## Provided: Setup + cross_validate_model"),
        code(_BEFORE_OVERFIT),
        md("## Your Implementation"),
        code(
            "def overfitting_report(X: pd.DataFrame, y: pd.Series,\n"
            "                        max_depths=range(1, 11),\n"
            "                        test_size: float = 0.2,\n"
            "                        random_state: int = 42) -> pd.DataFrame:\n"
            '    """\n'
            "    Train DecisionTreeRegressor at each max_depth.\n"
            "    Returns DataFrame with columns:\n"
            "        max_depth, train_r2, test_r2, gap, overfit\n"
            "    where gap = train_r2 - test_r2 and overfit = (gap > 0.1).\n"
            '    """\n'
            "    X_train, X_test, y_train, y_test = train_test_split(\n"
            "        X, y, test_size=test_size, random_state=random_state\n"
            "    )\n"
            "    records = []\n"
            "    for depth in max_depths:\n"
            "        # TODO: m = DecisionTreeRegressor(max_depth=depth, random_state=42)\n"
            "        # TODO: m.fit(X_train, y_train)\n"
            "        # TODO: tr_r2 = float(r2_score(y_train, m.predict(X_train)))\n"
            "        # TODO: te_r2 = float(r2_score(y_test,  m.predict(X_test)))\n"
            "        # TODO: gap   = round(tr_r2 - te_r2, 4)\n"
            "        # TODO: records.append({\n"
            "        #     'max_depth': depth,\n"
            "        #     'train_r2':  round(tr_r2, 4),\n"
            "        #     'test_r2':   round(te_r2, 4),\n"
            "        #     'gap':       gap,\n"
            "        #     'overfit':   bool(gap > 0.1),\n"
            "        # })\n"
            "        pass\n"
            "    return pd.DataFrame(records)"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    df = make_regression_data(200)\n"
            "    X  = df.drop(columns=['price'])\n"
            "    y  = df['price']\n"
            "\n"
            "    # Check 1: defined, returns DataFrame\n"
            "    try:\n"
            "        assert 'overfitting_report' in globals()\n"
            "        report = overfitting_report(X, y)\n"
            "        assert isinstance(report, pd.DataFrame), \\\n"
            "            f'expected DataFrame, got {type(report).__name__}'\n"
            "        passed += 1; print('\\u2705 Check 1: overfitting_report returns DataFrame')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: required columns present\n"
            "    try:\n"
            "        for col in ('max_depth', 'train_r2', 'test_r2', 'gap', 'overfit'):\n"
            "            assert col in report.columns, f'missing column: {col!r}'\n"
            "        passed += 1; print(f'\\u2705 Check 2: all 5 required columns present')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: row count == 10 (default range(1, 11))\n"
            "    try:\n"
            "        assert len(report) == 10, \\\n"
            "            f'expected 10 rows (depths 1-10), got {len(report)}'\n"
            "        passed += 1; print(f'\\u2705 Check 3: 10 rows (one per depth)')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: depth=1 shows underfitting — test_r2 < train_r2\n"
            "    try:\n"
            "        row1 = report[report['max_depth'] == 1].iloc[0]\n"
            "        assert row1['test_r2'] < row1['train_r2'], \\\n"
            "            f'at depth=1, test_r2 should be < train_r2; ' \\\n"
            "            f'got train={row1[\"train_r2\"]:.3f} test={row1[\"test_r2\"]:.3f}'\n"
            "        passed += 1; print(f'\\u2705 Check 4: depth=1 train_r2={row1[\"train_r2\"]:.3f} > test_r2={row1[\"test_r2\"]:.3f}')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: depth=10 memorises training data — train_r2 > 0.99\n"
            "    try:\n"
            "        row10 = report[report['max_depth'] == 10].iloc[0]\n"
            "        assert row10['train_r2'] > 0.99, \\\n"
            "            f'at depth=10, tree should memorise train data (train_r2 > 0.99), ' \\\n"
            "            f'got {row10[\"train_r2\"]}'\n"
            "        passed += 1; print(f'\\u2705 Check 5: depth=10 train_r2={row10[\"train_r2\"]} > 0.99 (memorised)')\n"
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
            + OVERFITTING_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 03 — train_classifier
# ---------------------------------------------------------------------------

def ex03():
    global _cid; _cid = 200
    return [
        md(
            "# Day 049 — Exercise 3: train_classifier\n\n"
            "**What you'll build:** `train_classifier(X_train, y_train, max_iter=1000) "
            "-> LogisticRegression` — train a logistic regression model for binary "
            "classification.\n\n"
            "**Why it matters:** Logistic Regression is to classification what Linear "
            "Regression is to regression — the fundamental linear model you use first "
            "before trying something more complex. It learns the decision boundary that "
            "best separates classes, and its coefficients are directly interpretable as "
            "log-odds per unit change in a feature."
        ),
        md("## Provided: Setup + cross_validate_model + overfitting_report"),
        code(_BEFORE_CLASSIF),
        md("## Your Implementation"),
        code(
            "def train_classifier(X_train: pd.DataFrame,\n"
            "                     y_train: pd.Series,\n"
            "                     max_iter: int = 1000) -> LogisticRegression:\n"
            '    """\n'
            "    Fit LogisticRegression for binary or multi-class classification.\n\n"
            "    Args:\n"
            "        X_train:  feature matrix (numeric, should be scaled)\n"
            "        y_train:  target labels\n"
            "        max_iter: solver iteration limit (default 1000 avoids ConvergenceWarning)\n"
            "    Returns:\n"
            "        Fitted LogisticRegression model\n"
            '    """\n'
            "    # TODO: model = LogisticRegression(random_state=42, max_iter=max_iter)\n"
            "    # TODO: model.fit(X_train, y_train)\n"
            "    # TODO: return model\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    df_c = make_classification_data(200)\n"
            "    X_c  = df_c.drop(columns=['passed'])\n"
            "    y_c  = df_c['passed']\n"
            "    X_tr_c, X_te_c, y_tr_c, y_te_c = train_test_split(\n"
            "        X_c, y_c, test_size=0.2, random_state=42\n"
            "    )\n"
            "    scaler    = StandardScaler()\n"
            "    X_tr_s    = pd.DataFrame(scaler.fit_transform(X_tr_c), columns=X_c.columns)\n"
            "    X_te_s    = pd.DataFrame(scaler.transform(X_te_c),     columns=X_c.columns)\n"
            "\n"
            "    # Check 1: defined, returns LogisticRegression\n"
            "    try:\n"
            "        assert 'train_classifier' in globals()\n"
            "        clf = train_classifier(X_tr_s, y_tr_c)\n"
            "        assert isinstance(clf, LogisticRegression), \\\n"
            "            f'expected LogisticRegression, got {type(clf).__name__}'\n"
            "        passed += 1; print('\\u2705 Check 1: train_classifier returns LogisticRegression')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: model is fitted (has coef_ attribute)\n"
            "    try:\n"
            "        assert hasattr(clf, 'coef_'), 'model must be fitted (has coef_)'\n"
            "        passed += 1; print('\\u2705 Check 2: model is fitted (has coef_)')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: coef_ shape matches n_features\n"
            "    try:\n"
            "        assert clf.coef_.shape[1] == X_c.shape[1], \\\n"
            "            f'coef_ n_features={clf.coef_.shape[1]}, expected {X_c.shape[1]}'\n"
            "        passed += 1; print(f'\\u2705 Check 3: coef_ shape {clf.coef_.shape} matches {X_c.shape[1]} features')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: accuracy on test set > 0.80\n"
            "    try:\n"
            "        y_pred = clf.predict(X_te_s)\n"
            "        acc    = accuracy_score(y_te_c, y_pred)\n"
            "        assert acc > 0.80, f'accuracy should be > 0.80, got {acc:.4f}'\n"
            "        passed += 1; print(f'\\u2705 Check 4: test accuracy={acc:.4f} > 0.80')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: model has predict_proba (LogisticRegression feature)\n"
            "    try:\n"
            "        assert hasattr(clf, 'predict_proba'), \\\n"
            "            'LogisticRegression should have predict_proba method'\n"
            "        proba = clf.predict_proba(X_te_s)\n"
            "        assert proba.shape == (len(X_te_s), 2), \\\n"
            "            f'predict_proba shape {proba.shape} should be ({len(X_te_s)}, 2)'\n"
            "        passed += 1; print(f'\\u2705 Check 5: predict_proba works, shape={proba.shape}')\n"
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
            + CLASSIFIER_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 04 — classification_metrics
# ---------------------------------------------------------------------------

def ex04():
    global _cid; _cid = 300
    return [
        md(
            "# Day 049 — Exercise 4: classification_metrics\n\n"
            "**What you'll build:** `classification_metrics(model, X_test, y_test) -> dict` "
            "— compute accuracy, precision, recall, F1, confusion matrix, and the full "
            "classification report for a fitted classifier.\n\n"
            "**Why it matters:** Accuracy alone is misleading when classes are imbalanced. "
            "A model that always predicts 'pass' is 65% accurate on our dataset — but it "
            "never identifies a failing student. Precision tells you how many predicted "
            "positives are correct; recall tells you how many actual positives were found; "
            "F1 is the harmonic mean of both."
        ),
        md("## Provided: Setup + cross_validate_model + overfitting_report + train_classifier"),
        code(_BEFORE_METRICS),
        md("## Your Implementation"),
        code(
            "def classification_metrics(model, X_test: pd.DataFrame,\n"
            "                            y_test: pd.Series) -> dict:\n"
            '    """\n'
            "    Full classification evaluation for a fitted model.\n\n"
            "    Returns dict with keys:\n"
            "        accuracy         — fraction of correct predictions\n"
            "        precision        — TP / (TP + FP), zero_division=0\n"
            "        recall           — TP / (TP + FN), zero_division=0\n"
            "        f1               — harmonic mean of precision and recall\n"
            "        confusion_matrix — 2D numpy array [[TN, FP], [FN, TP]]\n"
            "        report           — sklearn classification_report string\n"
            '    """\n'
            "    y_pred = model.predict(X_test)\n"
            "    # TODO: return {\n"
            "    #     'accuracy':         round(float(accuracy_score(y_test, y_pred)), 4),\n"
            "    #     'precision':        round(float(precision_score(y_test, y_pred,\n"
            "    #                                                      zero_division=0)), 4),\n"
            "    #     'recall':           round(float(recall_score(y_test, y_pred,\n"
            "    #                                                   zero_division=0)), 4),\n"
            "    #     'f1':               round(float(f1_score(y_test, y_pred,\n"
            "    #                                               zero_division=0)), 4),\n"
            "    #     'confusion_matrix': confusion_matrix(y_test, y_pred),\n"
            "    #     'report':           classification_report(y_test, y_pred),\n"
            "    # }\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    df_c = make_classification_data(200)\n"
            "    X_c  = df_c.drop(columns=['passed'])\n"
            "    y_c  = df_c['passed']\n"
            "    X_tr_c, X_te_c, y_tr_c, y_te_c = train_test_split(\n"
            "        X_c, y_c, test_size=0.2, random_state=42\n"
            "    )\n"
            "    scaler = StandardScaler()\n"
            "    X_tr_s = pd.DataFrame(scaler.fit_transform(X_tr_c), columns=X_c.columns)\n"
            "    X_te_s = pd.DataFrame(scaler.transform(X_te_c),     columns=X_c.columns)\n"
            "    clf    = train_classifier(X_tr_s, y_tr_c)\n"
            "\n"
            "    # Check 1: defined, returns dict\n"
            "    try:\n"
            "        assert 'classification_metrics' in globals()\n"
            "        result = classification_metrics(clf, X_te_s, y_te_c)\n"
            "        assert isinstance(result, dict), \\\n"
            "            f'expected dict, got {type(result).__name__}'\n"
            "        passed += 1; print('\\u2705 Check 1: classification_metrics returns dict')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: all 6 keys present\n"
            "    try:\n"
            "        for k in ('accuracy', 'precision', 'recall', 'f1',\n"
            "                  'confusion_matrix', 'report'):\n"
            "            assert k in result, f'missing key: {k!r}'\n"
            "        passed += 1; print('\\u2705 Check 2: all 6 keys present')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: numeric metrics in [0, 1]\n"
            "    try:\n"
            "        for k in ('accuracy', 'precision', 'recall', 'f1'):\n"
            "            v = result[k]\n"
            "            assert 0.0 <= v <= 1.0, f'{k}={v} is not in [0, 1]'\n"
            "        passed += 1; print(f'\\u2705 Check 3: all numeric metrics in [0, 1]')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: confusion_matrix is 2D array with shape (2, 2)\n"
            "    try:\n"
            "        cm = result['confusion_matrix']\n"
            "        assert hasattr(cm, 'shape'), 'confusion_matrix must be numpy array'\n"
            "        assert cm.shape == (2, 2), \\\n"
            "            f'confusion_matrix shape {cm.shape} should be (2, 2)'\n"
            "        assert cm.sum() == len(y_te_c), \\\n"
            "            f'confusion_matrix sum={cm.sum()} should equal n_test={len(y_te_c)}'\n"
            "        passed += 1; print(f'\\u2705 Check 4: confusion_matrix shape {cm.shape}, sum={cm.sum()}')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: report is a non-empty string\n"
            "    try:\n"
            "        rep = result['report']\n"
            "        assert isinstance(rep, str) and len(rep) > 20, \\\n"
            "            f'report must be a non-empty string, got {type(rep).__name__}'\n"
            "        passed += 1; print(f'\\u2705 Check 5: report is a {len(rep)}-char string')\n"
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
            + METRICS_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 05 — ModelEvaluator class
# ---------------------------------------------------------------------------

def ex05():
    global _cid; _cid = 400
    return [
        md(
            "# Day 049 — Exercise 5: ModelEvaluator Class\n\n"
            "**What you'll build:** The `ModelEvaluator` class — a unified evaluator "
            "for both regression and classification models:\n"
            "- `__init__(task='regression')` — 'regression' or 'classification'\n"
            "- `evaluate(model, X_train, X_test, y_train, y_test, cv=5) -> dict` — "
            "cross-validate on train, fit, then evaluate on test\n"
            "- `summary() -> str` — formatted text summary\n\n"
            "**Why it matters:** Every ML project follows the same evaluation loop. "
            "`ModelEvaluator` encodes that loop in a reusable object: cross-validate "
            "to get a reliable estimate, fit the final model on the full training set, "
            "then measure final performance on the held-out test set."
        ),
        md("## Provided: All Helper Functions"),
        code(ALL_IMPLS),
        md("## Your Implementation"),
        code(
            "class ModelEvaluator:\n"
            '    """\n'
            "    Unified evaluator for regression and classification.\n\n"
            "    Usage:\n"
            "        ev     = ModelEvaluator(task='regression')\n"
            "        result = ev.evaluate(LinearRegression(), X_train, X_test, y_train, y_test)\n"
            "        print(ev.summary())\n"
            '    """\n'
            "\n"
            "    def __init__(self, task: str = 'regression'):\n"
            "        # TODO: assert task in ('regression', 'classification')\n"
            "        # TODO: self.task     = task\n"
            "        # TODO: self._results = {}\n"
            "        pass\n"
            "\n"
            "    def evaluate(self, model, X_train: pd.DataFrame, X_test: pd.DataFrame,\n"
            "                 y_train: pd.Series, y_test: pd.Series,\n"
            "                 cv: int = 5) -> dict:\n"
            '        """\n'
            "        Cross-validate on train, fit the model, evaluate on test.\n"
            "        Uses cross_validate_model for CV and classification_metrics or\n"
            "        regression metrics depending on self.task.\n"
            "        Stores results in self._results.\n"
            "        Returns the results dict.\n"
            '        """\n'
            "        # TODO: scoring   = 'r2' if self.task == 'regression' else 'accuracy'\n"
            "        # TODO: cv_result = cross_validate_model(model, X_train, y_train,\n"
            "        #                                        cv=cv, scoring=scoring)\n"
            "        # TODO: model.fit(X_train, y_train)\n"
            "        # TODO: if self.task == 'regression':\n"
            "        #     y_pred  = model.predict(X_test)\n"
            "        #     r2      = float(r2_score(y_test, y_pred))\n"
            "        #     rmse    = float(np.sqrt(mean_squared_error(y_test, y_pred)))\n"
            "        #     mae     = float(mean_absolute_error(y_test, y_pred))\n"
            "        #     metrics = {'r2': round(r2, 4),\n"
            "        #                'rmse': round(rmse, 2),\n"
            "        #                'mae':  round(mae,  2)}\n"
            "        # TODO: else:\n"
            "        #     metrics = classification_metrics(model, X_test, y_test)\n"
            "        # TODO: self._results = {'task': self.task, 'cv': cv_result, 'metrics': metrics}\n"
            "        # TODO: return self._results\n"
            "        pass\n"
            "\n"
            "    def summary(self) -> str:\n"
            '        """\n'
            "        Return a multi-line string summarising CV scores and test metrics.\n"
            '        """\n'
            "        # TODO: if not self._results:\n"
            "        #     return 'No evaluation run yet.'\n"
            "        # TODO: cv = self._results['cv']\n"
            "        # TODO: m  = self._results['metrics']\n"
            "        # TODO: lines = [\n"
            "        #     f\"Task: {self.task}\",\n"
            "        #     f\"Cross-val {cv['scoring']} ({cv['cv_folds']}-fold): \"\n"
            "        #     f\"{cv['mean']:.4f} \\u00b1 {cv['std']:.4f}\",\n"
            "        # ]\n"
            "        # TODO: if self.task == 'regression':\n"
            "        #     lines.append(f\"Test R\\u00b2={m['r2']:.4f} RMSE={m['rmse']:.2f} MAE={m['mae']:.2f}\")\n"
            "        # TODO: else:\n"
            "        #     lines.append(f\"Test Acc={m['accuracy']:.4f} F1={m['f1']:.4f}\")\n"
            "        # TODO: return '\\n'.join(lines)\n"
            "        pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # ── Regression setup ──\n"
            "    df_r = make_regression_data(200)\n"
            "    X_r  = df_r.drop(columns=['price'])\n"
            "    y_r  = df_r['price']\n"
            "    X_tr_r, X_te_r, y_tr_r, y_te_r = train_test_split(\n"
            "        X_r, y_r, test_size=0.2, random_state=42\n"
            "    )\n"
            "    sc_r   = StandardScaler()\n"
            "    X_tr_rs = pd.DataFrame(sc_r.fit_transform(X_tr_r), columns=X_r.columns)\n"
            "    X_te_rs = pd.DataFrame(sc_r.transform(X_te_r),     columns=X_r.columns)\n"
            "\n"
            "    # Check 1: class defined with evaluate and summary\n"
            "    try:\n"
            "        assert 'ModelEvaluator' in globals()\n"
            "        for m in ('evaluate', 'summary'):\n"
            "            assert hasattr(ModelEvaluator, m), f'missing method: {m}'\n"
            "        passed += 1; print('\\u2705 Check 1: ModelEvaluator has evaluate and summary')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: evaluate returns dict with task, cv, metrics\n"
            "    try:\n"
            "        ev     = ModelEvaluator(task='regression')\n"
            "        result = ev.evaluate(LinearRegression(),\n"
            "                             X_tr_rs, X_te_rs, y_tr_r, y_te_r)\n"
            "        assert isinstance(result, dict), \\\n"
            "            f'evaluate must return dict, got {type(result).__name__}'\n"
            "        for k in ('task', 'cv', 'metrics'):\n"
            "            assert k in result, f'missing key: {k!r}'\n"
            "        passed += 1; print('\\u2705 Check 2: evaluate returns dict with task, cv, metrics')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 3: regression metrics include r2 > 0\n"
            "    try:\n"
            "        m = result['metrics']\n"
            "        assert 'r2' in m, \"regression metrics must include 'r2'\"\n"
            "        assert m['r2'] > 0, f'R\\u00b2 should be > 0, got {m[\"r2\"]}'\n"
            "        assert 'mae' in m, \"regression metrics must include 'mae'\"\n"
            "        passed += 1; print(f'\\u2705 Check 3: regression metrics R\\u00b2={m[\"r2\"]} MAE={m[\"mae\"]}')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: classification mode — accuracy > 0.80\n"
            "    try:\n"
            "        df_c = make_classification_data(200)\n"
            "        X_c  = df_c.drop(columns=['passed'])\n"
            "        y_c  = df_c['passed']\n"
            "        X_tr_c, X_te_c, y_tr_c, y_te_c = train_test_split(\n"
            "            X_c, y_c, test_size=0.2, random_state=42\n"
            "        )\n"
            "        sc_c    = StandardScaler()\n"
            "        X_tr_cs = pd.DataFrame(sc_c.fit_transform(X_tr_c), columns=X_c.columns)\n"
            "        X_te_cs = pd.DataFrame(sc_c.transform(X_te_c),     columns=X_c.columns)\n"
            "        ev_c    = ModelEvaluator(task='classification')\n"
            "        res_c   = ev_c.evaluate(LogisticRegression(max_iter=1000),\n"
            "                                X_tr_cs, X_te_cs, y_tr_c, y_te_c)\n"
            "        acc = res_c['metrics']['accuracy']\n"
            "        assert acc > 0.80, f'classification accuracy should be > 0.80, got {acc}'\n"
            "        passed += 1; print(f'\\u2705 Check 4: classification accuracy={acc} > 0.80')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: summary() returns non-empty string\n"
            "    try:\n"
            "        s = ev.summary()\n"
            "        assert isinstance(s, str) and len(s) > 10, \\\n"
            "            f'summary must be a non-empty string, got {s!r}'\n"
            "        passed += 1; print(f'\\u2705 Check 5: summary() returns {len(s)}-char string')\n"
            "        print('\\n--- Summary ---')\n"
            "        print(s)\n"
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
            + MODEL_EVALUATOR_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Project notebook
# ---------------------------------------------------------------------------

def project_nb():
    global _cid; _cid = 500
    all_code = ALL_IMPLS + "\n\n\n" + MODEL_EVALUATOR_IMPL
    return [
        md(
            "# Day 049 Project: Evaluate & Improve the Model\n\n"
            "## What You're Building\n\n"
            "A full evaluation report that compares a regression model and a "
            "classification model, detects overfitting, and saves a two-panel chart.\n\n"
            "## Project Requirements\n\n"
            "1. Evaluate a `LinearRegression` on housing data using `ModelEvaluator(task='regression')`\n"
            "2. Evaluate a `LogisticRegression` on exam data using `ModelEvaluator(task='classification')`\n"
            "3. Build an `overfitting_report` for the housing data (depths 1–15)\n"
            "4. Store: `reg_summary` (str), `clf_summary` (str), `overfit_df` (DataFrame)\n"
            "5. Save a 2-panel matplotlib figure to `model_evaluation.png`:\n"
            "   - Left panel: overfitting curve (train_r2 and test_r2 vs depth)\n"
            "   - Right panel: confusion matrix heatmap for the classifier\n"
            "6. Run `_run_project_checks()` to verify\n\n"
            "Use `StandardScaler` on both datasets before training."
        ),
        md("## Provided: All Implementations"),
        code(all_code),
        md("## Your Pipeline"),
        code(
            "import matplotlib\n"
            "matplotlib.use('Agg')\n"
            "import matplotlib.pyplot as plt\n"
            "\n"
            "# ── Regression evaluation ──\n"
            "df_r = make_regression_data(200)\n"
            "X_r  = df_r.drop(columns=['price'])\n"
            "y_r  = df_r['price']\n"
            "X_tr_r, X_te_r, y_tr_r, y_te_r = train_test_split(X_r, y_r,\n"
            "                                                    test_size=0.2, random_state=42)\n"
            "sc_r    = StandardScaler()\n"
            "X_tr_rs = pd.DataFrame(sc_r.fit_transform(X_tr_r), columns=X_r.columns)\n"
            "X_te_rs = pd.DataFrame(sc_r.transform(X_te_r),     columns=X_r.columns)\n"
            "\n"
            "# TODO: ev_r        = ModelEvaluator(task='regression')\n"
            "# TODO: ev_r.evaluate(LinearRegression(), X_tr_rs, X_te_rs, y_tr_r, y_te_r)\n"
            "# TODO: reg_summary = ev_r.summary()\n"
            "# TODO: print(reg_summary)\n"
            "\n"
            "# ── Classification evaluation ──\n"
            "df_c = make_classification_data(200)\n"
            "X_c  = df_c.drop(columns=['passed'])\n"
            "y_c  = df_c['passed']\n"
            "X_tr_c, X_te_c, y_tr_c, y_te_c = train_test_split(X_c, y_c,\n"
            "                                                    test_size=0.2, random_state=42)\n"
            "sc_c    = StandardScaler()\n"
            "X_tr_cs = pd.DataFrame(sc_c.fit_transform(X_tr_c), columns=X_c.columns)\n"
            "X_te_cs = pd.DataFrame(sc_c.transform(X_te_c),     columns=X_c.columns)\n"
            "\n"
            "# TODO: ev_c        = ModelEvaluator(task='classification')\n"
            "# TODO: ev_c.evaluate(LogisticRegression(max_iter=1000), X_tr_cs, X_te_cs, y_tr_c, y_te_c)\n"
            "# TODO: clf_summary = ev_c.summary()\n"
            "# TODO: print(clf_summary)\n"
            "\n"
            "# ── Overfitting report ──\n"
            "# TODO: overfit_df = overfitting_report(X_r, y_r, max_depths=range(1, 16))\n"
            "# TODO: print(overfit_df.to_string(index=False))\n"
            "\n"
            "# ── Save 2-panel figure ──\n"
            "# TODO: fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))\n"
            "# TODO: # Left: overfitting curve\n"
            "# TODO: ax1.plot(overfit_df['max_depth'], overfit_df['train_r2'],\n"
            "#                label='Train R\\u00b2', marker='o')\n"
            "# TODO: ax1.plot(overfit_df['max_depth'], overfit_df['test_r2'],\n"
            "#                label='Test R\\u00b2', marker='s')\n"
            "# TODO: ax1.set_xlabel('max_depth'); ax1.set_ylabel('R\\u00b2')\n"
            "# TODO: ax1.set_title('Overfitting Curve'); ax1.legend()\n"
            "# TODO: # Right: confusion matrix heatmap\n"
            "# TODO: cm = ev_c._results['metrics']['confusion_matrix']\n"
            "# TODO: ax2.imshow(cm, cmap='Blues')\n"
            "# TODO: for i in range(2):\n"
            "#     for j in range(2):\n"
            "#         ax2.text(j, i, str(cm[i, j]), ha='center', va='center', fontsize=14)\n"
            "# TODO: ax2.set_xticks([0,1]); ax2.set_yticks([0,1])\n"
            "# TODO: ax2.set_xticklabels(['Pred 0','Pred 1'])\n"
            "# TODO: ax2.set_yticklabels(['True 0','True 1'])\n"
            "# TODO: ax2.set_title('Confusion Matrix')\n"
            "# TODO: plt.tight_layout()\n"
            "# TODO: fig.savefig('model_evaluation.png', bbox_inches='tight', dpi=100)\n"
            "# TODO: plt.close('all')\n"
            "# TODO: print('Chart saved: model_evaluation.png')"
        ),
        md("## Checks"),
        code(
            "import os\n"
            "\n"
            "def _run_project_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: reg_summary defined and is a string\n"
            "    try:\n"
            "        assert 'reg_summary' in globals(), \\\n"
            "            'reg_summary not defined — call ev_r.summary()'\n"
            "        assert isinstance(reg_summary, str) and len(reg_summary) > 10\n"
            "        passed += 1; print('\\u2705 Check 1: reg_summary defined')\n"
            "        print(reg_summary)\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}'); return\n"
            "\n"
            "    # Check 2: clf_summary defined and is a string\n"
            "    try:\n"
            "        assert 'clf_summary' in globals(), \\\n"
            "            'clf_summary not defined — call ev_c.summary()'\n"
            "        assert isinstance(clf_summary, str) and len(clf_summary) > 10\n"
            "        passed += 1; print('\\u2705 Check 2: clf_summary defined')\n"
            "        print(clf_summary)\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: overfit_df has 15 rows (depths 1-15)\n"
            "    try:\n"
            "        assert 'overfit_df' in globals(), \\\n"
            "            'overfit_df not defined — call overfitting_report(...)'\n"
            "        assert isinstance(overfit_df, pd.DataFrame)\n"
            "        assert len(overfit_df) == 15, \\\n"
            "            f'overfit_df should have 15 rows (depths 1-15), got {len(overfit_df)}'\n"
            "        passed += 1; print(f'\\u2705 Check 3: overfit_df has 15 rows')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: cv mean in reg_summary suggests R² > 0\n"
            "    try:\n"
            "        assert 'r2' in reg_summary.lower() or 'R²' in reg_summary, \\\n"
            "            'reg_summary should mention R\\u00b2'\n"
            "        passed += 1; print('\\u2705 Check 4: reg_summary mentions R\\u00b2')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: chart file saved\n"
            "    try:\n"
            "        assert os.path.exists('model_evaluation.png'), \\\n"
            "            'model_evaluation.png not found'\n"
            "        assert os.path.getsize('model_evaluation.png') > 1000\n"
            "        passed += 1; print('\\u2705 Check 5: model_evaluation.png saved')\n"
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
            "- Add `DecisionTreeClassifier(max_depth=3)` to the classification pipeline "
            "and compare its accuracy and F1 against LogisticRegression\n"
            "- Try `scoring='neg_root_mean_squared_error'` in cross_val_score (sklearn "
            "uses negative scores so higher is always better) and convert back to positive\n"
            "- Plot the learning curve: train on 20%, 40%, 60%, 80%, 100% of training data "
            "and show how test R² changes\n"
            "- Use `ollama.chat` to narrate the reg_summary and clf_summary in plain English"
        ),
    ]


# ---------------------------------------------------------------------------
# Solution notebook
# ---------------------------------------------------------------------------

def solution_nb():
    global _cid; _cid = 600
    all_code = ALL_IMPLS + "\n\n\n" + MODEL_EVALUATOR_IMPL
    return [
        md(
            "# Day 049 Solution — Model Evaluation\n\n"
            "Demonstrates: cross-validation, overfitting curves, LogisticRegression "
            "classification metrics, confusion matrix heatmap, and ModelEvaluator "
            "for both regression and classification tasks."
        ),
        code(
            "import matplotlib\n"
            "matplotlib.use('Agg')\n"
            "import matplotlib.pyplot as plt\n"
            "import os\n"
        ),
        code(all_code),
        md("## Step 1 — Cross-Validation on Regression"),
        code(
            "df_r = make_regression_data(200)\n"
            "X_r  = df_r.drop(columns=['price'])\n"
            "y_r  = df_r['price']\n"
            "\n"
            "cv_result = cross_validate_model(LinearRegression(), X_r, y_r, cv=5, scoring='r2')\n"
            "print(f\"CV R\\u00b2 scores: {cv_result['scores'].round(4)}\")\n"
            "print(f\"Mean: {cv_result['mean']:.4f}  Std: {cv_result['std']:.4f}\")\n"
            "\n"
            "assert cv_result['mean'] > 0.9\n"
            "assert len(cv_result['scores']) == 5"
        ),
        md("## Step 2 — Overfitting Curve"),
        code(
            "overfit_df = overfitting_report(X_r, y_r, max_depths=range(1, 16))\n"
            "\n"
            "print('Overfitting report:')\n"
            "print(overfit_df.to_string(index=False))\n"
            "\n"
            "row10 = overfit_df[overfit_df['max_depth'] == 10].iloc[0]\n"
            "assert row10['train_r2'] > 0.99,  f'depth=10 should memorise train, got {row10[\"train_r2\"]}'"
        ),
        md("## Step 3 — Classification Pipeline"),
        code(
            "df_c = make_classification_data(200)\n"
            "X_c  = df_c.drop(columns=['passed'])\n"
            "y_c  = df_c['passed']\n"
            "X_tr_c, X_te_c, y_tr_c, y_te_c = train_test_split(\n"
            "    X_c, y_c, test_size=0.2, random_state=42\n"
            ")\n"
            "sc_c    = StandardScaler()\n"
            "X_tr_cs = pd.DataFrame(sc_c.fit_transform(X_tr_c), columns=X_c.columns)\n"
            "X_te_cs = pd.DataFrame(sc_c.transform(X_te_c),     columns=X_c.columns)\n"
            "\n"
            "clf = train_classifier(X_tr_cs, y_tr_c)\n"
            "cm_result = classification_metrics(clf, X_te_cs, y_te_c)\n"
            "\n"
            "print('Classification metrics:')\n"
            "for k in ('accuracy', 'precision', 'recall', 'f1'):\n"
            "    print(f'  {k}: {cm_result[k]:.4f}')\n"
            "print('Confusion matrix:\\n', cm_result['confusion_matrix'])\n"
            "print(cm_result['report'])\n"
            "\n"
            "assert cm_result['accuracy'] > 0.80"
        ),
        md("## Step 4 — ModelEvaluator (both tasks)"),
        code(
            "X_tr_r, X_te_r, y_tr_r, y_te_r = train_test_split(\n"
            "    X_r, y_r, test_size=0.2, random_state=42\n"
            ")\n"
            "sc_r    = StandardScaler()\n"
            "X_tr_rs = pd.DataFrame(sc_r.fit_transform(X_tr_r), columns=X_r.columns)\n"
            "X_te_rs = pd.DataFrame(sc_r.transform(X_te_r),     columns=X_r.columns)\n"
            "\n"
            "ev_r = ModelEvaluator(task='regression')\n"
            "ev_r.evaluate(LinearRegression(), X_tr_rs, X_te_rs, y_tr_r, y_te_r)\n"
            "reg_summary = ev_r.summary()\n"
            "\n"
            "ev_c = ModelEvaluator(task='classification')\n"
            "ev_c.evaluate(LogisticRegression(max_iter=1000),\n"
            "              X_tr_cs, X_te_cs, y_tr_c, y_te_c)\n"
            "clf_summary = ev_c.summary()\n"
            "\n"
            "print('=== Regression ===')\n"
            "print(reg_summary)\n"
            "print('\\n=== Classification ===')\n"
            "print(clf_summary)"
        ),
        md("## Step 5 — Save Visualisation"),
        code(
            "fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))\n"
            "\n"
            "# Left: overfitting curve\n"
            "ax1.plot(overfit_df['max_depth'], overfit_df['train_r2'],\n"
            "         marker='o', label='Train R\\u00b2', color='steelblue')\n"
            "ax1.plot(overfit_df['max_depth'], overfit_df['test_r2'],\n"
            "         marker='s', label='Test R\\u00b2',  color='tomato')\n"
            "ax1.fill_between(overfit_df['max_depth'],\n"
            "                  overfit_df['test_r2'], overfit_df['train_r2'],\n"
            "                  alpha=0.15, color='gray', label='gap')\n"
            "ax1.set_xlabel('max_depth')\n"
            "ax1.set_ylabel('R\\u00b2')\n"
            "ax1.set_title('Bias-Variance Tradeoff (DecisionTree)')\n"
            "ax1.legend()\n"
            "ax1.set_ylim(0, 1.05)\n"
            "\n"
            "# Right: confusion matrix heatmap\n"
            "cm_arr = ev_c._results['metrics']['confusion_matrix']\n"
            "im = ax2.imshow(cm_arr, cmap='Blues', vmin=0)\n"
            "for i in range(2):\n"
            "    for j in range(2):\n"
            "        ax2.text(j, i, str(cm_arr[i, j]),\n"
            "                  ha='center', va='center', fontsize=14, fontweight='bold')\n"
            "ax2.set_xticks([0, 1]); ax2.set_yticks([0, 1])\n"
            "ax2.set_xticklabels(['Pred: Fail', 'Pred: Pass'])\n"
            "ax2.set_yticklabels(['True: Fail', 'True: Pass'])\n"
            "ax2.set_title(f\"Confusion Matrix  Acc={ev_c._results['metrics']['accuracy']}\")\n"
            "\n"
            "plt.tight_layout()\n"
            "fig.savefig('model_evaluation.png', bbox_inches='tight', dpi=100)\n"
            "plt.close('all')\n"
            "print('Chart saved: model_evaluation.png')\n"
            "\n"
            "assert os.path.exists('model_evaluation.png')\n"
            "assert os.path.getsize('model_evaluation.png') > 1000\n"
            "\n"
            "print('\\nModel Evaluation complete!')"
        ),
    ]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Generating Day 049 notebooks...")
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
