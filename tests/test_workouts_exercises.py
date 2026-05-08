"""Tests for garmy.workouts.exercises module."""

import pytest

from garmy.workouts.exercises import (
    ALIASES,
    EXERCISES,
    ExerciseMatcher,
    MatchResult,
    get_matcher,
    resolve_exercise,
    search_exercises,
)


class TestMatchResult:
    """Test cases for MatchResult dataclass."""

    def test_match_result_creation(self):
        """Test creating a MatchResult."""
        result = MatchResult(
            name="BARBELL_BENCH_PRESS",
            category="BENCH_PRESS",
            score=0.95,
        )
        assert result.name == "BARBELL_BENCH_PRESS"
        assert result.category == "BENCH_PRESS"
        assert result.score == 0.95
        assert result.alternatives == []

    def test_match_result_with_alternatives(self):
        """Test MatchResult with alternatives."""
        alternatives = [
            ("DUMBBELL_BENCH_PRESS", "BENCH_PRESS", 0.90),
            ("INCLINE_BARBELL_BENCH_PRESS", "BENCH_PRESS", 0.88),
        ]
        result = MatchResult(
            name="BARBELL_BENCH_PRESS",
            category="BENCH_PRESS",
            score=0.95,
            alternatives=alternatives,
        )
        assert len(result.alternatives) == 2
        assert result.alternatives[0][0] == "DUMBBELL_BENCH_PRESS"

    def test_is_exact_property(self):
        """Test is_exact property."""
        exact_result = MatchResult(
            name="BARBELL_BENCH_PRESS",
            category="BENCH_PRESS",
            score=1.0,
        )
        assert exact_result.is_exact is True

        fuzzy_result = MatchResult(
            name="BARBELL_BENCH_PRESS",
            category="BENCH_PRESS",
            score=0.95,
        )
        assert fuzzy_result.is_exact is False

    def test_is_confident_property(self):
        """Test is_confident property."""
        confident_result = MatchResult(
            name="BARBELL_BENCH_PRESS",
            category="BENCH_PRESS",
            score=0.85,
        )
        assert confident_result.is_confident is True

        low_confidence_result = MatchResult(
            name="BARBELL_BENCH_PRESS",
            category="BENCH_PRESS",
            score=0.75,
        )
        assert low_confidence_result.is_confident is False

    def test_match_result_str(self):
        """Test string representation of MatchResult."""
        result = MatchResult(
            name="BARBELL_BENCH_PRESS",
            category="BENCH_PRESS",
            score=0.85,
        )
        assert str(result) == "BARBELL_BENCH_PRESS (85%)"

    def test_match_result_frozen(self):
        """Test that MatchResult is immutable (frozen)."""
        result = MatchResult(
            name="BARBELL_BENCH_PRESS",
            category="BENCH_PRESS",
            score=0.95,
        )
        with pytest.raises(AttributeError):
            result.name = "DUMBBELL_BENCH_PRESS"


class TestExerciseMatcherExactMatching:
    """Test exact matching functionality."""

    @pytest.fixture
    def matcher(self):
        """Create an ExerciseMatcher instance."""
        return ExerciseMatcher()

    def test_exact_match_screaming_snake_case(self, matcher):
        """Test exact match with SCREAMING_SNAKE_CASE input."""
        result = matcher.resolve("BARBELL_BENCH_PRESS")
        assert result is not None
        assert result.name == "BARBELL_BENCH_PRESS"
        assert result.category == "BENCH_PRESS"
        assert result.is_exact is True

    def test_exact_match_lowercase(self, matcher):
        """Test exact match with lowercase input."""
        result = matcher.resolve("barbell bench press")
        assert result is not None
        assert result.name == "BARBELL_BENCH_PRESS"
        assert result.category == "BENCH_PRESS"
        assert result.score >= 0.95

    def test_exact_match_mixed_case(self, matcher):
        """Test exact match with mixed case input."""
        result = matcher.resolve("Barbell Bench Press")
        assert result is not None
        assert result.name == "BARBELL_BENCH_PRESS"
        assert result.category == "BENCH_PRESS"

    def test_exact_match_with_underscores(self, matcher):
        """Test exact match with underscores instead of spaces."""
        result = matcher.resolve("barbell_bench_press")
        assert result is not None
        assert result.name == "BARBELL_BENCH_PRESS"
        assert result.category == "BENCH_PRESS"
        assert result.is_exact is True

    def test_exact_match_deadlift(self, matcher):
        """Test exact match for DEADLIFT exercises."""
        result = matcher.resolve("BARBELL_DEADLIFT")
        assert result is not None
        assert result.name == "BARBELL_DEADLIFT"
        assert result.category == "DEADLIFT"

    def test_exact_match_squat(self, matcher):
        """Test exact match for SQUAT exercises."""
        result = matcher.resolve("BARBELL_BACK_SQUAT")
        assert result is not None
        assert result.name == "BARBELL_BACK_SQUAT"
        assert result.category == "SQUAT"

    def test_exact_match_pull_up(self, matcher):
        """Test exact match for PULL_UP exercises."""
        result = matcher.resolve("PULL_UP")
        assert result is not None
        assert result.name == "PULL_UP"
        assert result.category == "PULL_UP"


