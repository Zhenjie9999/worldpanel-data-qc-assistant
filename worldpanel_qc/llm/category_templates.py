from __future__ import annotations


CATEGORY_TEMPLATES = {
    "general_fmcg": {
        "label": "General FMCG",
        "guidance": "Check penetration, frequency, volume, price, spend, promotions, units, and peer consistency.",
    },
    "fresh_produce": {
        "label": "Fresh Produce",
        "guidance": "Check seasonality, price volatility, product naming, units, supply-driven jumps, and extreme product-level values.",
    },
    "beverages": {
        "label": "Beverages",
        "guidance": "Check pack-size mix, promotions, and price-per-volume consistency.",
    },
    "dairy": {
        "label": "Dairy",
        "guidance": "Check pack-size mix, chilled shelf-life effects, promotions, household penetration, and price-per-volume consistency.",
    },
    "personal_care": {
        "label": "Personal Care",
        "guidance": "Check premiumization, pack-count units, purchase frequency, promotion effects, and product-level price dispersion.",
    },
}


def category_guidance(category_template: str) -> str:
    return CATEGORY_TEMPLATES.get(category_template, CATEGORY_TEMPLATES["general_fmcg"])["guidance"]


def validate_category_template(category_template: str) -> str:
    value = str(category_template or "general_fmcg").strip()
    if value not in CATEGORY_TEMPLATES:
        raise ValueError(f"Unknown category template: {value}")
    return value

