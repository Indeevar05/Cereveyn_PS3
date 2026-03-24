"""Phase 1: environment and test foundation."""

import importlib


def test_dependencies_import():
    """Assert all required libraries import successfully."""
    importlib.import_module("google.genai")
    importlib.import_module("googleapiclient.discovery")
    importlib.import_module("google.auth")
    importlib.import_module("boto3")
    importlib.import_module("pytest")
    importlib.import_module("pytest_mock")
    importlib.import_module("dotenv")


def test_pytest_runs():
    """Sanity check that the test runner executes."""
    assert True is True
