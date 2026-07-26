from textual import events
from textual.message import Message
from textual.widgets import Input


class TaskLineInput(Input):
    """A single-line text editor for inline Task creation and editing.

    Extends Textual's ``Input`` with two Rook-specific behaviors:
    pasted newlines normalize to spaces instead of truncating to the
    first line (Section 18.6), and Backspace on already-empty content
    is reported rather than silently doing nothing, so the owning
    ``TaskListView`` can cancel an in-progress new Task (Section 9.11).
    """

    class EmptyBackspace(Message):
        """Posted when Backspace is pressed while the value is already empty."""

    def _on_paste(self, event: events.Paste) -> None:
        if not event.text:
            return

        # prevent_default() (not just stop()) is required: Textual calls
        # every class's own _on_paste up the MRO in turn, so without it
        # Input's own _on_paste would also run and insert its unnormalized
        # first-line-only text right after ours.
        event.stop()
        event.prevent_default()

        normalized = " ".join(event.text.split())
        if not normalized:
            return

        selection = self.selection
        if selection.is_empty:
            self.insert_text_at_cursor(normalized)
        else:
            self.replace(normalized, *selection)

    def action_delete_left(self) -> None:
        if not self.value:
            self.post_message(self.EmptyBackspace())
            return
        super().action_delete_left()
