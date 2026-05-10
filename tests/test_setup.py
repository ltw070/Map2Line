"""Task 1-1 환경 설정 검증 테스트.

Red 단계: src 패키지 import 및 conftest fixture 동작을 검증한다.
"""
import importlib


def test_src_package_importable():
    """src 패키지를 import할 수 있어야 한다."""
    mod = importlib.import_module("src")
    assert mod is not None


def test_src_preprocessing_importable():
    """src.preprocessing 패키지를 import할 수 있어야 한다."""
    mod = importlib.import_module("src.preprocessing")
    assert mod is not None


def test_src_matching_importable():
    """src.matching 패키지를 import할 수 있어야 한다."""
    mod = importlib.import_module("src.matching")
    assert mod is not None


def test_src_ocr_importable():
    """src.ocr 패키지를 import할 수 있어야 한다."""
    mod = importlib.import_module("src.ocr")
    assert mod is not None


def test_src_api_importable():
    """src.api 패키지를 import할 수 있어야 한다."""
    mod = importlib.import_module("src.api")
    assert mod is not None


def test_white_bgr_image_fixture(white_bgr_image):
    """white_bgr_image fixture는 shape (100, 100, 3)이어야 한다."""
    assert white_bgr_image.shape == (100, 100, 3)


def test_white_bgr_image_all_white(white_bgr_image):
    """white_bgr_image는 모든 픽셀이 255이어야 한다."""
    assert (white_bgr_image == 255).all()


def test_red_dot_image_fixture(red_dot_image):
    """red_dot_image fixture는 shape (100, 100, 3)이어야 한다."""
    assert red_dot_image.shape == (100, 100, 3)


def test_red_dot_image_has_red_pixels(red_dot_image):
    """red_dot_image는 붉은 픽셀(B=0, G=0, R≥200)을 포함해야 한다."""
    red_pixels = (
        (red_dot_image[:, :, 2] >= 200)
        & (red_dot_image[:, :, 1] == 0)
        & (red_dot_image[:, :, 0] == 0)
    )
    assert red_pixels.any()


def test_sample_dir_fixture(sample_dir):
    """sample_dir fixture는 유효한 Path 객체이어야 한다."""
    from pathlib import Path
    assert isinstance(sample_dir, Path)
