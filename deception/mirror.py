"""
VEILGUARD Deception Engine — Mirror Decoys name generator.

This is the idea that ties the loop together: decoys are shaped BY the
map. Instead of generic honeypots that stand out, VEILGUARD reads the
naming style of your real resources and generates decoy names that
blend in — so an attacker can't tell a trap from a genuine asset.

Strategy (config.DECOY_NAMING):
    mirror = derive names from your real resources' style
    juicy  = use tempting fixed names (prod-db-backup, ...)
    both   = mirror when real resources exist, else juicy
"""

import re
import random


def _tokens(name):
    """Split a resource name into style tokens: separators + words."""
    sep = "-" if "-" in name else ("_" if "_" in name else "-")
    parts = re.split(r"[-_]", name)
    return sep, [p for p in parts if p]


def _infer_style(real_names):
    """
    Look at real resource names and infer the house style:
    the common separator and any shared prefix (e.g. company slug).
    """
    if not real_names:
        return "-", None

    # most common separator
    seps = ["-" if "-" in n else ("_" if "_" in n else "-") for n in real_names]
    sep = max(set(seps), key=seps.count)

    # shared leading token, if most names start the same way (e.g. "acme")
    firsts = []
    for n in real_names:
        _, toks = _tokens(n)
        if toks:
            firsts.append(toks[0])
    prefix = None
    if firsts:
        top = max(set(firsts), key=firsts.count)
        if firsts.count(top) >= max(2, len(firsts) // 2):
            prefix = top
    return sep, prefix


# Bait words that make a decoy irresistible, styled to match real names.
_BAIT = ["backup", "prod", "db", "secrets", "admin", "internal",
         "credentials", "archive", "keys", "export", "config"]


def _mirror_names(real_names, count):
    """Generate decoy names in the same style as the real ones."""
    sep, prefix = _infer_style(real_names)
    out, seen = [], set()
    attempts = 0
    while len(out) < count and attempts < count * 20:
        attempts += 1
        bait = random.sample(_BAIT, k=random.choice([2, 2, 3]))
        parts = ([prefix] if prefix else []) + bait
        name = sep.join(parts)
        if name not in seen:
            seen.add(name)
            out.append(name)
    return out


def generate_decoy_names(real_names, count, naming, juicy_names):
    """
    Return a list of `count` decoy base-names according to the strategy.

    real_names : list of real resource names from the Mapper snapshot
    naming     : "mirror" | "juicy" | "both"
    juicy_names: fallback tempting names
    """
    real_names = [n for n in (real_names or []) if n]

    if naming == "juicy":
        chosen = list(juicy_names)
    elif naming == "mirror":
        chosen = _mirror_names(real_names, count) if real_names else list(juicy_names)
    else:  # both
        chosen = _mirror_names(real_names, count) if real_names else list(juicy_names)

    # pad if we somehow have too few, trim if too many
    pool = list(juicy_names)
    i = 0
    while len(chosen) < count and i < len(pool):
        if pool[i] not in chosen:
            chosen.append(pool[i])
        i += 1
    return chosen[:count]
