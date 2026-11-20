"""gdal_guard: the background tile thread's GDAL work (shared, several at
once) and the main thread's GDAL rendering (exclusive) never overlap
(QGIS 4 on Windows crashed with an access violation when they did)."""

import threading
import time

from utils import gdal_guard


def test_shared_stretches_run_together_and_exclusive_waits_for_them():
    events = []
    inside = threading.Barrier(3)

    def tile_work(name):
        with gdal_guard.shared():
            inside.wait(timeout=5)       # both shared stretches at once
            time.sleep(0.2)
            events.append(f"{name} done")

    workers = [threading.Thread(target=tile_work, args=(n,)) for n in ("a", "b")]
    for worker in workers:
        worker.start()
    inside.wait(timeout=5)
    pumped = []
    with gdal_guard.exclusive(lambda: pumped.append(1)):
        events.append("render")         # only after both have ended
    for worker in workers:
        worker.join()
    assert events[-1] == "render" and set(events[:2]) == {"a done", "b done"}
    assert pumped                        # the window kept being served while waiting


def test_shared_waits_while_the_main_thread_renders():
    events = []
    started = threading.Event()

    def tile_work():
        started.set()
        with gdal_guard.shared():
            events.append("tile")

    with gdal_guard.exclusive():
        worker = threading.Thread(target=tile_work)
        worker.start()
        started.wait(timeout=5)
        time.sleep(0.2)
        events.append("render")
        # The holder itself may use shared() code (nested): no deadlock.
        with gdal_guard.shared():
            events.append("nested")
    worker.join(timeout=5)
    assert events == ["render", "nested", "tile"]


def test_shared_section_decorator():
    @gdal_guard.shared_section
    def work(value):
        return value * 2
    assert work(21) == 42


def test_helper_start_up_errors_go_into_the_export_log(tmp_path):
    """Helpers that do not start: the end of their own logs (a DLL that QGIS 4's
    Python cannot load...) is added to the export log line that says so."""
    import export_workers  # pylint: disable=import-outside-toplevel
    (tmp_path / "worker_0.log").write_bytes(b"Traceback ...\nImportError: DLL load failed while importing _core\n")
    (tmp_path / "worker_1.log").write_bytes(b"")
    text = export_workers.startup_errors(str(tmp_path))
    assert "worker 0 log:" in text and "DLL load failed" in text and "worker 1" not in text
    assert export_workers.startup_errors(str(tmp_path / "missing")) == ""


def test_helpers_accept_qt_date_and_colour_variables():
    """A project variable holding a QDateTime (@project_creation_date) or a
    QColor reaches the helpers on QGIS 3 (PyQt5: through sip) and on QGIS 4
    (PyQt6: the class itself); other classes are still refused."""
    import io  # pylint: disable=import-outside-toplevel
    import pickle  # pylint: disable=import-outside-toplevel
    import pytest  # pylint: disable=import-outside-toplevel
    import export_workers  # pylint: disable=import-outside-toplevel
    from qgis.PyQt.QtCore import QDateTime  # pylint: disable=import-outside-toplevel
    from qgis.PyQt.QtGui import QColor  # pylint: disable=import-outside-toplevel
    stream = io.BytesIO()
    export_workers.send(stream, ("init", {"when": QDateTime(2026, 11, 5, 7, 2), "colour": QColor(10, 20, 30)}))
    stream.seek(0)
    message = export_workers.receive(stream)
    assert message[1]["when"] == QDateTime(2026, 11, 5, 7, 2) and message[1]["colour"] == QColor(10, 20, 30)
    unpickler = export_workers._Unpickler(io.BytesIO(b""))  # pylint: disable=protected-access
    for package in ("PyQt5", "PyQt6"):
        try:
            assert unpickler.find_class(f"{package}.QtCore", "QDateTime").__name__ == "QDateTime"
        except ImportError:
            pass  # that PyQt is not installed here: its name was allowed
        with pytest.raises(pickle.UnpicklingError):
            unpickler.find_class(f"{package}.QtCore", "QProcess")
    with pytest.raises(pickle.UnpicklingError):
        unpickler.find_class("os", "system")


def test_nested_shared_does_not_deadlock_with_a_pending_exclusive():
    """A shared stretch calling shared() code (_size_range -> _dataset_table)
    while the main thread waits in exclusive(): both finish."""
    inside, pending = threading.Event(), threading.Event()
    events = []

    def tile_work():
        with gdal_guard.shared():
            inside.set()
            pending.wait(timeout=5)
            time.sleep(0.2)             # exclusive() is waiting for this stretch
            with gdal_guard.shared():
                events.append("nested")
        events.append("tile")

    worker = threading.Thread(target=tile_work, daemon=True)  # (a deadlock fails, not hangs)
    worker.start()
    inside.wait(timeout=5)
    pending.set()
    done = threading.Event()

    def render():
        with gdal_guard.exclusive():
            events.append("render")
        done.set()

    main = threading.Thread(target=render, daemon=True)
    main.start()
    worker.join(timeout=3)
    assert done.wait(timeout=3) and not worker.is_alive()
    assert events == ["nested", "tile", "render"]


def test_waiting_for_helpers_keeps_the_window_served(monkeypatch):
    """Helpers take seconds to start QGIS: wait_ready runs on QGIS's main
    thread, which kept no events served (Not Responding, Cancel unseen)."""
    import queue  # pylint: disable=import-outside-toplevel
    import export_workers  # pylint: disable=import-outside-toplevel
    monkeypatch.setattr(export_workers, "_READY_TIMEOUT_S", 0.5)
    pool = object.__new__(export_workers.WorkerPool)
    pool.workers, pool.alive, pool.error, pool.results = [None], [True], "", queue.Queue()
    pumped = []
    assert pool.wait_ready("3.44", lambda: False, lambda: pumped.append(1)) == []
    assert len(pumped) >= 2 and pool.alive == [False]


def test_a_helper_sending_what_cannot_be_read_is_stopped():
    """A message the main process refuses: the helper is stopped before its
    work is done here (else both wrote the same GeoPackages)."""
    import queue  # pylint: disable=import-outside-toplevel
    import subprocess  # pylint: disable=import-outside-toplevel
    import sys  # pylint: disable=import-outside-toplevel
    import export_workers  # pylint: disable=import-outside-toplevel
    script = ("import pickle, struct, sys, time, os\n"
              "data = pickle.dumps(('base-done', os.system))\n"
              "sys.stdout.buffer.write(struct.pack('<Q', len(data)) + data); sys.stdout.buffer.flush()\n"
              "time.sleep(60)\n")
    process = subprocess.Popen([sys.executable, "-c", script], stdout=subprocess.PIPE)  # pylint: disable=consider-using-with
    try:
        pool = object.__new__(export_workers.WorkerPool)
        pool.results = queue.Queue()
        pool._read(0, process)  # pylint: disable=protected-access
        number, message = pool.results.get(timeout=1)
        assert number == 0 and message[0] == "exit"
        assert process.poll() is not None  # stopped, not left writing
    finally:
        if process.poll() is None:
            process.kill()
        process.wait()
        process.stdout.close()
