"""Centralized presentation identity for Rook.

Domain and persistence code must not import this module (see
DEVELOPMENT_GUIDE.md Section 16.22) so branding can change without
touching task-state logic, schema, or tests unrelated to display copy.
"""

DISPLAY_NAME = "Rook"
ICON = "♖"
FALLBACK_ICON = "R"
CONSOLE_COMMAND = "rook"

# Static placeholder content for Phase 1 only. The full quote/mascot
# library and mood-based selection logic (Section 14) arrive in a later
# phase; this single pair is deliberately fixed for now.
MASCOT = "‧₊˚🖇️✩ ₊˚🎧⊹♡"
QUOTE = "Let's begin."
