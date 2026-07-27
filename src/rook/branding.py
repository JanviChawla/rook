"""Centralized presentation identity for Rook.

Domain and persistence code must not import this module (see
DEVELOPMENT_GUIDE.md Section 16.22) so branding can change without
touching task-state logic, schema, or tests unrelated to display copy.
"""

import random
from datetime import date

DISPLAY_NAME = "Rook"
ICON = "♖"
FALLBACK_ICON = "R"
CONSOLE_COMMAND = "rook"

# Fallbacks used when the libraries below are empty (Section 18.33).
MASCOT = "‧₊˚ 🖇️✩ ₊˚⊹"
QUOTE = "Let's begin."

_MASCOTS: list[str] = [
    # Face-forward, decorative-framed
    "｡・::・ﾟ★ (｡•̀ᴗ-) ✧.。",
    "˚₊‧꒰ (˶ˆ ᗜ ˆ˵) ꒱‧₊˚",
    "⋆｡°✩ ( ˙▿˙ ) ✩°｡⋆",
    "‧₊˚ ( ◡̈ ) ₊˚‧ ☾",
    "✧・゜: *.(๑˃ᴗ˂)ﾟ・✧",
    "⊹ ˚｡ (づ￣ ³￣)づ ｡˚ ⊹",
    "˖° ┈┈ ( ﾉ^ω^)ﾉ ┈┈ °˖",
    "⋆⁺₊ (｡'▽'｡)♡ ₊⁺⋆",
    "｡:゜(´∀`)゜:｡",
    "⌒°｡(ˊᵕˋ) 。°⌒",
    # Faceless, purely decorative
    "‧₊˚ 🖇️✩ ₊˚⊹",
    "˚₊‧꒰ ☕✨ ꒱‧₊˚",
    "⋆｡°✩ 📖 ⁺˚*•̩̩͙✩.",
    "˚₊‧꒰ა ☕️ ໒꒱‧₊˚",
    "⋆｡°✩ ⁺˚•̩̩͙✩•̩̩͙˚",
    "‧₊˚ 🕯️ ⋆｡˚ ☾",
    "✧˖°⋆ 🧵📌⋆⁺₊",
    "˚ · . 🩶 . · ˚ ⊹",
    "₊˚⊹♡ 🪞 ⊹˚₊",
    "⋆⁺˚｡⋆ 🎀 ⋆｡˚⁺⋆",
    "・゜・.。 🧸 。.・゜・",
    "˖⁺‧₊˚ 📖✨ ˚₊‧⁺˖",
    "⊹˚₊ ‧ 🪄 ‧ ₊˚⊹.",
]

_QUOTES: list[str] = [
    "You are art. You will never be again.",
    "Do the thing, and you shall have the power.",
    "You already survived every day before this one.",
    "Discipline is a mountain of evidence.",
    "You are the proof of your own effort.",
    "Your genius is how everything meets in you.",
    "Showing up is the whole trick.",
]


def pick_for_date(today: date) -> tuple[str, str]:
    """Return (mascot, quote) for the given date, stable within the day.

    Uses the date ordinal as a seed so the pair changes each calendar day
    but never flickers during a session. Mascot and quote are drawn
    independently so every combination is reachable over time.
    """
    rng = random.Random(today.toordinal())
    mascot = rng.choice(_MASCOTS) if _MASCOTS else MASCOT
    quote = rng.choice(_QUOTES) if _QUOTES else QUOTE
    return mascot, quote
