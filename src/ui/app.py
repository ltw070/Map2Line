"""Map2Line Streamlit UI — 도면 기반 라인 식별 시스템."""
import time

import requests
import streamlit as st
from PIL import Image


# ─── Constants ───────────────────────────────────────────────────────────
_API_URL = "http://localhost:8000/identify"
_SUPPORTED_FORMATS = ("jpg", "jpeg", "png")
_PAGE_TITLE = "Map2Line"
_PAGE_ICON = "🗺️"
_MAX_IMAGE_SIZE = 10_000_000  # 10MB


# ─── Page Configuration ──────────────────────────────────────────────────
st.set_page_config(
    page_title=_PAGE_TITLE,
    page_icon=_PAGE_ICON,
    layout="wide",
    initial_sidebar_state="expanded"
)


# ─── Title and Description ──────────────────────────────────────────────
st.title(f"{_PAGE_ICON} Map2Line — 도면 기반 라인 식별 시스템")
st.markdown("""
반도체 공장 도면 이미지에서 **라인**과 **구역**을 자동 식별합니다.
붉은 색 기둥의 기하학적 배치 패턴을 분석하여 신뢰도와 함께 결과를 제공합니다.
""")


# ─── Sidebar Configuration ──────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ 설정")
    api_url = st.text_input(
        "API URL",
        value=_API_URL,
        help="FastAPI 서버 주소 (기본값: http://localhost:8000)"
    )
    st.divider()
    st.subheader("📋 정보")
    st.markdown("""
    - **입력:** JPG, JPEG, PNG 형식의 도면 이미지
    - **출력:** 라인명, 구역, 신뢰도(%), 기둥 좌표
    - **응답:** 약 100~300ms (CPU 기준)
    """)


# ─── Main UI ────────────────────────────────────────────────────────────
st.header("📁 이미지 업로드")
uploaded_file = st.file_uploader(
    "도면 이미지를 여기에 드래그·드롭하거나 클릭하여 업로드",
    type=list(_SUPPORTED_FORMATS),
    help="지원되는 형식: JPG, JPEG, PNG"
)


if uploaded_file is not None:
    # ─── Image Preview ──────────────────────────────────────────────────
    st.subheader("📷 업로드된 이미지 미리보기")
    col_image, col_info = st.columns([3, 1])

    with col_image:
        image = Image.open(uploaded_file)
        st.image(image, use_column_width=True, caption="원본 이미지")

    with col_info:
        st.metric("파일 크기", f"{uploaded_file.size / 1024:.1f} KB")
        st.metric("해상도", f"{image.width} × {image.height}")

    # ─── Process Button ────────────────────────────────────────────────
    st.divider()
    st.subheader("🚀 식별 시작")
    if st.button("API 호출 및 분석", use_container_width=True, type="primary"):
        with st.spinner("분석 중... 잠깐만 기다려주세요."):
            try:
                # Prepare file for API
                uploaded_file.seek(0)
                files = {"image": uploaded_file}

                # Make API request
                start_time = time.time()
                response = requests.post(
                    api_url,
                    files=files,
                    timeout=30
                )
                elapsed_ms = (time.time() - start_time) * 1000

                # Check response status
                if response.status_code != 200:
                    st.error(
                        f"❌ API 오류 (상태 코드: {response.status_code})\n\n"
                        f"응답: {response.text[:200]}"
                    )
                else:
                    result = response.json()

                    # ─── Display Results ────────────────────────────
                    st.success("✅ 식별 성공!")

                    # Metrics row
                    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
                    with metric_col1:
                        st.metric("🏭 라인", result.get("line", "N/A"))
                    with metric_col2:
                        st.metric("📍 구역", result.get("section", "N/A"))
                    with metric_col3:
                        confidence_val = result.get("confidence", 0)
                        confidence_pct = confidence_val * 100
                        st.metric("📊 신뢰도", f"{confidence_pct:.1f}%")
                    with metric_col4:
                        st.metric("⏱️ 응답 시간", f"{elapsed_ms:.0f}ms")

                    # Details section
                    st.divider()
                    st.subheader("📋 상세 정보")
                    col_detail_left, col_detail_right = st.columns(2)

                    with col_detail_left:
                        st.write("**기둥 좌표 (앵커 포인트)**")
                        columns = result.get("columns", [])
                        if columns:
                            for idx, col in enumerate(columns, 1):
                                if isinstance(col, (list, tuple)) and len(col) >= 2:
                                    st.write(f"- 기둥 {idx}: ({col[0]}, {col[1]})")
                                else:
                                    st.write(f"- 기둥 {idx}: {col}")
                        else:
                            st.write("*기둥 정보 없음*")

                    with col_detail_right:
                        st.write("**추론 통계**")
                        st.write(f"- 응답 시간: {elapsed_ms:.1f}ms")
                        inference_time = result.get("inference_time_ms", None)
                        if inference_time is not None:
                            st.write(f"- 추론 시간: {inference_time:.1f}ms")

                    # Raw JSON (expandable)
                    with st.expander("📄 원본 JSON 응답 보기"):
                        st.json(result)

            except requests.exceptions.ConnectionError:
                st.error(
                    f"❌ API 서버에 연결할 수 없습니다.\n\n"
                    f"확인 사항:\n"
                    f"1. FastAPI 서버가 실행 중인가요?\n"
                    f"2. URL이 정확한가요? (현재: {api_url})\n"
                    f"3. 방화벽 설정을 확인해주세요."
                )
            except requests.exceptions.Timeout:
                st.error("❌ API 요청 시간 초과 (30초 이상 소요)")
            except requests.exceptions.RequestException as e:
                st.error(f"❌ 요청 오류: {str(e)[:200]}")
            except ValueError as e:
                st.error(f"❌ 응답 파싱 오류: {str(e)[:200]}")
            except Exception as e:
                st.error(f"❌ 예상치 못한 오류: {type(e).__name__}: {str(e)[:200]}")


# ─── Footer ────────────────────────────────────────────────────────────
st.divider()
st.caption(
    "🔧 Map2Line v1.0 | "
    "[GitHub](https://github.com/ltw070/Map2Line) | "
    "[문서](https://github.com/ltw070/Map2Line#readme)"
)
