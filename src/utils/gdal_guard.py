"""
gdal_guard.py

The background tile thread (GDALTilesGenerator in a thread) opens and
writes GeoPackages with GDAL in QGIS's own process (field pruning, feature
sizes, merged and grid-cut copies) while the main thread renders raster
layers, zoomed-out images and the terrain, which also run GDAL (in QGIS's
render threads). On QGIS 4 / Windows the two met inside GDAL and QGIS
closed with an access violation (export log: ogr.Open in the tile thread
while raster tiles were rendered).

``shared()``: a stretch of GDAL work in the tile thread (several may run at
once, e.g. merges on several threads). ``exclusive()``: the main thread's
GDAL rendering; it waits until no shared stretch runs and holds new ones
off until it is done. The tiles cut by ogr2ogr (separate processes) go on
meanwhile.
"""

import contextlib
import functools
import threading
import time

_condition = threading.Condition()
_shared = 0
_exclusive = False
_owner = None  # the thread holding exclusive()


@contextlib.contextmanager
def shared():
    """GDAL work of the tile thread: waits while the main thread renders."""
    global _shared  # pylint: disable=global-statement
    if _owner is threading.current_thread():  # inside its own exclusive(): already alone
        yield
        return
    with _condition:
        while _exclusive:
            _condition.wait()
        _shared += 1
    try:
        yield
    finally:
        with _condition:
            _shared -= 1
            _condition.notify_all()


def shared_section(function):
    """``function`` as a shared() stretch."""
    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        with shared():
            return function(*args, **kwargs)
    return wrapper


@contextlib.contextmanager
def exclusive(pump=None):
    """The main thread's GDAL rendering: waits for the tile thread's GDAL
    stretches to end (``pump()`` keeps the window responsive meanwhile) and
    holds new ones off until done."""
    global _exclusive, _owner  # pylint: disable=global-statement
    if _owner is threading.current_thread():  # nested: already held
        yield
        return
    with _condition:
        while _exclusive:  # (one exclusive at a time)
            _condition.wait()
        _exclusive = True
        _owner = threading.current_thread()
    try:
        while True:
            with _condition:
                if not _shared:
                    break
                _condition.wait(0.05)
            if pump is not None:
                pump()
            else:
                time.sleep(0)
        yield
    finally:
        with _condition:
            _exclusive = False
            _owner = None
            _condition.notify_all()