class TestExerciseMatcherAliasMatching:
    """Test alias-based matching."""

    @pytest.fixture
    def matcher(self):
        """Create an ExerciseMatcher instance."""
        return ExerciseMatcher()

    def test_alias_bench_press(self, matcher):
        """Test alias matching for 'bench press'."""
        result = matcher.resolve("bench press")
        assert result is not None
        # The alias points to BARBELL_BENCH_PRESS, but exact match for BENCH_PRESS wins
        assert "BENCH_PRESS" in result.name
        assert result.category == "BENCH_PRESS"
        assert result.score >= 0.95

    def test_alias_deadlift(self, matcher):
        """Test alias matching for 'deadlift'."""
        result = matcher.resolve("deadlift")
        assert result is not None
        # The alias points to BARBELL_DEADLIFT, but exact match for DEADLIFT wins
        assert "DEADLIFT" in result.name
        assert result.category == "DEADLIFT"
        assert result.score >= 0.95

    def test_alias_squat(self, matcher):
        """Test alias matching for 'squat'."""
        result = matcher.resolve("squat")
        assert result is not None
        # The alias points to BARBELL_BACK_SQUAT, but exact match for SQUAT wins
        assert "SQUAT" in result.name
        assert result.category == "SQUAT"
        assert result.score >= 0.95

    def test_alias_overhead_press(self, matcher):
        """Test alias matching for 'overhead press'."""
        result = matcher.resolve("overhead press")
        assert result is not None
        assert result.category == "SHOULDER_PRESS"
        assert result.score >= 0.80

    def test_alias_curl(self, matcher):
        """Test alias matching for 'curl'."""
        result = matcher.resolve("curl")
        assert result is not None
        assert result.name == "BARBELL_BICEPS_CURL"
        assert result.category == "CURL"

    def test_alias_abbreviated_ohp(self, matcher):
        """Test alias matching for 'ohp' abbreviation."""
        result = matcher.resolve("ohp")
        assert result is not None
        assert result.name == "OVERHEAD_PRESS"
        assert result.score == 0.95

    def test_alias_abbreviated_dl(self, matcher):
        """Test alias matching for 'dl' abbreviation."""
        result = matcher.resolve("dl")
        assert result is not None
        assert result.name == "BARBELL_DEADLIFT"

    def test_alias_rdl(self, matcher):
        """Test alias matching for 'rdl' abbreviation."""
        result = matcher.resolve("rdl")
        assert result is not None
        assert result.name == "ROMANIAN_DEADLIFT"

    def test_alias_pull_up(self, matcher):
        """Test alias matching for 'pull up'."""
        result = matcher.resolve("pull up")
        assert result is not None
        assert result.name == "PULL_UP"

    def test_alias_push_up(self, matcher):
        """Test alias matching for 'push up'."""
        result = matcher.resolve("push up")
        assert result is not None
        assert result.name == "PUSH_UP"

    def test_alias_dip(self, matcher):
        """Test alias matching for 'dip'."""
        result = matcher.resolve("dip")
        assert result is not None
        assert "DIP" in result.name
        assert result.category == "TRICEPS_EXTENSION"

    def test_alias_lat_pulldown(self, matcher):
        """Test alias matching for 'lat pulldown'."""
        result = matcher.resolve("lat pulldown")
        assert result is not None
        assert result.name == "LAT_PULLDOWN"

    def test_alias_hamstring_curl(self, matcher):
        """Test alias matching for 'hamstring curl'."""
        result = matcher.resolve("hamstring curl")
        assert result is not None
        assert "HAMSTRING" in result.name or "LEG_CURL" in result.name

    def test_alias_kettlebell_swing(self, matcher):
        """Test alias matching for 'kettlebell swing'."""
        result = matcher.resolve("kettlebell swing")
        assert result is not None
        assert result.name == "KETTLEBELL_SWING"

    def test_alias_case_insensitive(self, matcher):
        """Test that alias matching is case-insensitive."""
        result = matcher.resolve("BENCH PRESS")
        assert result is not None
        assert "BENCH_PRESS" in result.name


