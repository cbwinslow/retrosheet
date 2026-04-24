#!/usr/bin/env python3
"""Train simple logistic‑regression models for live‑play odds.

The live ingestion populates ``features.play_snapshot`` with two binary flags:
* ``is_hit`` – true when the play resulted in a hit (single, double, triple, HR).
* ``is_strikeout`` – true when the pitcher recorded a strikeout.

We train two independent models (one per target) and store them under
``data/models/``.  The models are registered in the existing ``models.model_registry``
so they can be loaded by the same inference service used for historic models.
"""

import joblib
import pandas as pd
import structlog
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

log = structlog.get_logger(__name__)

# Re‑use the warehouse helper to obtain a DB connection
from scripts.warehouse import get_connection


def load_features(conn) -> pd.DataFrame:
    sql = """
        SELECT game_pk, play_id, inning, half_inning, outs, balls, strikes,
               home_score, away_score, score_diff,
               batter_id, pitcher_id, batter_hand, pitcher_hand,
               leverage_idx, is_hit, is_strikeout
        FROM features.play_snapshot
        WHERE is_hit IS NOT NULL AND is_strikeout IS NOT NULL
    """
    return pd.read_sql(sql, conn)


def train_and_save(df: pd.DataFrame, target: str, model_name: str):
    X = df.drop(columns=["game_pk", "play_id", target])
    y = df[target].astype(int)
    model = LogisticRegression(max_iter=200, n_jobs=4)
    model.fit(X, y)
    auc = roc_auc_score(y, model.predict_proba(X)[:, 1])
    log.info("trained_model", model=model_name, auc=auc)

    model_path = f"data/models/{model_name}.joblib"
    joblib.dump(model, model_path)
    log.info("model_saved", path=model_path)

    # Register / update in model_registry (same table used by historic models)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO models.model_registry (model_name, model_path, model_type, is_active, created_at, updated_at)
        VALUES (%s, %s, %s, TRUE, now(), now())
        ON CONFLICT (model_name) DO UPDATE SET model_path = EXCLUDED.model_path, is_active = TRUE, updated_at = now();
        """,
        (model_name, model_path, "logistic_regression"),
    )
    conn.commit()
    cur.close()
    conn.close()


def main():
    conn = get_connection()
    df = load_features(conn)
    conn.close()
    if df.empty:
        log.warning("no_features", msg="features.play_snapshot empty – abort training")
        return
    train_and_save(df, target="is_hit", model_name="live_hit_odds")
    train_and_save(df, target="is_strikeout", model_name="live_so_odds")


if __name__ == "__main__":
    main()
