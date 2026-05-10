"""
테스트: 데이터 증강 파이프라인 (Data Augmentation Pipeline)

PRD §5 데이터 증강 대응
- 학습 데이터를 다양한 방식으로 변환하여 현장 이미지 상황 시뮬레이션
- 노이즈, 흐림(Blur), 크롭, 리사이즈 기법 적용
"""
import numpy as np
import pytest
import cv2

from src.preprocessing.data_augmentation import augment_image, augment_dataset


class TestAugmentImage:
    """단일 이미지 증강 함수 테스트."""

    def test_augment_crop_returns_cropped_image(self, white_bgr_image):
        """crop 증강 후 이미지 크기가 감소해야 한다."""
        result = augment_image(white_bgr_image, "crop", crop_ratio=0.8)
        assert isinstance(result, np.ndarray)
        assert result.dtype == np.uint8
        assert result.shape[2] == 3  # BGR 채널 유지
        # 80% 크롭 시 크기 감소 확인
        assert result.shape[0] < white_bgr_image.shape[0]
        assert result.shape[1] < white_bgr_image.shape[1]

    def test_augment_crop_respects_ratio(self, white_bgr_image):
        """crop_ratio가 적용되는지 검증."""
        crop_ratio = 0.7
        result = augment_image(white_bgr_image, "crop", crop_ratio=crop_ratio)
        # 원본 100x100, 70% 크롭 → ~70x70 근처
        expected_size = int(white_bgr_image.shape[0] * crop_ratio)
        # ±5px 오차 허용
        assert abs(result.shape[0] - expected_size) <= 5
        assert abs(result.shape[1] - expected_size) <= 5

    def test_augment_resize_returns_correct_size(self, white_bgr_image):
        """resize 증강 후 이미지가 지정 크기여야 한다."""
        target_size = (64, 64)
        result = augment_image(white_bgr_image, "resize", size=target_size)
        assert isinstance(result, np.ndarray)
        assert result.dtype == np.uint8
        assert result.shape == (target_size[0], target_size[1], 3)

    def test_augment_noise_preserves_dtype(self, white_bgr_image):
        """noise 증강 후 dtype이 uint8을 유지해야 한다."""
        result = augment_image(white_bgr_image, "noise", noise_std=10)
        assert isinstance(result, np.ndarray)
        assert result.dtype == np.uint8
        # 노이즈 추가로 픽셀값 변경 확인
        assert not np.array_equal(result, white_bgr_image)

    def test_augment_noise_preserves_shape(self, white_bgr_image):
        """noise 증강 후 이미지 형태가 유지되어야 한다."""
        result = augment_image(white_bgr_image, "noise", noise_std=10)
        assert result.shape == white_bgr_image.shape

    def test_augment_blur_returns_uint8_image(self, white_bgr_image):
        """blur 증강 후 결과가 uint8 이미지여야 한다."""
        result = augment_image(white_bgr_image, "blur", kernel_size=5)
        assert isinstance(result, np.ndarray)
        assert result.dtype == np.uint8
        assert result.shape == white_bgr_image.shape

    def test_augment_blur_changes_image(self, red_dot_image):
        """blur 증강이 이미지를 실제로 변경해야 한다."""
        result = augment_image(red_dot_image, "blur", kernel_size=5)
        # 블러로 인해 이미지 변경 확인
        assert not np.array_equal(result, red_dot_image)

    def test_augment_invalid_type_raises_error(self, white_bgr_image):
        """존재하지 않는 증강 타입은 ValueError를 발생시켜야 한다."""
        with pytest.raises(ValueError):
            augment_image(white_bgr_image, "invalid_type")

    def test_augment_handles_various_image_sizes(self):
        """다양한 크기의 이미지를 처리할 수 있어야 한다."""
        for size in [(50, 50), (128, 128), (256, 512)]:
            img = np.ones((*size, 3), dtype=np.uint8) * 128
            result = augment_image(img, "resize", size=(64, 64))
            assert result.shape == (64, 64, 3)

    def test_augment_preserves_channel_count(self, white_bgr_image):
        """모든 증강 후 채널 개수(3)가 유지되어야 한다."""
        for aug_type in ["crop", "resize", "noise", "blur"]:
            result = augment_image(
                white_bgr_image,
                aug_type,
                crop_ratio=0.8,
                size=(64, 64),
                noise_std=5,
                kernel_size=3,
            )
            assert result.shape[2] == 3