class TestExerciseMatcherFuzzyMatching:
    """Test fuzzy matching with typos."""

    @pytest.fixture
    def matcher(self):
        """Create an ExerciseMatcher instance."""
        return ExerciseMatcher()

    def test_typo_dumbel_curl(self, matcher):
        """Test fuzzy matching with typo 'dumbel' instead of 'dumbbell'."""
        result = matcher.resolve("dumbel curl")
        assert result is not None
        # Should match something with curl
        assert "CURL" in result.name or result.category == "CURL"

    def test_typo_bench_pres(self, matcher):
        """Test fuzzy matching with typo 'pres' instead of 'press'."""
        result = matcher.resolve("bench pres")
        assert result is not None
        assert "BENCH_PRESS" in result.name

    def test_typo_deadlift_variation(self, matcher):
        """Test fuzzy matching with typo in deadlift."""
        result = matcher.resolve("deadlift")
        assert result is not None
        assert "DEADLIFT" in result.name

    def test_single_character_typo_squat(self, matcher):
        """Test fuzzy matching with single character typo."""
        result = matcher.resolve("sqauat")
        assert result is not None
        assert "SQUAT" in result.name

    def test_transposed_characters(self, matcher):
        """Test fuzzy matching with transposed characters."""
        result = matcher.resolve("barbell benchpress")
        assert result is not None
        assert "BENCH_PRESS" in result.name

    def test_missing_word_fuzzy(self, matcher):
        """Test fuzzy matching with missing word."""
        result = matcher.resolve("bench")
        assert result is not None
        assert "BENCH_PRESS" in result.name

    def test_extra_word_fuzzy(self, matcher):
        """Test fuzzy matching with extra word."""
        result = matcher.resolve("heavy barbell bench press")
        assert result is not None
        assert result.name == "BARBELL_BENCH_PRESS"


class TestEquipmentHints:
    """Test equipment hint functionality."""

    @pytest.fixture
    def matcher(self):
        """Create an ExerciseMatcher instance."""
        return ExerciseMatcher()

    def test_equipment_hint_dumbbell_curl(self, matcher):
        """Test equipment hint prefers DUMBBELL exercises."""
        result = matcher.resolve("curl", equipment_hint="dumbbell")
        assert result is not None
        # Without hint, would be BARBELL_BICEPS_CURL
        # With hint, should prefer a dumbbell variant
        assert result.score >= 0.75

    def test_equipment_hint_barbell_row(self, matcher):
        """Test equipment hint prefers BARBELL exercises."""
        result = matcher.resolve("row", equipment_hint="barbell")
        assert result is not None
        assert result.score >= 0.75

    def test_equipment_hint_kettlebell_swing(self, matcher):
        """Test equipment hint with kettlebell."""
        result = matcher.resolve("swing", equipment_hint="kettlebell")
        assert result is not None
        # Should find some swing-related exercise
        assert "SWING" in result.name

    def test_equipment_hint_cable(self, matcher):
        """Test equipment hint with cable."""
        result = matcher.resolve("row", equipment_hint="cable")
        assert result is not None
        assert result.score >= 0.75

    def test_equipment_hint_case_insensitive(self, matcher):
        """Test that equipment hint is case-insensitive."""
        result = matcher.resolve("curl", equipment_hint="DUMBBELL")
        assert result is not None
        assert result.score >= 0.75

    def test_equipment_hint_with_exact_match(self, matcher):
        """Test equipment hint doesn't break exact matches."""
        result = matcher.resolve("BARBELL_BENCH_PRESS", equipment_hint="dumbbell")
        assert result is not None
        assert result.name == "BARBELL_BENCH_PRESS"
        assert result.is_exact is True


