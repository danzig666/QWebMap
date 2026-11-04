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
