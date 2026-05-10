"""OCR 교차검증 — Task 2-3.

Fine Matcher 결과를 EasyOCR로 교차 검증하여 신뢰도를 보정한다.
EasyOCR 미설치 환경에서는 OCR skip으로 graceful degrade한다.

사용 예:
    from src.ocr.column_reader import verify_with_ocr

    fine_result = {"line": "Line_A", "section": "0", "confidence": 0.80, ...}
    result = verify_with_ocr(query_image, fine_result)
    # {
    #     "line": "Line_A",
    #     "section": "102",
    #     "confidence": 0.85,
    #     "inference_time_ms": 185.3,
    #     "ocr_text": "Line_A 102",
    # }
"""
from __future__ import annotations

import re
import time
from typing import Any, Dict, Optional

import numpy as np

# EasyOCR 가용 여부 확인
try:
    import easyocr  # noqa: F401  (가용성 확인용)
    _EASYOCR_AVAILABLE = True
except ImportError:
    _EASYOCR_AVAILABLE = False

# --- 상수 ---
MIN_WIDTH_PX: int = 400          # 저해상도 판별 기준 (이미지 너비 px)
OCR_MATCH_BOOST: float = 0.05    # OCR 일치 시 신뢰도 상승량
OCR_MISMATCH_PENALTY: float = 0.10  # OCR 불일치 시 신뢰도 하향량
_COLUMN_NUMBER_RE = re.compile(r'\b(\d{3})\b')  # 3자리 기둥 번호 정규식

# lazy-init EasyOCR Reader (최초 호출 시 1회 초기화)
_reader: Optional[Any] = None


def verify_with_ocr(
    query_image: np.ndarray,
    fine_result: Dict[str, Any],
) -> Dict[str, Any]:
    """Fine Matcher 결과를 EasyOCR로 교차검증하여 신뢰도를 보정한다.

    Args:
        query_image: BGR 이미지, shape (H, W, 3), dtype uint8.
        fine_result: Fine Matcher 출력 딕셔너리.
            필수 키: "line" (str), "section" (str), "confidence" (float),
                     "inference_time_ms" (float)

    Returns:
        보정된 결과 딕셔너리:
        {
            "line": str,
            "section": str,
            "confidence": float (0.0~1.0 클리핑),
            "inference_time_ms": float,
            "ocr_text": str,
        }

    Notes:
        - fine_result 딕셔너리는 변경하지 않는다 (side-effect 없음).
        - EasyOCR 미설치 또는 저해상도 이미지인 경우 OCR을 skip한다.
    """
    start = time.perf_counter()

    # 원본 값 복사 (side-effect 방지)
    line: str = str(fine_result["line"])
    section: str = str(fine_result["section"])
    confidence: float = float(fine_result["confidence"])

    ocr_text: str = ""

    # 저해상도 판별
    img_width: int = query_image.shape[1]
    is_high_res: bool = img_width >= MIN_WIDTH_PX

    if is_high_res and _EASYOCR_AVAILABLE:
        ocr_text = _ocr_read_text(query_image)
        confidence = _adjust_confidence(confidence, line, ocr_text, section)
        # OCR에서 기둥 번호 추출 성공 시 section 갱신
        if ocr_text and line.lower() in ocr_text.lower():
            match = _COLUMN_NUMBER_RE.search(ocr_text)
            if match:
                section = match.group(1)

    elapsed_ms: float = (time.perf_counter() - start) * 1000.0

    return {
        "line": line,
        "section": section,
        "confidence": float(confidence),
        "inference_time_ms": elapsed_ms,
        "ocr_text": ocr_text,
    }


# ---------------------------------------------------------------------------
# 내부 헬퍼
# ---------------------------------------------------------------------------

def _ocr_read_text(image: np.ndarray) -> str:
    """EasyOCR로 이미지에서 텍스트를 추출한다.

    Args:
        image: BGR 이미지, shape (H, W, 3).

    Returns:
        추출된 텍스트 (공백 구분 결합). 실패 시 빈 문자열.
    """
    global _reader

    try:
        if _reader is None:
            import easyocr as _easyocr_lib
            _reader = _easyocr_lib.Reader(['en'], gpu=False, verbose=False)

        # EasyOCR는 RGB 또는 BGR 모두 처리 가능; 결과는 [(bbox, text, conf), ...]
        results = _reader.readtext(image, detail=1)
        texts = [item[1] for item in results if item[2] > 0.3]
        return " ".join(texts)
    except Exception:
        return ""


def _adjust_confidence(
    confidence: float,
    line: str,
    ocr_text: str,
    section: str,  # noqa: ARG001 (향후 section 기반 검증 확장용)
) -> float:
    """OCR 텍스트와 line 이름 비교 결과에 따라 신뢰도를 보정한다.

    Args:
        confidence: 현재 신뢰도 (0.0~1.0).
        line: Fine Matcher가 예측한 라인 이름.
        ocr_text: OCR로 추출한 원본 텍스트.
        section: 현재 section 값 (향후 검증 확장 예정).

    Returns:
        보정된 신뢰도 (0.0~1.0 클리핑).
    """
    if not ocr_text:
        # OCR 결과 없음 → 현상 유지
        return confidence

    if line.lower() in ocr_text.lower():
        adjusted = confidence + OCR_MATCH_BOOST
    else:
        adjusted = confidence - OCR_MISMATCH_PENALTY

    # 0.0~1.0 클리핑
    return float(max(0.0, min(1.0, adjusted)))
