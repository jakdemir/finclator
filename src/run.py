"""Weekly pipeline: fetch → classify → prices → evaluate → score → matrix."""
from __future__ import annotations

import sys

from . import classify, evaluate, fetch, matrix, prices, score
from .db import connect


def main(skip_fetch: bool = False, skip_classify: bool = False) -> None:
    conn = connect()
    fetch.sync_roster(conn)
    if not skip_fetch:
        print("fetch:", fetch.fetch_all(conn))
    if not skip_classify:
        print("classify:", classify.classify_pending(conn))
    print("prices:", prices.update_prices(conn))
    print("evaluate:", evaluate.evaluate(conn))
    print("score:", score.recompute(conn))
    matrix.print_grid(matrix.build(conn))


if __name__ == "__main__":
    main(skip_fetch="--no-fetch" in sys.argv, skip_classify="--no-classify" in sys.argv)
