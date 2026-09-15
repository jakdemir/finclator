"""Weekly pipeline: fetch → classify → prices → evaluate → score → matrix."""
from __future__ import annotations

import sys

from . import audit, classify, evaluate, fetch, matrix, pine, prices, score
from .db import connect, log


def main(skip_fetch: bool = False, skip_classify: bool = False) -> None:
    conn = connect()
    fetch.sync_roster(conn)
    if not skip_fetch:
        log(f"fetch: {fetch.fetch_all(conn)}")
    if not skip_classify:
        log(f"classify: {classify.classify_pending(conn)}")
    log(f"prices: {prices.update_prices(conn)}")
    log(f"evaluate: {evaluate.evaluate(conn)}")
    log(f"score: {score.recompute(conn)}")
    matrix.print_grid(matrix.build(conn))
    log(f"audit: {audit.build()}")
    log(f"pine: {pine.generate(conn)}")


if __name__ == "__main__":
    main(skip_fetch="--no-fetch" in sys.argv, skip_classify="--no-classify" in sys.argv)