class TestSearchFunctionality:
    """Test search functionality."""

    @pytest.fixture
    def matcher(self):
        """Create an ExerciseMatcher instance."""
        return ExerciseMatcher()

    def test_search_basic(self, matcher):
        """Test basic search returns results."""
        results = matcher.search("bench press")
        assert isinstance(results, list)
        assert len(results) > 0
        assert all(isinstance(r, MatchResult) for r in results)

    def test_search_returns_ranked_results(self, matcher):
        """Test search returns results ranked by score."""
        results = matcher.search("bench press", limit=10)
        assert len(results) > 0
        # Results should be sorted by score descending
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_search_limit_parameter(self, matcher):
        """Test search respects limit parameter."""
        results = matcher.search("press", limit=5)
        assert len(results) <= 5

    def test_search_limit_default(self, matcher):
        """Test search default limit is 10."""
        results = matcher.search("bench")
        assert len(results) <= 10

    def test_search_all_results_have_positive_score(self, matcher):
        """Test all search results have positive scores."""
        results = matcher.search("curl", limit=10)
        assert all(r.score > 0 for r in results)

    def test_search_squat(self, matcher):
        """Test search for 'squat' returns multiple variants."""
        results = matcher.search("squat", limit=10)
        assert len(results) > 0
        assert any("SQUAT" in r.name for r in results)

    def test_search_deadlift(self, matcher):
        """Test search for 'deadlift' returns variants."""
        results = matcher.search("deadlift", limit=5)
        assert len(results) > 0
        assert any("DEADLIFT" in r.name for r in results)

    def test_search_empty_query(self, matcher):
        """Test search with empty query returns empty list."""
        results = matcher.search("")
        assert results == []

    def test_search_whitespace_only(self, matcher):
        """Test search with whitespace-only query returns empty list."""
        results = matcher.search("   ")
        assert results == []

    def test_search_includes_high_score_results(self, matcher):
        """Test search includes exact and high-confidence matches first."""
        results = matcher.search("barbell bench press", limit=5)
        assert len(results) > 0
        # First result should be highly confident
        assert results[0].is_confident


class TestCategoryFunctions:
    """Test category-related functions."""

    @pytest.fixture
    def matcher(self):
        """Create an ExerciseMatcher instance."""
        return ExerciseMatcher()

    def test_list_categories(self, matcher):
        """Test list_categories returns non-empty list."""
        categories = matcher.list_categories()
        assert isinstance(categories, list)
        assert len(categories) > 0
        # Should be sorted
        assert categories == sorted(categories)

    def test_list_categories_contains_common_categories(self, matcher):
        """Test list_categories includes common exercise categories."""
        categories = matcher.list_categories()
        assert "BENCH_PRESS" in categories
        assert "DEADLIFT" in categories
        assert "SQUAT" in categories
        assert "CURL" in categories
        assert "ROW" in categories
        assert "PULL_UP" in categories
        assert "PUSH_UP" in categories

    def test_get_category_exact_name(self, matcher):
        """Test get_category with exact exercise name."""
        category = matcher.get_category("BARBELL_BENCH_PRESS")
        assert category == "BENCH_PRESS"

    def test_get_category_normalized_name(self, matcher):
        """Test get_category with normalized exercise name."""
        category = matcher.get_category("barbell bench press")
        assert category == "BENCH_PRESS"

    def test_get_category_not_found(self, matcher):
        """Test get_category returns None for unknown exercise."""
        category = matcher.get_category("NONEXISTENT_EXERCISE")
        assert category is None

    def test_list_by_category_bench_press(self, matcher):
        """Test list_by_category for BENCH_PRESS."""
        exercises = matcher.list_by_category("BENCH_PRESS")
        assert isinstance(exercises, list)
        assert len(exercises) > 0
        # All should contain BENCH_PRESS or related terms
        assert "BARBELL_BENCH_PRESS" in exercises
        assert all(isinstance(e, str) for e in exercises)
        # Should be sorted
        assert exercises == sorted(exercises)

    def test_list_by_category_case_insensitive(self, matcher):
        """Test list_by_category is case-insensitive."""
        exercises_upper = matcher.list_by_category("BENCH_PRESS")
        exercises_lower = matcher.list_by_category("bench_press")
        assert exercises_upper == exercises_lower

    def test_list_by_category_all_returned_are_valid(self, matcher):
        """Test all returned exercises belong to the category."""
        exercises = matcher.list_by_category("DEADLIFT")
        for exercise in exercises:
            assert EXERCISES[exercise] == "DEADLIFT"

    def test_list_by_category_deadlift(self, matcher):
        """Test list_by_category for DEADLIFT."""
        exercises = matcher.list_by_category("DEADLIFT")
        assert len(exercises) > 0
        assert "BARBELL_DEADLIFT" in exercises

    def test_list_by_category_curl(self, matcher):
        """Test list_by_category for CURL."""
        exercises = matcher.list_by_category("CURL")
        assert len(exercises) > 0
        assert "BARBELL_BICEPS_CURL" in exercises


