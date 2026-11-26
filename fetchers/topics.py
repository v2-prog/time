"""Topic tags derived from a record's text.

Tags are coarse categories (e.g. "quarterly_report", "firb"), not text. For ASX
records they are computed from the headline in memory before the headline is
withheld, so the engine can match on them without republishing headlines.
"""
import re

TOPIC_RULES = [
    ("quarterly_report", r"quarterly|operational review|activities report|appendix 4c|appendix 5b|production report"),
    ("periodic_report", r"annual report|half[- ]year|full[- ]year|results|appendix 4[de]|financial report"),
    ("offtake", r"offtake|off-take|supply agreement|sales agreement|binding term sheet"),
    ("pricing_contract", r"sales contract|price index|pricing|negotiation"),
    ("approval", r"approv|permit|licen[cs]e grant|environmental|epbc|mining lease|grant of"),
    ("firb", r"\bfirb\b|foreign investment|disposal order|treasurer|foreign acquisitions"),
    ("china_trade", r"china|chinese|cmrg|mofcom|tariff|anti-dumping|customs"),
    ("export_controls", r"export control|export licen|export restriction"),
    ("rare_earths", r"rare earth|ndpr|dysprosium|terbium|heavy rare|magnet"),
    ("iron_ore", r"iron ore|pilbara|jimblebar|fines"),
    ("coal", r"\bcoal\b|coking|thermal coal|met coal"),
    ("lithium", r"lithium|spodumene"),
    ("capital_raising", r"placement|entitlement offer|capital raising|share purchase plan|\bspp\b"),
    ("funding", r"loan|debt facility|export finance|naif|critical minerals facility|grant funding"),
    ("guidance", r"guidance|outlook|update to market"),
    ("investor_event", r"investor|site tour|presentation|briefing|webcast|address"),
    # routine filings: never matched on their own
    ("routine", r"director'?s interest|substantial holder|cessation of securities|quotation of securities|"
                r"unquoted securities|dividend|buy-?back|notice of (annual )?general meeting|results of meeting|"
                r"change of (company secretary|director)|cleansing|appendix 2a|appendix 3[a-z]|proxy form|"
                r"issued capital|constitution|daily share buy-back"),
]
_COMPILED = [(t, re.compile(p, re.I)) for t, p in TOPIC_RULES]
ROUTINE = {"routine"}


def topics_for(*texts):
    text = " ".join(t for t in texts if t)
    return sorted({t for t, rx in _COMPILED if rx.search(text)})
