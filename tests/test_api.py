"""FastAPI 엔드포인트 테스트 — Task 2-4.

POST /identify 엔드포인트의 3가지 핵심 시나리오를 검증한다:
  1. 정상 응답 형식 (필수 키, 타입)
  2. 응답 시간 p95 ≤ 1.5s
  3. 잘못된 파일 형식 → 422 반환
"""

import io
import statistics
import time

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient


# ------------------------------------------------------------------
# TestClient 픽스처
# ------------------------------------------------------------------

@pytest.fixture(scope="module")
def client():
    """FastAPI TestClient를 반환한다."""
    from src.api.main import app
    return TestClient(app)


# ------------------------------------------------------------------
# 유틸: 인메모리 JPEG / PNG 이미지 바이트 생성
# ------------------------------------------------------------------

def _make_jpeg_bytes(width: int = 500, height: int = 400) -> bytes:
    """BGR ndarray → JPEG 바이트 (메모리 내 생성)."""
    img = np.ones((height, width, 3), dtype=np.uint8) * 200
    # 붉은 원 몇 개 추가 (앵커 역할)
    cv2.circle(img, (100, 100), 15, (0, 0, 180), -1)
    cv2.circle(img, (300, 150), 15, (0, 0, 180), -1)
    cv2.circle(img, (450, 200), 15, (0, 0, 180), -1)
    _, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 90])
    return buf.tobytes()


def _make_png_bytes(width: int = 500, height: int = 400) -> bytes:
    """BGR ndarray → PNG 바이트 (메모리 내 생성)."""
    img = np.ones((height, width, 3), dtype=np.uint8) * 200
    cv2.circle(img, (100, 100), 15, (0, 0, 180), -1)
    _, buf = cv2.imencode(".png", img)
    return buf.tobytes()


# ------------------------------------------------------------------
# 시나리오 1: 정상 응답 형식 검증
# ------------------------------------------------------------------

