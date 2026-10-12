#!/usr/bin/env python3
"""PostHog adapter — turns product-analytics data into a strategy business model.

WHAT POSTHOG CAN AND CANNOT TELL YOU
------------------------------------
This matters more than the code. PostHog knows what people did in your product. It does not
know your margins, your ad spend, or your sales labour. So:

  PostHog CAN supply (and this adapter derives):
    retention_months      <- from a retention curve
    test_baseline_rate    <- from a funnel's first-step conversion
    available_sample      <- from the size of the exposed cohort

  PostHog CANNOT supply (this adapter lists them in `missing`, every time):
    price_per_unit, variable_cost_per_unit, marketing_budget, monthly_fixed_costs,
    expected_new_customers, claimed_cac, payback_tolerance_months

An adapter that quietly filled those with plausible defaults would be the single most dangerous
object in this repository. It does not. Whatever it cannot source is named in `missing`, and
`strategy_calc.py` will then tell you what it could not compute.

MODES
  --live         read the PostHog API (needs POSTHOG_API_KEY and POSTHOG_PROJECT_ID)
  --offline FILE replay a saved JSON response (used by CI; also the way to work without a key)

USAGE
  export POSTHOG_API_KEY=phx_...
  export POSTHOG_PROJECT_ID=12345
  python3 tools/adapters/posthog.py --live --insight retention --insight-id abc123

  python3 tools/adapters/posthog.py --offline examples/adapter/posthog_retention.json

Only the standard library is used: no SDK, no dependency, no implicit network call.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

HOST_DEFAULT = "https://us.posthog.com"
TIMEOUT_SECONDS = 30

# Fields PostHog structurally cannot provide. Named here so the omission is deliberate and visible.
NOT_AVAILABLE_FROM_POSTHOG = [
    "price_per_unit",
    "variable_cost_per_unit",
    "monthly_fixed_costs",
    "marketing_budget",
    "expected_new_customers",
    "claimed_cac",
    "payback_tolerance_months",
]


# --------------------------------------------------------------------------- derivation
def lifetime_from_retention(curve: list[dict], floor: float = 0.5) -> tuple[float | None, str]:
    """Estimate an expected customer lifetime from a retention curve.

    Two things make this harder than it looks:

    1. Retention curves are truncated. Reading "the month retention crosses 50%" gives a
       half-life, not a lifetime, and understates it badly — real retention decays with a long
       tail. On a real sample the half-life reading gave 1 month where a fitted model gives
       several.
    2. Real curves are closer to a power law than to exponential decay. A power law has a
       heavier tail and implies a longer lifetime. Exponential fitting is therefore a
       *conservative floor*, and this function says so rather than presenting a point estimate
       as if it were the answer.

    Method: fit exponential decay through the first observed retention point, giving
    lifetime = 1/λ. Report it as a floor and state the method. Where the curve never decays
    (or has fewer than two usable points), refuse to estimate rather than guess.
    """
    points = []
    for row in curve:
        if not isinstance(row, dict):
            continue
        period = row.get("period", row.get("month", row.get("day")))
        value = row.get("retention", row.get("value"))
        if period is None or value is None:
            continue
        try:
            period, value = float(period), float(value)
        except (TypeError, ValueError):
            continue
        if period > 0 and 0 < value < 1:      # period 0 is always 1.0; it carries no decay signal
            points.append((period, value))
    if not points:
        return None, "no decaying retention points (period > 0 with 0 < retention < 1)"

    points.sort()
    period, value = points[0]
    lam = -math.log(value) / period
    if lam <= 1e-9:
        return None, "the curve shows no measurable decay; a lifetime cannot be estimated from it"
    lifetime = 1.0 / lam

    crossed = next((p for p, v in points if v <= floor), None)
    half_life_note = (f"; half-life reading was {max(crossed - 1, 0):g} periods, which understates "
                      f"the lifetime" if crossed else "")
    note = (f"exponential fit through the first decaying point (period {period:g}, "
            f"retention {value:.0%}) gives lambda={lam:.4f}/period and lifetime {lifetime:.1f} "
            f"periods. This is a CONSERVATIVE FLOOR: real retention decays closer to a power law, "
            f"so the true tail is longer{half_life_note}")
    return lifetime, note


def baseline_rate_from_funnel(funnel: dict) -> tuple[float | None, str]:
    """Take the first-step-to-second-step conversion as a testable baseline rate."""
    steps = funnel.get("steps") or funnel.get("result") or []
    if not isinstance(steps, list) or len(steps) < 2:
        return None, "funnel needs at least two steps"
    counts = []
    for step in steps:
        count = step.get("count") if isinstance(step, dict) else None
        if count is None and isinstance(step, dict):
            count = step.get("value")
        counts.append(count)
    if len(counts) < 2 or counts[0] in (None, 0) or counts[1] is None:
        return None, "funnel steps are missing counts, or the first step has no entries"
    return counts[1] / counts[0], f"step 1 -> 2 conversion from a funnel of {len(counts)} steps"


def cohort_size(funnel: dict) -> int | None:
    steps = funnel.get("steps") or funnel.get("result") or []
    if isinstance(steps, list) and steps and isinstance(steps[0], dict):
        count = steps[0].get("count") or steps[0].get("value")
        if isinstance(count, (int, float)):
            return int(count)
    return None


# --------------------------------------------------------------------------- retrieval
def fetch_live(insight_id: str, host: str, api_key: str, project_id: str) -> dict:
    """One read-only GET. Raises on any failure rather than returning a partial result."""
    url = f"{host.rstrip('/')}/api/projects/{project_id}/insights/{insight_id}/"
    request = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "User-Agent": "rebuild-strategist-adapter/1.0",
    })
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        # Fail loudly with the status, never with a substituted value.
        raise SystemExit(f"error: PostHog returned HTTP {exc.code} for insight {insight_id}. "
                         f"No data was substituted.") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"error: could not reach PostHog ({exc.reason}). "
                         f"No data was substituted.") from exc


def build(payload: dict, *, insight_kind: str, system: str, resource: str,
          method: str, status: str) -> dict:
    model: dict = {}
    provenance: list[dict] = []
    missing = list(NOT_AVAILABLE_FROM_POSTHOG)

    if insight_kind == "retention":
        curve = payload.get("result") or payload.get("curve") or []
        months, note = lifetime_from_retention(curve)
        if months is None:
            missing.append(f"retention_months ({note})")
        else:
            model["retention_months"] = months
            provenance.append({"field": "retention_months",
                               "source_field": "result[].retention", "note": note, "grade": "A"})
        size = payload.get("cohort_size")
        if isinstance(size, (int, float)):
            model["available_sample"] = int(size)
            provenance.append({"field": "available_sample", "source_field": "cohort_size",
                               "note": "size of the exposed cohort", "grade": "A"})
        else:
            missing.append("available_sample (cohort size not in the response)")

    elif insight_kind == "funnel":
        rate, note = baseline_rate_from_funnel(payload)
        if rate is None:
            missing.append(f"test_baseline_rate ({note})")
        else:
            model["test_baseline_rate"] = rate
            provenance.append({"field": "test_baseline_rate", "source_field": "result[].count",
                               "note": note, "grade": "A"})
        size = cohort_size(payload)
        if size:
            model["available_sample"] = size
            provenance.append({"field": "available_sample", "source_field": "result[0].count",
                               "note": "entries at the first funnel step", "grade": "A"})
    else:
        raise SystemExit(f"error: unknown insight kind {insight_kind!r}; use 'retention' or 'funnel'")

    return {
        "adapter": f"posthog-{insight_kind}",
        "source": {
            "system": system,
            "resource": resource,
            "retrieved_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
            "method": method,
            "status": status,
        },
        "model": model,
        "provenance": provenance,
        "missing": missing,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--live", action="store_true", help="read the PostHog API")
    mode.add_argument("--offline", metavar="FILE", help="replay a saved JSON response")
    ap.add_argument("--insight", choices=["retention", "funnel"], default="retention")
    ap.add_argument("--insight-id", default=None, help="PostHog insight id (required with --live)")
    ap.add_argument("--host", default=os.environ.get("POSTHOG_HOST", HOST_DEFAULT))
    ap.add_argument("--label", default=None, help="what this resource is, for the provenance record")
    args = ap.parse_args()

    if args.offline:
        if not os.path.exists(args.offline):
            print(f"error: no such file: {args.offline}", file=sys.stderr)
            return 2
        with open(args.offline, encoding="utf-8") as fh:
            try:
                payload = json.load(fh)
            except json.JSONDecodeError as exc:
                print(f"error: {args.offline} is not valid JSON: {exc}", file=sys.stderr)
                return 2
        result = build(payload, insight_kind=args.insight,
                       system="PostHog",
                       resource=args.label or os.path.basename(args.offline),
                       method="replayed saved JSON response",
                       # A replay is not a live read. This adapter will not claim otherwise.
                       status="configured")
    else:
        api_key = os.environ.get("POSTHOG_API_KEY")
        project_id = os.environ.get("POSTHOG_PROJECT_ID")
        if not api_key or not project_id:
            print("error: set POSTHOG_API_KEY and POSTHOG_PROJECT_ID for --live. "
                  "Use --offline with a saved response if you have no key.", file=sys.stderr)
            return 2
        if not args.insight_id:
            print("error: --insight-id is required with --live", file=sys.stderr)
            return 2
        payload = fetch_live(args.insight_id, args.host, api_key, project_id)
        result = build(payload, insight_kind=args.insight,
                       system="PostHog",
                       resource=args.label or f"insight {args.insight_id}",
                       method=f"GET {args.host.rstrip('/')}/api/projects/{project_id}/insights/{args.insight_id}/",
                       # A successful live read evidences `connected`. `tested` and
                       # `production_approved` need more than one read, and a human.
                       status="connected")

    json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    if result["missing"]:
        print(f"note: {len(result['missing'])} field(s) not obtainable from PostHog: "
              f"{', '.join(result['missing'][:4])}"
              f"{' ...' if len(result['missing']) > 4 else ''}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
