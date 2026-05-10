"""Coarse Matcher — Task 2-1 Green 구현.

ResNet-18 기반 CNN으로 Top-K 라인 후보를 반환한다.
PyTorch 미설치 환경을 위한 numpy 폴백 구현 포함.

사용 예:
    from src.matching.coarse_matcher import coarse_matcher

    result = coarse_matcher(image, top_k=5)
    # {"candidates": [{"line": "Line_A_1", "confidence": 0.95}, ...],
    #  "inference_time_ms": 120.5}
"""

import time
from typing import Any, Dict, List, Union

import numpy as np

# PyTorch 가용 여부 확인
try:
    import torch
    import torchvision.transforms as transforms
    from torchvision.models import resnet18, ResNet18_Weights
    _TORCH_AVAILABLE = True
except ImportError:
    _TORCH_AVAILABLE = False

# --- 전역 상수 ---
_INPUT_SIZE = (224, 224)
_IMAGENET_MEAN = [0.485, 0.456, 0.406]
_IMAGENET_STD = [0.229, 0.224, 0.225]
_NUM_CLASSES = 1000  # ImageNet 클래스 수 (Mock 매핑용)

# --- 모델 싱글톤 ---
_MODEL = None
_TRANSFORM = None
_DEVICE = None


def _get_device() -> "torch.device":
    """실행 디바이스 반환 (CUDA 우선, 없으면 CPU)."""
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def _load_model() -> None:
    """ResNet-18 모델을 한 번만 로드한다 (싱글톤 패턴)."""
    global _MODEL, _TRANSFORM, _DEVICE
    if _MODEL is not None:
        return

    _DEVICE = _get_device()
    _MODEL = resnet18(weights=ResNet18_Weights.IMAGENET1K_V1).eval().to(_DEVICE)
    _TRANSFORM = transforms.Compose([
        transforms.ToPILImage(),
        transforms.Resize(_INPUT_SIZE),
        transforms.ToTensor(),
        transforms.Normalize(mean=_IMAGENET_MEAN, std=_IMAGENET_STD),
    ])


def _generate_line_names(num_classes: int) -> List[str]:
    """클래스 인덱스를 라인명으로 매핑한다 (Mock).

    실제 서비스에서는 fine-tuning된 모델의 클래스 레이블로 교체한다.
    """
    names: List[str] = []
    for i in range(num_classes):
        letter = chr(65 + (i % 26))   # A–Z 순환
        group = i // 26 + 1
        names.append(f"Line_{letter}_{group}")
    return names


# 라인명 캐시 (전역 1회 생성)
_LINE_NAMES: List[str] = _generate_line_names(_NUM_CLASSES)


def _infer_single_torch(image: np.ndarray, top_k: int) -> Dict[str, Any]:
    """PyTorch ResNet-18으로 단일 이미지를 추론한다."""
    _load_model()
    start = time.perf_counter()

    with torch.no_grad():
        tensor = _TRANSFORM(image).unsqueeze(0).to(_DEVICE)  # type: ignore[misc]
        logits = _MODEL(tensor)                               # type: ignore[misc]
        probs = torch.softmax(logits, dim=1)[0]

        k = min(top_k, len(probs))
        top_probs, top_indices = torch.topk(probs, k)

        candidates: List[Dict[str, Any]] = [
            {"line": _LINE_NAMES[idx.item()], "confidence": float(prob.item())}
            for prob, idx in zip(top_probs, top_indices)
        ]

    elapsed_ms = (time.perf_counter() - start) * 1000.0
    return {"candidates": candidates, "inference_time_ms": elapsed_ms}


def _infer_single_numpy(image: np.ndarray, top_k: int) -> Dict[str, Any]:
    """NumPy 폴백: 무작위 신뢰도로 Top-K 후보를 생성한다.

    PyTorch 미설치 환경에서 인터페이스 호환성을 보장하기 위한 구현.
    실제 추론 품질은 보장하지 않는다.
    """
    rng = np.random.default_rng(seed=int(image.sum()) % (2**31))
    start = time.perf_counter()

    raw_scores = rng.random(_NUM_CLASSES).astype(np.float64)
    # softmax 적용
    exp_scores = np.exp(raw_scores - raw_scores.max())
    probs = exp_scores / exp_scores.sum()

    top_indices = np.argsort(probs)[::-1][:top_k]
    candidates: List[Dict[str, Any]] = [
        {"line": _LINE_NAMES[idx], "confidence": float(probs[idx])}
        for idx in top_indices
    ]

    elapsed_ms = (time.perf_counter() - start) * 1000.0
    return {"candidates": candidates, "inference_time_ms": elapsed_ms}


def _infer_single(image: np.ndarray, top_k: int) -> Dict[str, Any]:
    """단일 이미지 추론 디스패처."""
    if _TORCH_AVAILABLE:
        return _infer_single_torch(image, top_k)
    return _infer_single_numpy(image, top_k)


def coarse_matcher(
    image: Union[np.ndarray, List[np.ndarray]],
    top_k: int = 5,
) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """CNN으로 입력 이미지의 Top-K 라인 후보를 반환한다.

    Args:
        image: BGR 이미지 (H, W, 3) 또는 배치.
               배치 형식: 4D ndarray (N, H, W, 3) 또는 list[ndarray].
        top_k: 반환할 후보 개수 (기본값: 5).

    Returns:
        단일 이미지 입력:
            {
                "candidates": [{"line": str, "confidence": float}, ...],
                "inference_time_ms": float,
            }
        배치 입력: 위 형식의 list.
    """
    is_batch = isinstance(image, list) or (
        isinstance(image, np.ndarray) and image.ndim == 4
    )

    if is_batch:
        if isinstance(image, list):
            images: List[np.ndarray] = image
        else:
            images = [image[i] for i in range(image.shape[0])]
        return [_infer_single(img, top_k) for img in images]

    assert isinstance(image, np.ndarray)
    return _infer_single(image, top_k)