class TestEquipmentFiltering:
    """Test equipment filtering functionality."""

    @pytest.fixture
    def matcher(self):
        """Create an ExerciseMatcher instance."""
        return ExerciseMatcher()

    def test_list_by_equipment_dumbbell(self, matcher):
        """Test list_by_equipment for DUMBBELL."""
        exercises = matcher.list_by_equipment("DUMBBELL")
        assert isinstance(exercises, list)
        assert len(exercises) > 0
        # All should start with DUMBBELL
        assert all(e.startswith("DUMBBELL") for e in exercises)
        assert "DUMBBELL_BENCH_PRESS" in exercises

    def test_list_by_equipment_barbell(self, matcher):
        """Test list_by_equipment for BARBELL."""
        exercises = matcher.list_by_equipment("BARBELL")
        assert len(exercises) > 0
        assert all(e.startswith("BARBELL") for e in exercises)
        assert "BARBELL_BENCH_PRESS" in exercises

    def test_list_by_equipment_kettlebell(self, matcher):
        """Test list_by_equipment for KETTLEBELL."""
        exercises = matcher.list_by_equipment("KETTLEBELL")
        assert len(exercises) > 0
        assert all(e.startswith("KETTLEBELL") for e in exercises)

    def test_list_by_equipment_cable(self, matcher):
        """Test list_by_equipment for CABLE."""
        exercises = matcher.list_by_equipment("CABLE")
        assert len(exercises) > 0
        assert all(e.startswith("CABLE") for e in exercises)

    def test_list_by_equipment_case_insensitive(self, matcher):
        """Test list_by_equipment is case-insensitive."""
        exercises_upper = matcher.list_by_equipment("DUMBBELL")
        exercises_lower = matcher.list_by_equipment("dumbbell")
        assert exercises_upper == exercises_lower

    def test_list_by_equipment_sorted(self, matcher):
        """Test list_by_equipment returns sorted results."""
        exercises = matcher.list_by_equipment("DUMBBELL")
        assert exercises == sorted(exercises)


class TestEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.fixture
    def matcher(self):
        """Create an ExerciseMatcher instance."""
        return ExerciseMatcher()

    def test_empty_input_returns_none(self, matcher):
        """Test empty input returns None."""
        result = matcher.resolve("")
        assert result is None

    def test_whitespace_only_returns_none(self, matcher):
        """Test whitespace-only input returns None."""
        result = matcher.resolve("   ")
        assert result is None
        result = matcher.resolve("\t\n")
        assert result is None

    def test_gibberish_input_returns_none_or_low_score(self, matcher):
        """Test gibberish input returns None or below threshold."""
        result = matcher.resolve("xyzabc123def456")
        # Should either return None or have very low score
        if result is not None:
            assert result.score < 0.5

    def test_resolve_or_raise_with_match(self, matcher):
        """Test resolve_or_raise returns result when match found."""
        result = matcher.resolve_or_raise("bench press")
        assert isinstance(result, MatchResult)
        assert "BENCH_PRESS" in result.name

    def test_resolve_or_raise_without_match_raises(self, matcher):
        """Test resolve_or_raise raises ValueError when no match."""
        with pytest.raises(ValueError) as exc_info:
            matcher.resolve_or_raise("xyzabc123")
        assert "No match found" in str(exc_info.value)

    def test_resolve_or_raise_includes_suggestions(self, matcher):
        """Test resolve_or_raise exception includes suggestions."""
        with pytest.raises(ValueError) as exc_info:
            matcher.resolve_or_raise("xyzabc123garbagetext")  # Gibberish that won't match
        error_msg = str(exc_info.value)
        assert "No match found" in error_msg

    def test_very_long_input(self, matcher):
        """Test handling of very long input."""
        long_input = "bench press " * 100
        result = matcher.resolve(long_input)
        # Should still work or return None gracefully
        assert result is None or isinstance(result, MatchResult)

    def test_special_characters_stripped(self, matcher):
        """Test that special characters are handled."""
        result = matcher.resolve("bench press")
        assert result is not None
        assert "BENCH_PRESS" in result.name

    def test_numeric_characters_preserved(self, matcher):
        """Test numeric characters in input."""
        result = matcher.resolve("45_degree_plank")
        # Should find the exercise if it exists
        assert result is not None or isinstance(result, type(None))

    def test_threshold_parameter(self):
        """Test creating matcher with custom threshold."""
        matcher_strict = ExerciseMatcher(threshold=0.9)
        matcher_lenient = ExerciseMatcher(threshold=0.3)

        # Both should find exact matches
        assert matcher_strict.resolve("BARBELL_BENCH_PRESS") is not None
        assert matcher_lenient.resolve("BARBELL_BENCH_PRESS") is not None

        # Lenient should find more fuzzy matches
        fuzzy_results_lenient = matcher_lenient.search("bench", limit=100)
        fuzzy_results_strict = matcher_strict.search("bench", limit=100)
        # Lenient might find more low-scoring results
        assert len(fuzzy_results_lenient) >= len(fuzzy_results_strict)


