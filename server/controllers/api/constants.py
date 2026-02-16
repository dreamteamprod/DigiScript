"""
Error message constants for API controllers.

This module centralizes error messages to reduce code duplication across controllers.
All error messages follow the existing API contract patterns.
"""

# =============================================================================
# HTTP 404 Not Found Errors
# =============================================================================

# Core entities
ERROR_SHOW_NOT_FOUND = "404 show not found"
ERROR_ACT_NOT_FOUND = "404 act not found"
ERROR_SCENE_NOT_FOUND = "404 scene not found"

# People
ERROR_CAST_MEMBER_NOT_FOUND = "404 cast member not found"
ERROR_CHARACTER_NOT_FOUND = "404 character not found"
ERROR_CHARACTER_GROUP_NOT_FOUND = "404 character group not found"
ERROR_CREW_NOT_FOUND = "404 crew member not found"

# Script
ERROR_SCRIPT_NOT_FOUND = "404 script not found"
ERROR_SCRIPT_REVISION_NOT_FOUND = "404 script revision not found"
ERROR_STAGE_DIRECTION_STYLE_NOT_FOUND = "404 stage direction style not found"

# Cues
ERROR_CUE_NOT_FOUND = "404 cue not found"
ERROR_CUE_TYPE_NOT_FOUND = "404 cue type not found"

# Microphones
ERROR_MICROPHONE_NOT_FOUND = "404 microphone not found"

# Tags
ERROR_TAG_NOT_FOUND = "404 tag not found"

# Stage: Props
ERROR_PROP_NOT_FOUND = "404 prop not found"
ERROR_PROPS_NOT_FOUND = "404 props not found"
ERROR_PROP_TYPE_NOT_FOUND = "404 prop type not found"

# Stage: Scenery
ERROR_SCENERY_NOT_FOUND = "404 scenery not found"
ERROR_SCENERY_TYPE_NOT_FOUND = "404 scenery type not found"

# Allocations
ERROR_ALLOCATION_NOT_FOUND = "404 allocation not found"

# Crew assignments
ERROR_CREW_ASSIGNMENT_NOT_FOUND = "404 crew assignment not found"


# =============================================================================
# HTTP 400 Validation Errors - Missing Required Fields
# =============================================================================

# Generic
ERROR_ID_MISSING = "ID missing"
ERROR_NAME_MISSING = "Name missing"
ERROR_INVALID_ID = "Invalid ID"

# People
ERROR_FIRST_NAME_MISSING = "First name missing"
ERROR_LAST_NAME_MISSING = "Last name missing"

# Appearance
ERROR_COLOUR_MISSING = "Colour missing"
ERROR_DESCRIPTION_MISSING = "Description missing"

# Acts/Scenes
ERROR_ACT_ID_MISSING = "Act ID missing"
ERROR_SCENE_ID_MISSING = "Scene ID missing"

# Cues
ERROR_PREFIX_MISSING = "Prefix missing"
ERROR_CUE_TYPE_MISSING = "Cue Type missing"
ERROR_CUE_ID_MISSING = "Cue ID missing"
ERROR_IDENTIFIER_MISSING = "Identifier missing"
ERROR_LINE_ID_MISSING = "Line ID missing"

# Stage direction styles
ERROR_TEXT_FORMAT_INVALID = "Text format missing or invalid"
ERROR_TEXT_COLOUR_MISSING = "Text colour missing"
ERROR_BACKGROUND_COLOUR_MISSING = "Background colour missing"

# Tags
ERROR_TAG_NAME_MISSING = "Tag name missing"

# Props/Scenery
ERROR_PROP_TYPE_ID_MISSING = "Prop type ID missing"
ERROR_SCENERY_TYPE_ID_MISSING = "Scenery type ID missing"

# Allocations
ERROR_PROPS_ID_MISSING = "props_id missing"
ERROR_SCENERY_ID_MISSING = "scenery_id missing"

# Crew assignments
ERROR_CREW_ID_MISSING = "crew_id missing"
ERROR_ASSIGNMENT_TYPE_MISSING = "assignment_type missing"
ERROR_ASSIGNMENT_TYPE_INVALID = "assignment_type must be 'set' or 'strike'"
ERROR_ITEM_ID_MISSING = "Either prop_id or scenery_id must be provided"
ERROR_ITEM_ID_BOTH = "Only one of prop_id or scenery_id can be provided"
ERROR_INVALID_BOUNDARY = "Scene is not a valid boundary for this assignment type"
ERROR_CREW_ASSIGNMENT_EXISTS = "Crew assignment already exists"


# =============================================================================
# HTTP 400 Conflict/Business Rule Errors
# =============================================================================

ERROR_NAME_ALREADY_TAKEN = "Name already taken"
ERROR_TAG_NAME_EXISTS = "Tag name already exists (case-insensitive)"
ERROR_SCRIPT_DRAFT_ACTIVE = (
    "409 cannot modify script while collaborative edit in progress"
)

# =============================================================================
# WebSocket Edit/Cuts Mode Errors
# =============================================================================

ERROR_EDIT_BLOCKED_BY_CUTTER = "Cannot edit: another user is in cuts mode"
ERROR_CUTS_BLOCKED_BY_EDITOR = "Cannot enter cuts mode: another user is editing"
ERROR_CUTS_BLOCKED_BY_CUTTER = "Cannot enter cuts mode: another user is already cutting"
ERROR_CUTS_BLOCKED_BY_DRAFT = "Cannot enter cuts mode: unsaved draft exists"