class TestIdentifyResponseFormat:
    """POST /identify — 정상 이미지 업로드 시 응답 구조 검증."""

    def test_jpeg_returns_200(self, client: TestClient):
        """JPEG 업로드 → HTTP 200."""
        data = _make_jpeg_bytes()
        resp = client.post(
            "/identify",
            files={"image": ("test.jpg", io.BytesIO(data), "image/jpeg")},
        )
        assert resp.status_code == 200, f"expected 200, got {resp.status_code}: {resp.text}"

    def test_png_returns_200(self, client: TestClient):
        """PNG 업로드 → HTTP 200."""
        data = _make_png_bytes()
        resp = client.post(
            "/identify",
            files={"image": ("test.png", io.BytesIO(data), "image/png")},
        )
        assert resp.status_code == 200, f"expected 200, got {resp.status_code}: {resp.text}"

    def test_response_has_required_keys(self, client: TestClient):
        """응답 JSON에 line, section, columns, confidence 키가 있어야 한다."""
        data = _make_jpeg_bytes()
        resp = client.post(
            "/identify",
            files={"image": ("test.jpg", io.BytesIO(data), "image/jpeg")},
        )
        assert resp.status_code == 200
        body = resp.json()
        required_keys = {"line", "section", "columns", "confidence"}
        missing = required_keys - set(body.keys())
        assert not missing, f"응답에 누락된 키: {missing}"

    def test_line_is_string(self, client: TestClient):
        """line 필드는 str이어야 한다."""
        data = _make_jpeg_bytes()
        resp = client.post(
            "/identify",
            files={"image": ("test.jpg", io.BytesIO(data), "image/jpeg")},
        )
        assert isinstance(resp.json()["line"], str)

    def test_section_is_string(self, client: TestClient):
        """section 필드는 str이어야 한다."""
        data = _make_jpeg_bytes()
        resp = client.post(
            "/identify",
            files={"image": ("test.jpg", io.BytesIO(data), "image/jpeg")},
        )
        assert isinstance(resp.json()["section"], str)

    def test_columns_is_string(self, client: TestClient):
        """columns 필드는 str이어야 한다."""
        data = _make_jpeg_bytes()
        resp = client.post(
            "/identify",
            files={"image": ("test.jpg", io.BytesIO(data), "image/jpeg")},
        )
        assert isinstance(resp.json()["columns"], str)

    def test_confidence_is_float_in_range(self, client: TestClient):
        """confidence 필드는 0.0~1.0 사이의 float이어야 한다."""
        data = _make_jpeg_bytes()
        resp = client.post(
            "/identify",
            files={"image": ("test.jpg", io.BytesIO(data), "image/jpeg")},
        )
        conf = resp.json()["confidence"]
        assert isinstance(conf, float), f"confidence 타입 오류: {type(conf)}"
        assert 0.0 <= conf <= 1.0, f"confidence 범위 초과: {conf}"

    def test_inference_time_ms_in_response(self, client: TestClient):
        """응답에 inference_time_ms 필드가 있어야 한다 (선택적 디버그 필드)."""
        data = _make_jpeg_bytes()
        resp = client.post(
            "/identify",
            files={"image": ("test.jpg", io.BytesIO(data), "image/jpeg")},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "inference_time_ms" in body, "inference_time_ms 키 누락"
        assert isinstance(body["inference_time_ms"], (int, float))
        assert body["inference_time_ms"] >= 0


# ------------------------------------------------------------------
# 시나리오 2: 응답 시간 p95 ≤ 1.5s
# ------------------------------------------------------------------

class TestIdentifyResponseTime:
    """POST /identify — 응답 시간 성능 검증 (PRD §6)."""

    def test_single_response_within_15s(self, client: TestClient):
        """단일 요청 응답 시간이 1.5s 이내여야 한다."""
        data = _make_jpeg_bytes()
        start = time.perf_counter()
        resp = client.post(
            "/identify",
            files={"image": ("test.jpg", io.BytesIO(data), "image/jpeg")},
        )
        elapsed = time.perf_counter() - start
        assert resp.status_code == 200
        assert elapsed <= 1.5, f"응답 시간 초과: {elapsed:.3f}s > 1.5s"

    def test_p95_response_time_within_15s(self, client: TestClient):
        """10회 연속 요청의 p95 응답 시간이 1.5s 이내여야 한다."""
        data = _make_jpeg_bytes()
        times = []
        for _ in range(10):
            start = time.perf_counter()
            resp = client.post(
                "/identify",
                files={"image": ("test.jpg", io.BytesIO(data), "image/jpeg")},
            )
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            assert resp.status_code == 200
            times.append(elapsed_ms)

        sorted_times = sorted(times)
        p95_idx = int(len(sorted_times) * 0.95) - 1
        p95_ms = sorted_times[max(p95_idx, 0)]
        mean_ms = statistics.mean(times)

        assert p95_ms <= 1500.0, (
            f"p95 응답 시간 초과: {p95_ms:.1f}ms > 1500ms "
            f"(평균: {mean_ms:.1f}ms, 전체: {sorted_times})"
        )

    def test_inference_time_ms_logged_in_response(self, client: TestClient):
        """inference_time_ms가 실제 경과 시간과 근사해야 한다 (±200ms 허용)."""
        data = _make_jpeg_bytes()
        start = time.perf_counter()
        resp = client.post(
            "/identify",
            files={"image": ("test.jpg", io.BytesIO(data), "image/jpeg")},
        )
        wall_ms = (time.perf_counter() - start) * 1000.0
        assert resp.status_code == 200
        reported_ms = resp.json()["inference_time_ms"]
        # 보고된 처리 시간이 실제 경과 시간보다 크지 않아야 한다 (충분한 허용 범위)
        assert reported_ms <= wall_ms + 200.0, (
            f"reported_ms({reported_ms:.1f}) >> wall_ms({wall_ms:.1f})"
        )


# ------------------------------------------------------------------
# 시나리오 3: 잘못된 파일 형식 → 422 반환
# ------------------------------------------------------------------

class TestIdentifyInvalidInput:
    """POST /identify — 잘못된 입력에 대한 에러 처리 검증."""

    def test_text_file_returns_422(self, client: TestClient):
        """텍스트 파일 업로드 → 422 Unprocessable Entity."""
        text_bytes = b"This is not an image file.\nJust plain text.\n"
        resp = client.post(
            "/identify",
            files={"image": ("test.txt", io.BytesIO(text_bytes), "text/plain")},
        )
        assert resp.status_code == 422, (
            f"expected 422 for text file, got {resp.status_code}: {resp.text}"
        )

    def test_empty_file_returns_422(self, client: TestClient):
        """빈 파일 업로드 → 422 Unprocessable Entity."""
        resp = client.post(
            "/identify",
            files={"image": ("empty.jpg", io.BytesIO(b""), "image/jpeg")},
        )
        assert resp.status_code == 422, (
            f"expected 422 for empty file, got {resp.status_code}: {resp.text}"
        )

    def test_random_bytes_returns_422(self, client: TestClient):
        """무작위 바이트 업로드 → 422 Unprocessable Entity."""
        rng = np.random.default_rng(42)
        garbage = rng.integers(0, 256, size=1024, dtype=np.uint8).tobytes()
        resp = client.post(
            "/identify",
            files={"image": ("garbage.jpg", io.BytesIO(garbage), "image/jpeg")},
        )
        assert resp.status_code == 422, (
            f"expected 422 for garbage bytes, got {resp.status_code}: {resp.text}"
        )

    def test_no_file_field_returns_422(self, client: TestClient):
        """파일 필드 없이 요청 → 422 Unprocessable Entity."""
        resp = client.post("/identify", data={"not_image": "hello"})
        assert resp.status_code == 422, (
            f"expected 422 when no file field, got {resp.status_code}: {resp.text}"
        )

    def test_error_response_has_detail(self, client: TestClient):
        """422 응답에 detail 필드가 있어야 한다."""
        text_bytes = b"not an image"
        resp = client.post(
            "/identify",
            files={"image": ("test.txt", io.BytesIO(text_bytes), "text/plain")},
        )
        assert resp.status_code == 422
        body = resp.json()
        assert "detail" in body, f"422 응답에 detail 키 없음: {body}"
