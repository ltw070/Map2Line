"""
데이터 증강 파이프라인 (Data Augmentation Pipeline)

PRD §5 데이터 증강 대응:
- 학습 데이터를 다양한 방식으로 변환하여 현장 이미지 상황 시뮬레이션
- 노이즈 추가, 흐림(Blur) 처리, 일부 가림(Crop), 크기 조정(Resize)
"""
from pathlib import Path
from typing import Optional
import numpy as np
import cv2


# 상수: 증강 기법 목록
_AUGMENTATION_TYPES = {"crop", "resize", "noise", "blur"}

# 상수: 기법별 기본 파라미터
_DEFAULT_CROP_RATIO = 0.8
_DEFAULT_RESIZE_SIZE = (64, 64)
_DEFAULT_NOISE_STD = 10
_DEFAULT_BLUR_KERNEL_SIZE = 5


def augment_image(
    image: np.ndarray,
    augmentation_type: str,
    crop_ratio: Optional[float] = None,
    size: Optional[tuple[int, int]] = None,
    noise_std: Optional[float] = None,
    kernel_size: Optional[int] = None,
) -> np.ndarray:
    """단일 이미지에 증강 기법을 적용한다.

    Args:
        image: BGR 이미지 (H, W, 3), dtype uint8.
        augmentation_type: "crop", "resize", "noise", "blur" 중 하나.
        crop_ratio: crop 기법 시 유지할 비율 (0.0~1.0, 기본값 0.8)
        size: resize 기법 시 목표 크기 (H, W), 기본값 (64, 64)
        noise_std: noise 기법 시 표준편차, 기본값 10
        kernel_size: blur 기법 시 커널 크기 (홀수), 기본값 5

    Returns:
        증강된 이미지 (H', W', 3), dtype uint8.

    Raises:
        ValueError: augmentation_type이 유효하지 않은 경우.
    """
    if augmentation_type not in _AUGMENTATION_TYPES:
        raise ValueError(
            f"augmentation_type must be one of {_AUGMENTATION_TYPES}, "
            f"got {augmentation_type}"
        )

    if augmentation_type == "crop":
        return _augment_crop(image, crop_ratio or _DEFAULT_CROP_RATIO)
    elif augmentation_type == "resize":
        return _augment_resize(image, size or _DEFAULT_RESIZE_SIZE)
    elif augmentation_type == "noise":
        return _augment_noise(image, noise_std or _DEFAULT_NOISE_STD)
    elif augmentation_type == "blur":
        return _augment_blur(image, kernel_size or _DEFAULT_BLUR_KERNEL_SIZE)


def _augment_crop(image: np.ndarray, crop_ratio: float) -> np.ndarray:
    """이미지를 중심에서 랜덤하게 크롭한다.

    Args:
        image: BGR 이미지.
        crop_ratio: 유지할 비율 (0.0~1.0).

    Returns:
        크롭된 이미지.
    """
    h, w = image.shape[:2]
    new_h = int(h * crop_ratio)
    new_w = int(w * crop_ratio)

    # 중심 기준 랜덤 오프셋
    y_offset = np.random.randint(0, h - new_h + 1) if h > new_h else 0
    x_offset = np.random.randint(0, w - new_w + 1) if w > new_w else 0

    return image[y_offset : y_offset + new_h, x_offset : x_offset + new_w]


def _augment_resize(image: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    """이미지를 지정 크기로 리사이즈한다.

    Args:
        image: BGR 이미지.
        size: 목표 크기 (H, W).

    Returns:
        리사이즈된 이미지 (size[0], size[1], 3).
    """
    return cv2.resize(image, (size[1], size[0]))


def _augment_noise(image: np.ndarray, noise_std: float) -> np.ndarray:
    """이미지에 가우시안 노이즈를 추가한다.

    Args:
        image: BGR 이미지.
        noise_std: 표준편차.

    Returns:
        노이즈가 추가된 이미지 (dtype uint8).
    """
    noise = np.random.normal(0, noise_std, image.shape)
    noisy = image.astype(np.float32) + noise
    # uint8 범위로 클리핑
    noisy = np.clip(noisy, 0, 255)
    return noisy.astype(np.uint8)


def _augment_blur(image: np.ndarray, kernel_size: int) -> np.ndarray:
    """이미지에 가우시안 블러를 적용한다.

    Args:
        image: BGR 이미지.
        kernel_size: 커널 크기 (홀수).

    Returns:
        블러된 이미지 (dtype uint8).
    """
    # 커널 크기가 홀수 확보
    if kernel_size % 2 == 0:
        kernel_size += 1
    return cv2.GaussianBlur(image, (kernel_size, kernel_size), 0)


def augment_dataset(
    input_dir: Path,
    output_dir: Path,
    augmentation_types: list[str],
) -> None:
    """디렉토리 내 이미지들을 증강하여 저장한다.

    Args:
        input_dir: 원본 이미지 디렉토리 (Path 또는 str).
        output_dir: 증강 이미지 저장 디렉토리 (Path 또는 str).
        augmentation_types: 적용할 증강 기법 목록 ["crop", "resize", ...].

    Raises:
        FileNotFoundError: input_dir이 존재하지 않는 경우.
        ValueError: input_dir이 디렉토리가 아닌 경우.
    """
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)

    if not input_dir.exists():
        raise FileNotFoundError(f"input_dir does not exist: {input_dir}")

    if not input_dir.is_dir():
        raise ValueError(f"input_dir must be a directory: {input_dir}")

    # 출력 디렉토리 생성
    output_dir.mkdir(parents=True, exist_ok=True)

    # 지원하는 이미지 확장자
    image_extensions = {".png", ".jpg", ".jpeg", ".bmp", ".tiff"}

    # 입력 디렉토리의 모든 이미지 파일 처리
    for image_file in input_dir.iterdir():
        if image_file.suffix.lower() not in image_extensions:
            continue

        # 이미지 읽기
        image = cv2.imread(str(image_file))
        if image is None:
            continue

        # 각 증강 기법별로 처리
        for aug_type in augmentation_types:
            try:
                augmented = augment_image(image, aug_type)
            except ValueError:
                continue

            # 출력 파일명 생성: original_augtype.png
            stem = image_file.stem
            output_path = output_dir / f"{stem}_{aug_type}.png"
            cv2.imwrite(str(output_path), augmented)
