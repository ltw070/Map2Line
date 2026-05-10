"""Task 1-4: 기하 패턴 매칭 테스트 (Red → Green → Refactor)."""
from src.matching.pattern_matcher import match_pattern


class TestMatchPattern:
    """match_pattern 함수에 대한 TDD 테스트 스위트."""

    def test_identical_pattern_returns_100_confidence(self):
        """동일 패턴 입력 시 신뢰도 1.0 반환."""
        query = [(50, 50), (150, 50), (100, 150)]
        ref_db = {
            "Line_A": {
                "section_102": [(50, 50), (150, 50), (100, 150)]
            }
        }
        result = match_pattern(query, ref_db)

        assert result["line"] == "Line_A"
        assert result["section"] == "section_102"
        assert result["confidence"] == 1.0

    def test_scaled_50pct_identifies_same_line(self):
        """50% 축소된 패턴도 동일 라인으로 식별 (스케일 불변성)."""
        # 원본: [(50,50),(150,50),(100,150)] → 50% 축소
        query = [(25, 25), (75, 25), (50, 75)]
        ref_db = {
            "Line_A": {
                "section_102": [(50, 50), (150, 50), (100, 150)]
            }
        }
        result = match_pattern(query, ref_db)

        assert result["line"] == "Line_A"
        assert result["section"] == "section_102"
        assert result["confidence"] >= 0.95

    def test_two_similar_patterns_selects_correct_line(self):
        """유사 패턴 2개 중 정답 라인을 선택 (오분류 방지)."""
        query = [(50, 50), (150, 50), (100, 150)]
        ref_db = {
            "Line_A": {
                "section_102": [(50, 50), (150, 50), (100, 150)]  # 정확히 일치
            },
            "Line_B": {
                "section_203": [(60, 60), (160, 60), (110, 160)]  # 유사하지만 다름
            },
        }
        result = match_pattern(query, ref_db)

        assert result["line"] == "Line_A"
        assert result["section"] == "section_102"

    def test_one_missing_anchor_still_matches(self):
        """앵커 1개 누락 시에도 매칭 성공 (robustness)."""
        # 3개 중 2개만 제공
        query = [(50, 50), (150, 50)]
        ref_db = {
            "Line_A": {
                "section_102": [(50, 50), (150, 50), (100, 150)]
            }
        }
        result = match_pattern(query, ref_db)

        assert result["line"] == "Line_A"
        assert result["section"] == "section_102"
        assert 0.8 <= result["confidence"] < 1.0

    def test_insufficient_query_returns_none(self):
        """쿼리 앵커가 2개 미만이면 None 반환."""
        query = [(50, 50)]
        ref_db = {
            "Line_A": {"section_102": [(50, 50), (150, 50), (100, 150)]}
        }
        result = match_pattern(query, ref_db)

        assert result["line"] is None
        assert result["section"] is None
        assert result["confidence"] == 0.0
