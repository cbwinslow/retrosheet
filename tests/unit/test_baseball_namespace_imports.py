"""Tests for baseball top-level namespace import behavior."""

import importlib


def test_import_baseball_without_optional_prediction_dependencies() -> None:
    """Top-level import should not eagerly require heavy ML dependencies."""
    module = importlib.import_module('baseball')
    assert module.__version__ == '0.1.0'


def test_missing_export_raises_attribute_error() -> None:
    """Unknown attributes should raise a standard AttributeError."""
    module = importlib.import_module('baseball')
    try:
        getattr(module, 'DOES_NOT_EXIST')
        raise AssertionError('Expected AttributeError for missing symbol')
    except AttributeError as exc:
        assert 'DOES_NOT_EXIST' in str(exc)
