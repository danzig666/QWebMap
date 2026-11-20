"""PyQGIS integration fixtures: one headless QgsApplication per session."""

import pytest

from q2vt_support import QGIS_AVAILABLE, exit_without_teardown, register_plugin_package

if not QGIS_AVAILABLE:
    collect_ignore_glob = ["test_*.py"]  # pylint: disable=invalid-name
else:
    # Import the plugin before test modules import ``fidelity`` so both
    # resolve to the same module objects.
    register_plugin_package()


@pytest.fixture(scope="session")
def plugin():
    """The plugin root package, imported as ``q2vt_plugin``."""
    return register_plugin_package()


@pytest.fixture(autouse=True)
def _no_blocking_questions(monkeypatch):
    """A question box no test answers (closing a shown window with settings
    that cannot be saved asks first) would wait forever offscreen: Yes.
    Message boxes likewise: Ok. Tests that check one patch it themselves."""
    if QGIS_AVAILABLE:
        from qgis.PyQt.QtWidgets import QMessageBox  # pylint: disable=import-outside-toplevel
        monkeypatch.setattr(QMessageBox, "question",
                            staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes))
        for name in ("warning", "information", "critical"):
            monkeypatch.setattr(QMessageBox, name,
                                staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok))


def pytest_sessionfinish(session, exitstatus):
    session.config._q2vt_exitstatus = int(exitstatus)  # pylint: disable=protected-access


def pytest_unconfigure(config):
    exit_without_teardown(config)
