"""
Unit tests for line type validation using Strategy pattern.

Tests cover all four line type validators (DIALOGUE, STAGE_DIRECTION, CUE_LINE, SPACING)
and the LineTypeValidatorRegistry.
"""

import pytest
from unittest.mock import MagicMock

from models.script import ScriptLineType
from models.show import ShowScriptType
from utils.show.line_type_validator import (
    DialogueValidator,
    StageDirectionValidator,
    CueLineValidator,
    SpacingValidator,
    LineTypeValidatorRegistry,
    LineTypeValidationResult,
)


class TestDialogueValidator:
    """Test suite for DialogueValidator."""

    @pytest.fixture
    def validator(self):
        """Create a DialogueValidator instance."""
        return DialogueValidator()

    @pytest.fixture
    def full_mode_show(self):
        """Create a mock show in FULL script mode."""
        show = MagicMock()
        show.script_mode = ShowScriptType.FULL
        return show

    @pytest.fixture
    def compact_mode_show(self):
        """Create a mock show in COMPACT script mode."""
        show = MagicMock()
        show.script_mode = ShowScriptType.COMPACT
        return show

    def test_valid_single_part_with_character(self, validator, full_mode_show):
        """Test dialogue with valid single line part and character."""
        line_json = {
            "line_type": 1,
            "line_parts": [{"character_id": 1, "line_text": "Hello world"}],
        }
        result = validator.validate(line_json, full_mode_show)
        assert result.is_valid is True
        assert result.error_message == ""

    def test_valid_single_part_with_character_group(self, validator, full_mode_show):
        """Test dialogue with valid single line part and character group."""
        line_json = {
            "line_type": 1,
            "line_parts": [{"character_group_id": 1, "line_text": "Hello world"}],
        }
        result = validator.validate(line_json, full_mode_show)
        assert result.is_valid is True

    def test_valid_multiple_parts_full_mode(self, validator, full_mode_show):
        """Test dialogue with multiple line parts in FULL mode."""
        line_json = {
            "line_type": 1,
            "line_parts": [
                {"character_id": 1, "line_text": "Hello"},
                {"character_id": 2, "line_text": "Hi there"},
                {"character_id": 1, "line_text": "How are you?"},
            ],
        }
        result = validator.validate(line_json, full_mode_show)
        assert result.is_valid is True

    def test_rejects_empty_line_parts_array(self, validator, full_mode_show):
        """Test dialogue with empty line_parts array is rejected."""
        line_json = {"line_type": 1, "line_parts": []}
        result = validator.validate(line_json, full_mode_show)
        assert result.is_valid is False
        assert "must have at least one line part" in result.error_message

    def test_rejects_multiple_parts_compact_mode(self, validator, compact_mode_show):
        """Test dialogue with multiple line parts in COMPACT mode is rejected."""
        line_json = {
            "line_type": 1,
            "line_parts": [
                {"character_id": 1, "line_text": "Hello"},
                {"character_id": 2, "line_text": "Hi"},
            ],
        }
        result = validator.validate(line_json, compact_mode_show)
        assert result.is_valid is False
        assert "only have 1 line part in compact script mode" in result.error_message

    def test_rejects_no_character_or_group(self, validator, full_mode_show):
        """Test dialogue line part with neither character nor group is rejected."""
        line_json = {"line_type": 1, "line_parts": [{"line_text": "Hello world"}]}
        result = validator.validate(line_json, full_mode_show)
        assert result.is_valid is False
        assert "must have a character or character group" in result.error_message

    def test_rejects_both_character_and_group(self, validator, full_mode_show):
        """Test dialogue line part with both character and group is rejected."""
        line_json = {
            "line_type": 1,
            "line_parts": [
                {"character_id": 1, "character_group_id": 1, "line_text": "Hello"}
            ],
        }
        result = validator.validate(line_json, full_mode_show)
        assert result.is_valid is False
        assert "cannot have both character and character group" in result.error_message

    def test_rejects_empty_text_single_part(self, validator, full_mode_show):
        """Test dialogue with single part and None text is rejected."""
        line_json = {
            "line_type": 1,
            "line_parts": [{"character_id": 1, "line_text": None}],
        }
        result = validator.validate(line_json, full_mode_show)
        assert result.is_valid is False
        assert "must contain text" in result.error_message

    def test_allows_empty_text_if_other_parts_have_text(
        self, validator, full_mode_show
    ):
        """Test dialogue allows None text in one part if others have text."""
        line_json = {
            "line_type": 1,
            "line_parts": [
                {"character_id": 1, "line_text": "Hello"},
                {"character_id": 2, "line_text": None},
            ],
        }
        result = validator.validate(line_json, full_mode_show)
        assert result.is_valid is True

    def test_rejects_all_empty_text_multipart(self, validator, full_mode_show):
        """Test dialogue with multiple parts all having None text is rejected."""
        line_json = {
            "line_type": 1,
            "line_parts": [
                {"character_id": 1, "line_text": None},
                {"character_id": 2, "line_text": None},
            ],
        }
        result = validator.validate(line_json, full_mode_show)
        assert result.is_valid is False
        assert "At least one line part must contain text" in result.error_message


