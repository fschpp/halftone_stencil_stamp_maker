import os
import sys

import numpy as np
import pytest
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def photo(tmp_path):
    h, w = 200, 400
    yy, xx = np.mgrid[0:h, 0:w]
    img = np.zeros((h, w, 3), dtype=np.uint8)
    img[..., 0] = xx / w * 255
    img[..., 1] = yy / h * 255
    img[..., 2] = 255 - xx / w * 200
    img[np.hypot(xx - 280, yy - 100) < 60] = (230, 40, 40)
    path = tmp_path / "foto.png"
    Image.fromarray(img).save(path)
    return str(path)
