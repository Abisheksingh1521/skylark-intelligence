"""
Canonical Field Mappings & Domain Enumerations for Skylark Intelligence.
"""

# Canonical Sector Names
CANONICAL_SECTORS = {
    "mining": "Mining",
    "renewables": "Renewables",
    "powerline": "Powerline",
    "railways": "Railways",
    "construction": "Construction",
    "highways": "Highways",
    "dsp": "DSP",
    "tender": "Tender",
    "manufacturing": "Manufacturing",
    "aviation": "Aviation",
    "security and surveillance": "Security and Surveillance",
    "others": "Others",
    "other": "Others",
}

# Closure Probability Mappings (Correction 1: Missing = None, NOT 0.0)
CLOSURE_PROBABILITY_MAP = {
    "high": 0.75,
    "medium": 0.50,
    "low": 0.25,
}

# Deal Status Standard Mapping
DEAL_STATUS_MAP = {
    "won": "Won",
    "open": "Open",
    "dead": "Dead",
    "lost": "Dead",
    "on hold": "On Hold",
}

# Work Order Execution Status Standard Mapping
EXECUTION_STATUS_MAP = {
    "completed": "Completed",
    "ongoing": "Ongoing",
    "executed until current month": "Ongoing",
    "not started": "Not Started",
    "pause / struck": "Paused",
    "pause/struck": "Paused",
    "partial completed": "Ongoing",
    "details pending from client": "Not Started",
}