class TestStageDirectionValidator:
    """Test suite for StageDirectionValidator."""

    @pytest.fixture
    def validator(self):
        """Create a StageDirectionValidator instance."""
        return StageDirectionValidator()

    @pytest.fixture
    def mock_show(self):
        """Create a mock show."""
        return MagicMock()

    def test_valid_with_text(self, validator, mock_show):
        """Test stage direction with valid single part and text."""
        line_json = {"line_type": 2, "line_parts": [{"line_text": "Enter stage left"}]}
        result = validator.validate(line_json, mock_show)
        assert result.is_valid is True
        assert result.error_message == ""

    def test_rejects_zero_parts(self, validator, mock_show):
        """Test stage direction with zero parts is rejected."""
        line_json = {"line_type": 2, "line_parts": []}
        result = validator.validate(line_json, mock_show)
        assert result.is_valid is False
        assert "must have exactly 1 line part" in result.error_message

    def test_rejects_multiple_parts(self, validator, mock_show):
        """Test stage direction with multiple parts is rejected."""
        line_json = {
            "line_type": 2,
            "line_parts": [{"line_text": "Enter"}, {"line_text": "Exit"}],
        }
        result = validator.validate(line_json, mock_show)
        assert result.is_valid is False
        assert "must have exactly 1 line part" in result.error_message

    def test_rejects_with_character(self, validator, mock_show):
        """Test stage direction with character_id is rejected."""
        line_json = {
            "line_type": 2,
            "line_parts": [{"character_id": 1, "line_text": "Enter stage left"}],
        }
        result = validator.validate(line_json, mock_show)
        assert result.is_valid is False
        assert "cannot have characters" in result.error_message

    def test_rejects_with_character_group(self, validator, mock_show):
        """Test stage direction with character_group_id is rejected."""
        line_json = {
            "line_type": 2,
            "line_parts": [{"character_group_id": 1, "line_text": "Enter stage left"}],
        }
        result = validator.validate(line_json, mock_show)
        assert result.is_valid is False
        assert "cannot have character groups" in result.error_message

    def test_rejects_empty_text(self, validator, mock_show):
        """Test stage direction with None text is rejected."""
        line_json = {"line_type": 2, "line_parts": [{"line_text": None}]}
        result = validator.validate(line_json, mock_show)
        assert result.is_valid is False
        assert "must contain text" in result.error_message

    def test_rejects_whitespace_only_text(self, validator, mock_show):
        """Test stage direction with whitespace-only text is rejected."""
        line_json = {"line_type": 2, "line_parts": [{"line_text": "   "}]}
        result = validator.validate(line_json, mock_show)
        assert result.is_valid is False
        assert "must contain text" in result.error_message


class TestCueLineValidator:
    """Test suite for CueLineValidator."""

    @pytest.fixture
    def validator(self):
        """Create a CueLineValidator instance."""
        return CueLineValidator()

    @pytest.fixture
    def mock_show(self):
        """Create a mock show."""
        return MagicMock()

    def test_valid_with_no_parts(self, validator, mock_show):
        """Test cue line with no line_parts is valid."""
        line_json = {"line_type": 3, "line_parts": []}
        result = validator.validate(line_json, mock_show)
        assert result.is_valid is True
        assert result.error_message == ""

    def test_rejects_with_one_line_part(self, validator, mock_show):
        """Test cue line with one line_part is rejected."""
        line_json = {"line_type": 3, "line_parts": [{"line_text": "Some text"}]}
        result = validator.validate(line_json, mock_show)
        assert result.is_valid is False
        assert "cannot have line parts" in result.error_message

    def test_rejects_with_multiple_line_parts(self, validator, mock_show):
        """Test cue line with multiple line_parts is rejected."""
        line_json = {
            "line_type": 3,
            "line_parts": [
                {"character_id": 1, "line_text": "Text 1"},
                {"character_id": 2, "line_text": "Text 2"},
            ],
        }
        result = validator.validate(line_json, mock_show)
        assert result.is_valid is False
        assert "cannot have line parts" in result.error_message