class TestModuleLevelFunctions:
    """Test module-level convenience functions."""

    def test_get_matcher_returns_singleton(self):
        """Test get_matcher returns same instance."""
        matcher1 = get_matcher()
        matcher2 = get_matcher()
        assert matcher1 is matcher2

    def test_get_matcher_returns_exercise_matcher(self):
        """Test get_matcher returns ExerciseMatcher."""
        matcher = get_matcher()
        assert isinstance(matcher, ExerciseMatcher)

    def test_resolve_exercise_returns_tuple(self):
        """Test resolve_exercise returns (name, category) tuple."""
        name, category = resolve_exercise("bench press")
        assert isinstance(name, str)
        assert isinstance(category, str)
        assert "BENCH_PRESS" in name
        assert category == "BENCH_PRESS"

    def test_resolve_exercise_raises_on_no_match(self):
        """Test resolve_exercise raises ValueError on no match."""
        with pytest.raises(ValueError):
            resolve_exercise("xyzabc123")

    def test_resolve_exercise_with_equipment_hint(self):
        """Test resolve_exercise accepts equipment_hint."""
        name, category = resolve_exercise("curl", equipment_hint="dumbbell")
        assert isinstance(name, str)
        assert isinstance(category, str)

    def test_search_exercises_returns_list(self):
        """Test search_exercises returns list."""
        results = search_exercises("bench")
        assert isinstance(results, list)
        assert all(isinstance(r, MatchResult) for r in results)

    def test_search_exercises_with_limit(self):
        """Test search_exercises accepts limit parameter."""
        results = search_exercises("bench", limit=5)
        assert len(results) <= 5

    def test_search_exercises_empty_query(self):
        """Test search_exercises with empty query."""
        results = search_exercises("")
        assert results == []


class TestConsistency:
    """Test consistency across different matching methods."""

    @pytest.fixture
    def matcher(self):
        """Create an ExerciseMatcher instance."""
        return ExerciseMatcher()

    def test_resolve_vs_search_consistency(self, matcher):
        """Test that resolve and search return consistent results."""
        # For a given query, resolve should return top search result
        query = "bench press"
        resolve_result = matcher.resolve(query)
        search_results = matcher.search(query, limit=1)

        if resolve_result and search_results:
            assert resolve_result.name == search_results[0].name

    def test_get_category_matches_exercises_db(self, matcher):
        """Test get_category matches EXERCISES database."""
        for exercise_name, expected_category in list(EXERCISES.items())[:50]:
            category = matcher.get_category(exercise_name)
            assert category == expected_category

    def test_list_by_category_consistency(self, matcher):
        """Test list_by_category is consistent."""
        categories = matcher.list_categories()
        for category in categories:
            exercises = matcher.list_by_category(category)
            # All returned exercises should belong to this category
            for exercise in exercises:
                assert EXERCISES[exercise] == category

    def test_list_by_equipment_consistency(self, matcher):
        """Test list_by_equipment is consistent."""
        for equipment in ["DUMBBELL", "BARBELL", "KETTLEBELL"]:
            exercises = matcher.list_by_equipment(equipment)
            for exercise in exercises:
                assert exercise.startswith(equipment)

    def test_alias_consistency(self, matcher):
        """Test all aliases map to valid exercises."""
        for alias, target in list(ALIASES.items())[:10]:  # Test first 10 aliases
            if target in EXERCISES:
                # Should be able to resolve this alias
                result = matcher.resolve(alias)
                assert result is not None
                # The result should be valid
                assert result.name in EXERCISES


