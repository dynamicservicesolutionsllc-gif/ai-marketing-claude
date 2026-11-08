#!/usr/bin/env python3
"""Run the authorized Amazon API discovery as a one-candidate GitHub queue job."""
import sys
import discover_products

# Keep each scheduled run incremental; all candidates still require editorial review.
discover_products.PRODUCTS_TO_STAGE = 1

if __name__ == "__main__":
    try:
        sys.exit(discover_products.main())
    except (RuntimeError, ValueError, KeyError, OSError) as exc:
        discover_products.log_msg(
            f"ERROR: {type(exc).__name__}: discovery stopped; no live import"
        )
        sys.exit(1)