class TestSpacingValidator:
    """Test suite for SpacingValidator."""

    @pytest.fixture
    def validator(self):
        """Create a SpacingValidator instance."""
        return SpacingValidator()

    @pytest.fixture
    def mock_show(self):
        """Create a mock show."""
        return MagicMock()

    def test_valid_with_no_parts(self, validator, mock_show):
        """Test spacing line with no line_parts is valid."""
        line_json = {"line_type": 4, "line_parts": []}
        result = validator.validate(line_json, mock_show)
        assert result.is_valid is True
        assert result.error_message == ""

    def test_rejects_with_one_line_part(self, validator, mock_show):
        """Test spacing line with one line_part is rejected."""
        line_json = {"line_type": 4, "line_parts": [{"line_text": "Some text"}]}
        result = validator.validate(line_json, mock_show)
        assert result.is_valid is False
        assert "cannot have line parts" in result.error_message

    def test_rejects_with_multiple_line_parts(self, validator, mock_show):
        """Test spacing line with multiple line_parts is rejected."""
        line_json = {
            "line_type": 4,
            "line_parts": [
                {"character_id": 1, "line_text": "Text 1"},
                {"character_id": 2, "line_text": "Text 2"},
            ],
        }
        result = validator.validate(line_json, mock_show)
        assert result.is_valid is False
        assert "cannot have line parts" in result.error_message


class TestLineTypeValidatorRegistry:
    """Test suite for LineTypeValidatorRegistry."""

    @pytest.fixture
    def registry(self):
        """Create a LineTypeValidatorRegistry instance."""
        return LineTypeValidatorRegistry()

    @pytest.fixture
    def mock_show(self):
        """Create a mock show in FULL mode."""
        show = MagicMock()
        show.script_mode = ShowScriptType.FULL
        return show

    def test_validates_dialogue_type(self, registry, mock_show):
        """Test registry routes DIALOGUE type to DialogueValidator."""
        line_json = {
            "line_type": 1,
            "line_parts": [{"character_id": 1, "line_text": "Hello"}],
        }
        result = registry.validate_line(line_json, mock_show)
        assert result.is_valid is True

    def test_validates_stage_direction_type(self, registry, mock_show):
        """Test registry routes STAGE_DIRECTION type to StageDirectionValidator."""
        line_json = {"line_type": 2, "line_parts": [{"line_text": "Enter stage left"}]}
        result = registry.validate_line(line_json, mock_show)
        assert result.is_valid is True

    def test_validates_cue_line_type(self, registry, mock_show):
        """Test registry routes CUE_LINE type to CueLineValidator."""
        line_json = {"line_type": 3, "line_parts": []}
        result = registry.validate_line(line_json, mock_show)
        assert result.is_valid is True

    def test_validates_spacing_type(self, registry, mock_show):
        """Test registry routes SPACING type to SpacingValidator."""
        line_json = {"line_type": 4, "line_parts": []}
        result = registry.validate_line(line_json, mock_show)
        assert result.is_valid is True

    def test_rejects_missing_line_type(self, registry, mock_show):
        """Test registry rejects line with no line_type."""
        line_json = {"line_parts": [{"character_id": 1, "line_text": "Hello"}]}
        result = registry.validate_line(line_json, mock_show)
        assert result.is_valid is False
        assert "Line type is required" in result.error_message

    def test_rejects_invalid_line_type_value(self, registry, mock_show):
        """Test registry rejects line with invalid line_type value."""
        line_json = {"line_type": 99, "line_parts": []}
        result = registry.validate_line(line_json, mock_show)
        assert result.is_valid is False
        assert "Invalid line type: 99" in result.error_message

    def test_handles_all_enum_values(self, registry, mock_show):
        """Test registry has validators for all ScriptLineType enum values."""
        # Verify all enum values have validators
        for line_type in ScriptLineType:
            assert line_type in registry._validators

    def test_dialogue_validation_fails_correctly(self, registry, mock_show):
        """Test registry correctly returns validation failure for invalid dialogue."""
        line_json = {
            "line_type": 1,
            "line_parts": [],  # Invalid: dialogue needs at least one part
        }
        result = registry.validate_line(line_json, mock_show)
        assert result.is_valid is False
        assert "must have at least one line part" in result.error_message

    def test_stage_direction_validation_fails_correctly(self, registry, mock_show):
        """Test registry correctly returns validation failure for invalid stage direction."""
        line_json = {
            "line_type": 2,
            "line_parts": [
                {
                    "character_id": 1,
                    "line_text": "Enter",
                }  # Invalid: stage direction can't have character
            ],
        }
        result = registry.validate_line(line_json, mock_show)
        assert result.is_valid is False
        assert "cannot have characters" in result.error_message

    def test_cue_line_validation_fails_correctly(self, registry, mock_show):
        """Test registry correctly returns validation failure for invalid cue line."""
        line_json = {
            "line_type": 3,
            "line_parts": [{"line_text": "Text"}],  # Invalid: cue line can't have parts
        }
        result = registry.validate_line(line_json, mock_show)
        assert result.is_valid is False
        assert "cannot have line parts" in result.error_message

    def test_spacing_validation_fails_correctly(self, registry, mock_show):
        """Test registry correctly returns validation failure for invalid spacing line."""
        line_json = {
            "line_type": 4,
            "line_parts": [
                {"line_text": "Text"}
            ],  # Invalid: spacing line can't have parts
        }
        result = registry.validate_line(line_json, mock_show)
        assert result.is_valid is False
        assert "cannot have line parts" in result.error_message