class TestAugmentDataset:
    """데이터셋 전체 증강 함수 테스트."""

    def test_augment_dataset_creates_augmented_files(
        self, sample_dir, white_bgr_image, red_dot_image
    ):
        """증강 데이터셋 함수가 파일을 생성해야 한다."""
        # 입력 디렉토리 생성 및 이미지 저장
        sample_dir.mkdir(parents=True, exist_ok=True)
        input_dir = sample_dir / "input"
        input_dir.mkdir(exist_ok=True)

        cv2.imwrite(str(input_dir / "image1.png"), white_bgr_image)
        cv2.imwrite(str(input_dir / "image2.png"), red_dot_image)

        # 출력 디렉토리
        output_dir = sample_dir / "output"

        # 증강 실행
        augment_dataset(input_dir, output_dir, ["crop", "resize"])

        # 출력 파일 확인
        assert output_dir.exists()
        output_files = list(output_dir.glob("*.png"))
        # 입력 2개 x 증강 2개 = 최소 2개의 파일 생성
        assert len(output_files) >= 2

    def test_augment_dataset_preserves_metadata(
        self, sample_dir, white_bgr_image
    ):
        """증강 후 메타데이터(원본과 같은 채널수)가 보존되어야 한다."""
        sample_dir.mkdir(parents=True, exist_ok=True)
        input_dir = sample_dir / "input"
        input_dir.mkdir(exist_ok=True)

        cv2.imwrite(str(input_dir / "test.png"), white_bgr_image)

        output_dir = sample_dir / "output"
        augment_dataset(input_dir, output_dir, ["crop"])

        # 출력된 이미지 읽기
        output_files = list(output_dir.glob("*.png"))
        assert len(output_files) > 0

        for file in output_files:
            img = cv2.imread(str(file))
            assert img is not None
            assert img.shape[2] == 3  # BGR 채널 유지

    def test_augment_dataset_empty_input_dir(self, sample_dir):
        """빈 입력 디렉토리도 안전하게 처리해야 한다."""
        sample_dir.mkdir(parents=True, exist_ok=True)
        input_dir = sample_dir / "empty_input"
        input_dir.mkdir(exist_ok=True)

        output_dir = sample_dir / "output"

        # 예외 없이 실행
        augment_dataset(input_dir, output_dir, ["crop"])

    def test_augment_dataset_multiple_types(self, sample_dir, white_bgr_image):
        """여러 증강 기법을 동시에 적용할 수 있어야 한다."""
        sample_dir.mkdir(parents=True, exist_ok=True)
        input_dir = sample_dir / "input"
        input_dir.mkdir(exist_ok=True)

        cv2.imwrite(str(input_dir / "image.png"), white_bgr_image)

        output_dir = sample_dir / "output"
        augment_dataset(
            input_dir, output_dir, ["crop", "resize", "noise", "blur"]
        )

        # 증강 기법 4개 + 원본 = 최소 4개 파일
        output_files = list(output_dir.glob("*.png"))
        assert len(output_files) >= 4

    def test_augment_dataset_handles_nonexistent_input_dir(self, sample_dir):
        """존재하지 않는 입력 디렉토리는 ValueError를 발생시켜야 한다."""
        nonexistent = sample_dir / "nonexistent"
        output_dir = sample_dir / "output"

        with pytest.raises((ValueError, FileNotFoundError)):
            augment_dataset(nonexistent, output_dir, ["crop"])

    def test_augment_dataset_creates_output_directory(
        self, sample_dir, white_bgr_image
    ):
        """출력 디렉토리가 없으면 생성해야 한다."""
        sample_dir.mkdir(parents=True, exist_ok=True)
        input_dir = sample_dir / "input"
        input_dir.mkdir(exist_ok=True)

        cv2.imwrite(str(input_dir / "image.png"), white_bgr_image)

        output_dir = sample_dir / "output"
        assert not output_dir.exists()

        augment_dataset(input_dir, output_dir, ["resize"])

        assert output_dir.exists()


class TestAugmentIntegration:
    """증강 파이프라인 통합 테스트."""

    def test_augmented_images_are_valid(self, sample_dir, white_bgr_image):
        """증강된 이미지들이 유효한 BGR 형식이어야 한다."""
        sample_dir.mkdir(parents=True, exist_ok=True)
        input_dir = sample_dir / "input"
        input_dir.mkdir(exist_ok=True)

        cv2.imwrite(str(input_dir / "original.png"), white_bgr_image)

        output_dir = sample_dir / "output"
        augment_dataset(input_dir, output_dir, ["crop", "resize", "noise"])

        output_files = sorted(output_dir.glob("*.png"))
        for file in output_files:
            img = cv2.imread(str(file))
            assert img is not None
            assert img.dtype == np.uint8
            assert len(img.shape) == 3
            assert img.shape[2] == 3

    def test_augmentation_randomness(self, white_bgr_image):
        """같은 기법을 두 번 적용해도 다른 결과를 반환해야 한다 (randomness)."""
        result1 = augment_image(white_bgr_image, "noise", noise_std=10)
        result2 = augment_image(white_bgr_image, "noise", noise_std=10)

        # 두 결과가 다름 (노이즈의 무작위성)
        assert not np.array_equal(result1, result2)

    def test_augmentation_respects_seed_if_provided(self, white_bgr_image):
        """시드가 지정되면 결과가 재현 가능해야 한다 (선택사항)."""
        # 이 테스트는 선택사항이며, 구현 시 시드 파라미터 추가 가능
        pass
