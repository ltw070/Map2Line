"""공용 fixture: 합성 이미지(numpy array) 및 샘플 경로 제공."""
import numpy as np
import pytest


@pytest.fixture
def white_bgr_image():
    """흰 배경 BGR 이미지 (100x100)."""
    return np.ones((100, 100, 3), dtype=np.uint8) * 255


@pytest.fixture
def red_dot_image():
    """흰 배경에 붉은 원이 있는 BGR 이미지."""
    img = np.ones((100, 100, 3), dtype=np.uint8) * 255
    import cv2
    cv2.circle(img, (50, 50), 10, (0, 0, 200), -1)
    return img


@pytest.fixture
def sample_dir(tmp_path):
    """임시 샘플 디렉토리 경로."""
    return tmp_path / "samples"


@pytest.fixture
def map_sample_bgr():
    """ref_map/map_sample.png를 BGR ndarray로 반환. 파일 없으면 None."""
    import os
    import cv2
    path = os.path.join(os.path.dirname(__file__), "..", "ref_map", "map_sample.png")
    if not os.path.exists(path):
        return None
    return cv2.imread(path)
