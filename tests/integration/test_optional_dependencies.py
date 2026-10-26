"""The plugin loads and draws glyphs without scipy and OpenCV (QGIS builds
without them: the QGIS 4.2.3 image rebuilt on Ubuntu 26.04 has no scipy,
and the plugin failed to load: scipy was imported with the glyph module)."""

import os
import subprocess
import sys

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
TESTS = os.path.dirname(HERE)

WITHOUT = """
import sys
sys.modules["scipy"] = None  # import scipy -> ImportError
sys.modules["scipy.ndimage"] = None
sys.modules["cv2"] = None
sys.path.insert(0, {tests!r})
from q2vt_support import register_plugin_package
plugin = register_plugin_package()
from q2vt_plugin.src.core import glyphs_generator as g
import numpy as np
mask = np.ones((20, 30), bool)
mask[0], mask[:, 0] = False, False
d = g._edt(mask)
print("LOADED", round(float(d[19, 29]), 6), flush=True)
import os
os._exit(0)
"""


def test_the_plugin_loads_without_scipy_and_cv2(plugin):
    run = subprocess.run([sys.executable, "-c", WITHOUT.format(tests=TESTS)], capture_output=True,
                         text=True, timeout=300, env={**os.environ, "QT_QPA_PLATFORM": "offscreen"})
    assert run.returncode == 0 and "LOADED" in run.stdout, run.stdout[-2000:] + run.stderr[-3000:]
    assert float(run.stdout.split("LOADED")[1].split()[0]) == pytest.approx(19.0)  # nearest False: the top row


def test_numpy_distance_transform_is_exact(plugin):
    """The fallback gives scipy's exact Euclidean distances."""
    from q2vt_plugin.src.core.glyphs_generator import _edt_numpy  # pylint: disable=import-error
    rng = np.random.default_rng(3)
    for shape in ((24, 24), (37, 61), (120, 90)):
        mask = rng.random(shape) > 0.25
        mask[0] = False
        got = _edt_numpy(mask, chunk_cells=5000)  # several row blocks
        ndimage = pytest.importorskip("scipy.ndimage")
        assert np.abs(got - ndimage.distance_transform_edt(mask)).max() == pytest.approx(0.0, abs=1e-9)
    ring = np.ones((9, 9), bool)
    ring[4, 4] = False
    assert _edt_numpy(ring)[0, 0] == pytest.approx(np.hypot(4, 4))
