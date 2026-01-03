"""Line type validation using Strategy pattern."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from models.script import ScriptLineType
from models.show import ShowScriptType


@dataclass
class LineTypeValidationResult:
    """Result of line type validation.

    :param is_valid: Whether the line passed validation
    :param error_message: Error message if validation failed
    """

    is_valid: bool
    error_message: str = ""


class BaseLineTypeValidator(ABC):
    """Abstract base class for line type validators."""

    @abstractmethod
    def validate(self, line_json: dict, show) -> LineTypeValidationResult:
        """Validate a line based on type-specific rules.

        :param line_json: Line data from API request
        :param show: Show model instance
        :return: Validation result
        """
        pass


class DialogueValidator(BaseLineTypeValidator):
    """Validator for DIALOGUE lines."""

    def validate(self, line_json: dict, show) -> LineTypeValidationResult:
        line_parts = line_json.get("line_parts", [])

        if len(line_parts) == 0:
            return LineTypeValidationResult(
                is_valid=False,
                error_message="Dialogue lines must have at least one line part",
            )

        if show.script_mode == ShowScriptType.COMPACT and len(line_parts) > 1:
            return LineTypeValidationResult(
                is_valid=False,
                error_message="Lines can only have 1 line part in compact script mode",
            )

        for line_part in line_parts:
            if line_part.get("line_text") is None:
                if len(line_parts) == 1:
                    return LineTypeValidationResult(
                        is_valid=False, error_message="Dialogue lines must contain text"
                    )
                if not any(lp.get("line_text") is not None for lp in line_parts):
                    return LineTypeValidationResult(
                        is_valid=False,
                        error_message="At least one line part must contain text",
                    )

            has_character = line_part.get("character_id") is not None
            has_group = line_part.get("character_group_id") is not None

            if not has_character and not has_group:
                return LineTypeValidationResult(
                    is_valid=False,
                    error_message="Dialogue line parts must have a character or character group",
                )
            if has_character and has_group:
                return LineTypeValidationResult(
                    is_valid=False,
                    error_message="Line parts cannot have both character and character group",
                )

        return LineTypeValidationResult(is_valid=True)


class StageDirectionValidator(BaseLineTypeValidator):
    """Validator for STAGE_DIRECTION lines."""

    def validate(self, line_json: dict, show) -> LineTypeValidationResult:
        line_parts = line_json.get("line_parts", [])

        if len(line_parts) != 1:
            return LineTypeValidationResult(
                is_valid=False,
                error_message="Stage directions must have exactly 1 line part",
            )

        line_part = line_parts[0]

        if line_part.get("character_id") is not None:
            return LineTypeValidationResult(
                is_valid=False, error_message="Stage directions cannot have characters"
            )
        if line_part.get("character_group_id") is not None:
            return LineTypeValidationResult(
                is_valid=False,
                error_message="Stage directions cannot have character groups",
            )

        line_text = line_part.get("line_text")
        if line_text is None or (
            isinstance(line_text, str) and line_text.strip() == ""
        ):
            return LineTypeValidationResult(
                is_valid=False, error_message="Stage directions must contain text"
            )

        return LineTypeValidationResult(is_valid=True)


class CueLineValidator(BaseLineTypeValidator):
    """Validator for CUE_LINE lines."""

    def validate(self, line_json: dict, show) -> LineTypeValidationResult:
        line_parts = line_json.get("line_parts", [])

        if len(line_parts) > 0:
            return LineTypeValidationResult(
                is_valid=False, error_message="Cue lines cannot have line parts"
            )

        return LineTypeValidationResult(is_valid=True)


class SpacingValidator(BaseLineTypeValidator):
    """Validator for SPACING lines."""

    def validate(self, line_json: dict, show) -> LineTypeValidationResult:
        line_parts = line_json.get("line_parts", [])

        if len(line_parts) > 0:
            return LineTypeValidationResult(
                is_valid=False, error_message="Spacing lines cannot have line parts"
            )

        return LineTypeValidationResult(is_valid=True)


class LineTypeValidatorRegistry:
    """Registry of validators for each LineType."""

    def __init__(self):
        self._validators = {
            ScriptLineType.DIALOGUE: DialogueValidator(),
            ScriptLineType.STAGE_DIRECTION: StageDirectionValidator(),
            ScriptLineType.CUE_LINE: CueLineValidator(),
            ScriptLineType.SPACING: SpacingValidator(),
        }

    def validate_line(self, line_json: dict, show) -> LineTypeValidationResult:
        """Validate a line using the appropriate type-specific validator.

        :param line_json: Line data with "line_type" key
        :param show: Show model instance
        :return: Validation result
        """
        line_type_value = line_json.get("line_type")
        if line_type_value is None:
            return LineTypeValidationResult(
                is_valid=False, error_message="Line type is required"
            )

        try:
            line_type = ScriptLineType(line_type_value)
        except ValueError:
            return LineTypeValidationResult(
                is_valid=False, error_message=f"Invalid line type: {line_type_value}"
            )

        validator = self._validators.get(line_type)
        if validator is None:
            return LineTypeValidationResult(
                is_valid=False, error_message=f"No validator for line type: {line_type}"
            )

        return validator.validate(line_json, show)