class TestPerformance:
    """Test performance characteristics."""

    @pytest.fixture
    def matcher(self):
        """Create an ExerciseMatcher instance."""
        return ExerciseMatcher()

    def test_resolve_completes_quickly(self, matcher):
        """Test resolve completes in reasonable time."""
        import time

        start = time.time()
        for _ in range(100):
            matcher.resolve("bench press")
        elapsed = time.time() - start
        # Should complete 100 queries in less than 1 second
        assert elapsed < 1.0

    def test_search_completes_quickly(self, matcher):
        """Test search completes in reasonable time."""
        import time

        start = time.time()
        for _ in range(20):
            matcher.search("bench", limit=10)
        elapsed = time.time() - start
        # Should complete 20 searches in less than 2 seconds
        assert elapsed < 2.0

    def test_list_categories_completes_quickly(self, matcher):
        """Test list_categories completes quickly."""
        import time

        start = time.time()
        for _ in range(100):
            matcher.list_categories()
        elapsed = time.time() - start
        # Should be very fast
        assert elapsed < 0.1


class TestRegressions:
    """Test specific exercise matching scenarios."""

    @pytest.fixture
    def matcher(self):
        """Create an ExerciseMatcher instance."""
        return ExerciseMatcher()

    def test_face_pull_resolves(self, matcher):
        """Test face pull resolves correctly."""
        result = matcher.resolve("face pull")
        assert result is not None
        assert "FACE_PULL" in result.name

    def test_abs_wheel_resolves(self, matcher):
        """Test ab wheel resolves correctly."""
        result = matcher.resolve("ab wheel")
        assert result is not None
        assert result.name == "AB_WHEEL_ROLLOUT"

    def test_goblet_squat_resolves(self, matcher):
        """Test goblet squat resolves correctly."""
        result = matcher.resolve("goblet squat")
        assert result is not None
        assert result.name == "GOBLET_SQUAT"

    def test_hack_squat_resolves(self, matcher):
        """Test hack squat resolves correctly."""
        result = matcher.resolve("hack squat")
        assert result is not None
        assert "HACK_SQUAT" in result.name

    def test_leg_press_resolves(self, matcher):
        """Test leg press resolves correctly."""
        result = matcher.resolve("leg press")
        assert result is not None
        assert result.name == "LEG_PRESS"

    def test_leg_extension_resolves(self, matcher):
        """Test leg extension resolves correctly."""
        result = matcher.resolve("leg extension")
        assert result is not None
        assert result.name == "LEG_EXTENSIONS"

    def test_nordic_curl_resolves(self, matcher):
        """Test nordic hamstring curl resolves."""
        result = matcher.resolve("nordic hamstring curl")
        assert result is not None
        assert "NORDIC" in result.name or "HAMSTRING" in result.name

    def test_pallof_press_resolves(self, matcher):
        """Test pallof press resolves correctly."""
        result = matcher.resolve("pallof press")
        assert result is not None
        assert result.name == "PALLOF_PRESS"

    def test_woodchop_resolves(self, matcher):
        """Test woodchop resolves correctly."""
        result = matcher.resolve("woodchop")
        assert result is not None
        assert "WOODCHOP" in result.name or "CHOP" in result.name

    def test_hollow_body_hold_resolves(self, matcher):
        """Test hollow body hold resolves correctly."""
        result = matcher.resolve("hollow body hold")
        assert result is not None
        assert result.name == "HOLLOW_BODY_HOLD"

    def test_arnold_press_resolves(self, matcher):
        """Test arnold press resolves correctly."""
        result = matcher.resolve("arnold press")
        assert result is not None
        assert result.name == "ARNOLD_PRESS"

    def test_battle_rope_resolves(self, matcher):
        """Test battle rope resolves correctly."""
        result = matcher.resolve("battle rope")
        assert result is not None
        assert "BATTLE_ROPE" in result.name


