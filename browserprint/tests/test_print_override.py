"""Unit tests for PrintOverridePanel.get_override()."""

import pytest


@pytest.fixture()
def panel():
    from browserprint.ui.print_override import PrintOverridePanel

    return PrintOverridePanel()


def test_get_override_returns_none_when_switch_is_off(panel) -> None:
    panel._switch.value = False
    panel._input.value = "ZDesigner GK420d"
    assert panel.get_override() is None


def test_get_override_returns_none_when_switch_is_on_but_input_is_empty(panel) -> None:
    panel._switch.value = True
    panel._input.value = ""
    assert panel.get_override() is None


def test_get_override_returns_none_when_switch_is_on_but_input_is_whitespace(
    panel,
) -> None:
    panel._switch.value = True
    panel._input.value = "   "
    assert panel.get_override() is None


def test_get_override_returns_value_when_switch_is_on_and_input_is_filled(
    panel,
) -> None:
    panel._switch.value = True
    panel._input.value = "ZDesigner GK420d"
    assert panel.get_override() == "ZDesigner GK420d"


def test_get_override_strips_whitespace_from_value(panel) -> None:
    panel._switch.value = True
    panel._input.value = "  My Printer  "
    assert panel.get_override() == "My Printer"
