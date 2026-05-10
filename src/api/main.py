"""FastAPI 엔드포인트 — Task 2-4.

POST /identify: 도면 이미지를 업로드하면 라인·구역을 식별한다.
Coarse → Fine → OCR 전체 파이프라인을 통합한다.

사용 예:
    uvicorn src.api.main:app --reload
    curl -F "image=@sample.jpg" http://localhost:8000/identify
"""
from __future__ import annotations

import io
import time
from typing import Any, Dict

import cv2
import numpy as np
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse

from src.matching.coarse_matcher import coarse_matcher
from src.matching.fine_matcher import fine_matcher
from src.ocr.column_reader import verify_with_ocr

# --- 상수 ---
_ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/jpg"}
_ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
_MAX_IMAGE_BYTES: int = 20 * 1024 * 1024  # 20 MB

app = FastAPI(
    title="Map2Line Identification Engine",
    description="반도체 공장 도면 이미지에서 라인·구역을 자동 식별합니다.",
    version="0.2.4",
)


@app.post("/identify")
async def identify(image: UploadFile = File(...)) -> JSONResponse:
    """도면 이미지를 업로드하면 라인·구역을 식별한다.

    Args:
        image: multipart/form-data로 전달된 이미지 파일 (JPEG 또는 PNG).

    Returns:
        JSON:
        {
            "line": str,              # 식별된 라인명 (예: "Line_A_1")
            "section": str,           # 구역 번호 (예: "102")
            "columns": str,           # 기둥 범위 (예: "B4-B6")
            "confidence": float,      # 신뢰도 (0.0~1.0)
            "inference_time_ms": float  # 처리 시간 (ms)
        }

    Raises:
        422 Unprocessable Entity:
            - 파일이 JPEG/PNG가 아닌 경우
            - 파일 내용이 빈 경우
            - 이미지 디코딩에 실패한 경우
    """
    pipeline_start = time.perf_counter()

    # 1. 파일 형식 검증
    validation_error = _validate_upload(image)
    if validation_error:
        return JSONResponse(
            status_code=422,
            content={"detail": validation_error},
        )

    # 2. 파일 내용 읽기
    raw_bytes = await image.read()
    if not raw_bytes:
        return JSONResponse(
            status_code=422,
            content={"detail": "업로드된 파일이 비어 있습니다."},
        )

    # 3. BGR ndarray 디코딩
    bgr_image = _decode_image(raw_bytes)
    if bgr_image is None:
        return JSONResponse(
            status_code=422,
            content={"detail": "이미지 디코딩에 실패했습니다. 유효한 JPEG/PNG 파일을 업로드하세요."},
        )

    # 4. 파이프라인 실행: Coarse → Fine → OCR
    result = _run_pipeline(bgr_image)
    result["inference_time_ms"] = round(
        (time.perf_counter() - pipeline_start) * 1000.0, 2
    )

    return JSONResponse(status_code=200, content=result)


# ---------------------------------------------------------------------------
# 내부 헬퍼
# ---------------------------------------------------------------------------

def _validate_upload(upload: UploadFile) -> str:
    """업로드 파일의 형식을 검증한다.

    Args:
        upload: FastAPI UploadFile 객체.

    Returns:
        오류 메시지 문자열. 유효하면 빈 문자열 반환.
    """
    # Content-Type 검사
    content_type = (upload.content_type or "").lower().split(";")[0].strip()
    if content_type and content_type not in _ALLOWED_CONTENT_TYPES:
        return (
            f"지원하지 않는 파일 형식입니다: '{content_type}'. "
            "JPEG 또는 PNG 이미지를 업로드하세요."
        )

    # 파일명 확장자 검사 (content_type이 없거나 octet-stream인 경우 보조 수단)
    filename = (upload.filename or "").lower()
    if filename:
        ext = "." + filename.rsplit(".", 1)[-1] if "." in filename else ""
        if ext and ext not in _ALLOWED_EXTENSIONS:
            return (
                f"지원하지 않는 파일 확장자입니다: '{ext}'. "
                ".jpg / .jpeg / .png 파일을 업로드하세요."
            )

    return ""


def _decode_image(raw_bytes: bytes) -> "np.ndarray | None":
    """바이트 배열을 BGR ndarray로 디코딩한다.

    Args:
        raw_bytes: 이미지 파일 원본 바이트.

    Returns:
        BGR ndarray (H, W, 3) 또는 디코딩 실패 시 None.
    """
    try:
        arr = np.frombuffer(raw_bytes, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None or img.size == 0:
            return None
        return img
    except Exception:
        return None


def _run_pipeline(bgr_image: np.ndarray) -> Dict[str, Any]:
    """Coarse → Fine → OCR 파이프라인을 실행하고 최종 결과를 반환한다.

    Args:
        bgr_image: BGR ndarray (H, W, 3).

    Returns:
        {
            "line": str,
            "section": str,
            "columns": str,
            "confidence": float,
        }
    """
    # --- Coarse Matcher: Top-5 후보 추출 ---
    coarse_result = coarse_matcher(bgr_image, top_k=5)
    candidates = coarse_result.get("candidates", [])  # type: ignore[union-attr]

    # --- Fine Matcher: 최종 라인 선택 ---
    fine_result = fine_matcher(bgr_image, candidates, top_k=1)

    # --- OCR 교차검증: 신뢰도 보정 ---
    ocr_result = verify_with_ocr(bgr_image, fine_result)  # type: ignore[arg-type]

    # --- 응답 포맷팅 ---
    line: str = str(ocr_result.get("line", ""))
    section: str = str(ocr_result.get("section", "0"))
    confidence: float = float(ocr_result.get("confidence", 0.0))
    confidence = round(max(0.0, min(1.0, confidence)), 4)

    # columns: Phase 2 MVP에서는 anchor 패턴으로부터 mock 값 생성
    # Phase 3에서 anchor_detector + pattern_matcher 결과로 교체 예정
    columns: str = _estimate_columns(bgr_image, line)

    return {
        "line": line,
        "section": section,
        "columns": columns,
        "confidence": confidence,
    }


def _estimate_columns(bgr_image: np.ndarray, line: str) -> str:
    """기둥 범위 추정 (Phase 2 MVP mock).

    실제 구현은 Phase 3에서 anchor_detector + pattern_matcher 결과로 교체한다.
    현재는 이미지 해상도 기반으로 mock 기둥 범위를 반환한다.

    Args:
        bgr_image: BGR ndarray.
        line: 식별된 라인명.

    Returns:
        기둥 범위 문자열 (예: "B4-B6").
    """
    height, width = bgr_image.shape[:2]
    # 이미지 가로 해상도에 따라 기둥 수 추정 (mock)
    col_count = max(2, min(8, width // 100))
    start_col = 1
    end_col = start_col + col_count - 1
    # 라인명에서 알파벳 접두어 추출
    prefix = "B"
    for ch in line:
        if ch.isalpha():
            prefix = ch.upper()
            break
    return f"{prefix}{start_col}-{prefix}{end_col}"