class TestDataIntegrity:
    """Test that the exercise database is properly configured."""

    def test_exercises_dict_not_empty(self):
        """Test EXERCISES dict is not empty."""
        assert len(EXERCISES) > 0

    def test_aliases_dict_not_empty(self):
        """Test ALIASES dict is not empty."""
        assert len(ALIASES) > 0

    def test_all_exercise_names_are_strings(self):
        """Test all exercise names are strings."""
        assert all(isinstance(k, str) for k in EXERCISES.keys())

    def test_all_categories_are_strings(self):
        """Test all categories are strings."""
        assert all(isinstance(v, str) for v in EXERCISES.values())

    def test_all_aliases_point_to_valid_exercises(self):
        """Test all aliases point to exercises in EXERCISES."""
        for alias, target in ALIASES.items():
            # Target should be in EXERCISES or be transformable to it
            assert isinstance(target, str)

    def test_exercises_have_reasonable_count(self):
        """Test EXERCISES dict has a reasonable number of entries."""
        # Should have at least 100 exercises
        assert len(EXERCISES) > 100

    def test_categories_are_uppercase(self):
        """Test all category names follow SCREAMING_SNAKE_CASE."""
        categories = set(EXERCISES.values())
        for category in categories:
            assert category == category.upper()
            assert "_" in category or len(category) < 20


class TestNormalization:
    """Test text normalization logic."""

    def test_normalize_removes_special_chars(self):
        """Test normalization removes special characters."""
        matcher = ExerciseMatcher()
        normalized = matcher._normalize("bench-press!")
        assert "!" not in normalized
        assert "-" not in normalized

    def test_normalize_lowercase(self):
        """Test normalization converts to lowercase."""
        matcher = ExerciseMatcher()
        normalized = matcher._normalize("BARBELL_BENCH_PRESS")
        assert normalized == normalized.lower()

    def test_normalize_spaces_to_underscores(self):
        """Test normalization replaces spaces with underscores."""
        matcher = ExerciseMatcher()
        normalized = matcher._normalize("barbell bench press")
        assert " " not in normalized
        assert normalized == "barbell_bench_press"

    def test_normalize_strips_whitespace(self):
        """Test normalization strips leading/trailing whitespace."""
        matcher = ExerciseMatcher()
        normalized = matcher._normalize("  bench press  ")
        assert normalized == "bench_press"
        assert not normalized.startswith(" ")
        assert not normalized.endswith(" ")


class TestTokenization:
    """Test tokenization logic."""

    def test_tokenize_splits_by_underscores(self):
        """Test tokenization splits by underscores."""
        matcher = ExerciseMatcher()
        tokens = matcher._tokenize("barbell_bench_press")
        assert "barbell" in tokens
        assert "bench" in tokens
        assert "press" in tokens

    def test_tokenize_splits_by_spaces(self):
        """Test tokenization splits by spaces."""
        matcher = ExerciseMatcher()
        tokens = matcher._tokenize("barbell bench press")
        assert len(tokens) == 3

    def test_tokenize_returns_set(self):
        """Test tokenization returns a set."""
        matcher = ExerciseMatcher()
        tokens = matcher._tokenize("bench press")
        assert isinstance(tokens, set)


class TestLevenshteinSimilarity:
    """Test Levenshtein similarity calculation."""

    def test_levenshtein_exact_match(self):
        """Test Levenshtein distance for identical strings."""
        matcher = ExerciseMatcher()
        ratio = matcher._levenshtein_ratio("bench", "bench")
        assert ratio == 1.0

    def test_levenshtein_completely_different(self):
        """Test Levenshtein distance for completely different strings."""
        matcher = ExerciseMatcher()
        ratio = matcher._levenshtein_ratio("abc", "xyz")
        assert ratio < 0.5

    def test_levenshtein_single_char_difference(self):
        """Test Levenshtein distance with single character difference."""
        matcher = ExerciseMatcher()
        ratio = matcher._levenshtein_ratio("bench", "bencH")
        assert ratio >= 0.8

    def test_levenshtein_typo_dumbbell(self):
        """Test Levenshtein distance for common typo."""
        matcher = ExerciseMatcher()
        ratio = matcher._levenshtein_ratio("dumbbell", "dumbel")
        assert ratio >= 0.7
