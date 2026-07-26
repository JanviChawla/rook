from rook.widgets.shortcut_footer import TODAY_EMPTY_FOOTER, TODAY_FOOTER, select_footer_text


def test_wide_variant_used_when_it_fits() -> None:
    text = select_footer_text(TODAY_FOOTER, width=len(TODAY_FOOTER.wide))
    assert text == TODAY_FOOTER.wide


def test_medium_variant_used_when_wide_does_not_fit() -> None:
    text = select_footer_text(TODAY_FOOTER, width=len(TODAY_FOOTER.medium))
    assert text == TODAY_FOOTER.medium


def test_compact_variant_used_when_nothing_else_fits() -> None:
    text = select_footer_text(TODAY_FOOTER, width=len(TODAY_FOOTER.compact))
    assert text == TODAY_FOOTER.compact


def test_compact_variant_is_the_floor_even_below_minimum_width() -> None:
    text = select_footer_text(TODAY_FOOTER, width=1)
    assert text == TODAY_FOOTER.compact


def test_empty_footer_variants_never_wrap_either() -> None:
    text = select_footer_text(TODAY_EMPTY_FOOTER, width=len(TODAY_EMPTY_FOOTER.compact))
    assert text == TODAY_EMPTY_FOOTER.compact
