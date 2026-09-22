"""Shared helpers for creating and validating script lines.

These functions are called both by the REST PATCH/POST endpoints
(``ScriptController``) and by the collaborative save path
(``_save_script_page`` in ``ydoc_to_lines``).

Extracting them here avoids a circular import between the controller
module and the save utilities.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from models.script import (
    ScriptLine,
    ScriptLinePart,
    ScriptLineRevisionAssociation,
    ScriptLineType,
)
from utils.show.line_type_validator import LineTypeValidatorRegistry


if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from models.script import ScriptRevision
    from models.show import Show


def validate_line(show: Show, line_json: dict) -> tuple[bool, str]:
    """Validate a script line JSON dict against show constraints.

    :param show: Show model instance.
    :param line_json: Dict with line fields (same shape as the REST API body).
    :returns: ``(is_valid, error_message)`` tuple.
    """
    registry = LineTypeValidatorRegistry()
    result = registry.validate_line(line_json, show)
    return result.is_valid, result.error_message


def create_new_line(
    session: Session,
    revision: ScriptRevision,
    line: dict,
    previous_line: ScriptLineRevisionAssociation | None,
    with_association: bool = True,
) -> tuple[ScriptLineRevisionAssociation | None, ScriptLine]:
    """Create a new ``ScriptLine`` and optionally its revision association.

    Mirrors the logic in ``ScriptController._create_new_line``.  Both the
    REST endpoint and the collaborative save path use this function so the
    line-creation logic stays in one place.

    :param session: Active SQLAlchemy session.
    :param revision: The target ``ScriptRevision``.
    :param line: Dict of line fields (``act_id``, ``scene_id``, ``page``,
        ``line_type``, ``stage_direction_style_id``, ``line_parts``).
    :param previous_line: Preceding ``ScriptLineRevisionAssociation`` used to
        set linked-list ``next_line`` / ``previous_line`` pointers.
    :param with_association: When ``True`` (default) a
        ``ScriptLineRevisionAssociation`` is created and its pointers set.
        Pass ``False`` when the caller will manage the association itself
        (e.g. the PATCH "updated" branch).
    :returns: ``(association_or_None, line_object)`` tuple.
    """
    line_obj = ScriptLine(
        act_id=line["act_id"],
        scene_id=line["scene_id"],
        page=line["page"],
        line_type=ScriptLineType(line["line_type"]),
        stage_direction_style_id=line["stage_direction_style_id"],
    )
    session.add(line_obj)
    session.flush()

    line_association = None
    if with_association:
        line_association = ScriptLineRevisionAssociation(
            revision_id=revision.id, line_id=line_obj.id
        )
        session.add(line_association)
        session.flush()

        if previous_line:
            previous_line.next_line = line_obj
            line_association.previous_line = previous_line.line
            session.flush()

    for line_part in line["line_parts"]:
        part_obj = ScriptLinePart(
            line_id=line_obj.id,
            part_index=line_part["part_index"],
            character_id=line_part["character_id"],
            character_group_id=line_part["character_group_id"],
            line_text=line_part["line_text"],
        )
        session.add(part_obj)
        line_obj.line_parts.append(part_obj)

    session.flush()
    return line_association, line_obj
