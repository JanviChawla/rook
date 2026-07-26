from dataclasses import dataclass

from textual import events
from textual.widgets import Static


@dataclass(frozen=True, slots=True)
class FooterVariant:
    wide: str
    medium: str
    compact: str


# Section 9.14: the full Today footer, and its progressively shortened forms.
TODAY_FOOTER = FooterVariant(
    wide=(
        "[n] new   [e] edit   [x] complete   [>] migrate   [d] delete   "
        "[u] undo   [r] routine   [a] archive   [?] help   [q] quit"
    ),
    medium=(
        "n new  e edit  x done  > migrate  d delete  u undo  r routine  a archive  ? help  q quit"
    ),
    compact="n  e  x  >  d  u  r  a  ?  q",
)

# Section 10.15: Today's empty state omits keys that act on a Task, since
# none exists yet. The wide/medium/compact tiers follow the same shortening
# pattern as the populated footer.
TODAY_EMPTY_FOOTER = FooterVariant(
    wide="[n] new   [r] routine   [a] archive   [?] help   [q] quit",
    medium="n new  r routine  a archive  ? help  q quit",
    compact="n  r  a  ?  q",
)

# Section 10.7: while creating or editing a Task inline, the footer shows
# only the controls that apply to text entry.
EDITING_FOOTER_TEXT = "[Enter] save   [Esc] cancel"


def select_footer_text(variant: FooterVariant, width: int) -> str:
    """The widest footer tier that fits without wrapping."""
    for candidate in (variant.wide, variant.medium, variant.compact):
        if len(candidate) <= width:
            return candidate
    return variant.compact


class ShortcutFooter(Static):
    """The one-row shortcut footer, responsive to available width."""

    def __init__(self, *, has_tasks: bool, id: str | None = None) -> None:
        # markup=False: the "[key]" hints are literal text, not Rich console
        # markup tags, so brackets like "[n]" must not be parsed as styling.
        super().__init__(id=id, markup=False)
        self._has_tasks = has_tasks
        self._editing = False

    def on_mount(self) -> None:
        self._refresh_content()

    def on_resize(self, event: events.Resize) -> None:
        self._refresh_content()

    def set_editing(self, editing: bool) -> None:
        self._editing = editing
        self._refresh_content()

    def _refresh_content(self) -> None:
        if self._editing:
            self.update(EDITING_FOOTER_TEXT)
            return
        variant = TODAY_FOOTER if self._has_tasks else TODAY_EMPTY_FOOTER
        width = self.size.width or 80
        self.update(select_footer_text(variant, width))
