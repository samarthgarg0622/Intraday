# state.py
# ─────────────────────────────────────────────────────────────
# Saves the night brief's watchlist to disk so the morning job
# can explicitly compare and call out any changes.
# Uses a simple JSON file — no database needed.
# ─────────────────────────────────────────────────────────────

import json
import os
import logging
from datetime import datetime
import pytz

log = logging.getLogger(__name__)

IST          = pytz.timezone("Asia/Kolkata")
STATE_FILE   = "night_state.json"


def _serializable(watchlist: list) -> list:
    """
    Strips non-serializable fields (DataFrame) before saving.
    Only saves what's needed for morning comparison.
    """
    result = []
    for s in watchlist:
        lvl = s["levels"]
        result.append({
            "symbol":       s["symbol"],
            "display":      s["display"],
            "price":        s["price"],
            "change_pct":   s["change_pct"],
            "bias":         s["bias"],
            "setup":        s["setup"],
            "volume_ratio": s["volume_ratio"],
            "levels": {
                "pdh":                lvl["pdh"],
                "pdl":                lvl["pdl"],
                "ema":                lvl["ema"],
                "above_ema":          lvl["above_ema"],
                "nearest_support":    lvl["nearest_support"],
                "nearest_resistance": lvl["nearest_resistance"],
                "supports":           lvl["supports"],
                "resistances":        lvl["resistances"],
            },
        })
    return result


def save_night_state(watchlist: list) -> bool:
    """Saves tonight's watchlist to disk for morning comparison."""
    try:
        state = {
            "saved_at": datetime.now(IST).isoformat(),
            "watchlist": _serializable(watchlist),
        }
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
        log.info(f"Night state saved: {len(watchlist)} stocks → {STATE_FILE}")
        return True
    except Exception as e:
        log.error(f"Failed to save night state: {e}")
        return False


def load_night_state() -> dict | None:
    """
    Loads last night's saved watchlist.
    Returns None if file doesn't exist or is from a different day.
    """
    try:
        if not os.path.exists(STATE_FILE):
            log.warning("No night state file found — first run?")
            return None

        with open(STATE_FILE, "r") as f:
            state = json.load(f)

        # Verify it's from today or yesterday (not stale)
        saved_at = datetime.fromisoformat(state["saved_at"])
        now_ist  = datetime.now(IST)

        # Allow up to 18 hours old (night job at 8PM → morning job at 8:45AM = ~13hr gap)
        age_hours = (now_ist - saved_at).total_seconds() / 3600
        if age_hours > 18:
            log.warning(f"Night state is {age_hours:.1f}h old — too stale, ignoring")
            return None

        log.info(f"Loaded night state: {len(state['watchlist'])} stocks, saved {age_hours:.1f}h ago")
        return state

    except Exception as e:
        log.error(f"Failed to load night state: {e}")
        return None


def compare_watchlists(night_state: dict, morning_watchlist: list) -> dict:
    """
    Compares night watchlist with morning re-check.
    Returns a comparison dict highlighting changes.
    """
    night_list  = night_state["watchlist"]
    night_syms  = {s["symbol"]: s for s in night_list}
    morn_syms   = {s["symbol"]: s for s in morning_watchlist}

    # Stocks that were in night brief
    still_valid   = []   # Same stock, setup still good
    levels_changed = []  # Same stock, key levels shifted
    bias_changed   = []  # Same stock, bias flipped
    dropped        = []  # Was in night brief, no longer qualifies
    new_additions  = []  # Wasn't in night brief, now qualifies

    for sym, night in night_syms.items():
        if sym not in morn_syms:
            dropped.append(night["display"])
            continue

        morn = morn_syms[sym]
        changes = []

        # Check bias change
        if morn["bias"] != night["bias"]:
            bias_changed.append({
                "display":    night["display"],
                "was":        night["bias"],
                "now":        morn["bias"],
            })
            continue

        # Check level drift (>0.5% shift in nearest S/R)
        nl = night["levels"]
        ml = morn["levels"]

        if nl["nearest_resistance"] and ml["nearest_resistance"]:
            res_drift = abs(ml["nearest_resistance"] - nl["nearest_resistance"]) / nl["nearest_resistance"] * 100
            if res_drift > 0.5:
                changes.append(f"Resistance: ₹{nl['nearest_resistance']} → ₹{ml['nearest_resistance']}")

        if nl["nearest_support"] and ml["nearest_support"]:
            sup_drift = abs(ml["nearest_support"] - nl["nearest_support"]) / nl["nearest_support"] * 100
            if sup_drift > 0.5:
                changes.append(f"Support: ₹{nl['nearest_support']} → ₹{ml['nearest_support']}")

        if nl["above_ema"] != ml["above_ema"]:
            changes.append(f"EMA side flipped → price now {'above' if ml['above_ema'] else 'below'} EMA")

        if changes:
            levels_changed.append({"display": night["display"], "changes": changes})
        else:
            still_valid.append(night["display"])

    for sym, morn in morn_syms.items():
        if sym not in night_syms:
            new_additions.append(morn["display"])

    return {
        "still_valid":    still_valid,
        "levels_changed": levels_changed,
        "bias_changed":   bias_changed,
        "dropped":        dropped,
        "new_additions":  new_additions,
    }
