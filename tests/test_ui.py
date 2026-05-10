"""Streamlit UI 통합 테스트."""
import pytest


def test_ui_imports_without_error():
    """src/ui/app.py 임포트 성공."""
    try:
        import streamlit  # noqa: F401
    except ImportError:
        pytest.skip("streamlit 미설치 — pip install streamlit")

    try:
        from src.ui import app  # noqa: F401
    except ImportError as e:
        pytest.fail(f"UI 모듈 임포트 실패: {e}")


def test_streamlit_installed():
    """streamlit 패키지 설치 확인."""
    try:
        import streamlit  # noqa: F401
    except ImportError:
        pytest.skip("streamlit 미설치 — pip install streamlit")


def test_requests_installed():
    """requests 패키지 설치 확인."""
    try:
        import requests  # noqa: F401
    except ImportError:
        pytest.skip("requests 미설치 — pip install requests")


def test_pil_installed():
    """PIL 패키지 설치 확인."""
    try:
        from PIL import Image  # noqa: F401
    except ImportError:
        pytest.skip("pillow 미설치 — pip install pillow")


def test_ui_module_exists():
    """src/ui/ 디렉토리 및 app.py 파일 존재."""
    import os
    ui_dir = os.path.join("src", "ui")
    app_file = os.path.join(ui_dir, "app.py")

    # UI 디렉토리 존재 여부
    assert os.path.isdir(ui_dir), f"{ui_dir} 디렉토리 미존재"

    # app.py 파일 존재 여부
    assert os.path.isfile(app_file), f"{app_file} 파일 미존재"


def test_ui_app_has_required_functions():
    """app.py에 필수 함수·설정이 포함되어 있는지 확인."""
    import os
    app_file = os.path.join("src", "ui", "app.py")

    with open(app_file, "r", encoding="utf-8") as f:
        content = f.read()

    # 필수 요소 확인
    assert "st.set_page_config" in content, "st.set_page_config 호출 미존재"
    assert "st.title" in content, "st.title 호출 미존재"
    assert "st.file_uploader" in content, "st.file_uploader 호출 미존재"
    assert "requests.post" in content, "API POST 호출 미존재"


def test_ui_api_response_format_handling():
    """app.py에서 API 응답 포맷 처리 확인."""
    import os
    app_file = os.path.join("src", "ui", "app.py")

    with open(app_file, "r", encoding="utf-8") as f:
        content = f.read()

    # 응답 필드 처리 확인
    assert "line" in content, "line 필드 처리 미존재"
    assert "section" in content, "section 필드 처리 미존재"
    assert "confidence" in content, "confidence 필드 처리 미존재"


def test_ui_confidence_percentage_display():
    """app.py에서 신뢰도를 퍼센트로 표시하는지 확인."""
    import os
    app_file = os.path.join("src", "ui", "app.py")

    with open(app_file, "r", encoding="utf-8") as f:
        content = f.read()

    # 퍼센트 표시 패턴 확인 (여러 방식)
    patterns = [
        "*100" in content,
        "pct" in content.lower(),
        "percent" in content.lower(),
        ".1f%" in content,  # f-string 포맷
    ]
    assert any(patterns), "신뢰도 퍼센트 표시 로직 미존재"


def test_ui_error_handling():
    """app.py에서 에러 처리가 있는지 확인."""
    import os
    app_file = os.path.join("src", "ui", "app.py")

    with open(app_file, "r", encoding="utf-8") as f:
        content = f.read()

    # 에러 처리 확인
    assert "st.error" in content or "except" in content, \
        "에러 처리 로직 미존재"


def test_ui_init_file_exists():
    """src/ui/__init__.py 파일 존재."""
    import os
    init_file = os.path.join("src", "ui", "__init__.py")
    assert os.path.isfile(init_file), f"{init_file} 파일 미존재"
