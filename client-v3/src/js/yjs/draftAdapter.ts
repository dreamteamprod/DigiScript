import type { ScriptLine, ScriptLinePart } from '@/types/api/script';
import type { SnapshotLine, SnapshotLinePart } from './yjsSnapshot';

/**
 * A draft line in the shape the existing script components already consume
 * (`ScriptLine`), plus the draft's own identifiers. `id`/`line_parts[].id` stay the DB
 * ids (null for a not-yet-saved line), so viewers, cue code and the MRU character
 * helpers work unchanged.
 *
 * `_uid` is what edits use to find a line or part again: every one has it and it
 * survives a save. `_id` is the DB identity, which a save rewrites in place, so it must
 * not be used to address an edit (or as a Vue `:key`).
 */
export type DraftScriptLinePart = ScriptLinePart & {
  readonly _id: string;
  readonly _uid: string;
};
export type DraftScriptLine = Omit<ScriptLine, 'line_parts'> & {
  readonly _id: string;
  readonly _uid: string;
  line_parts: DraftScriptLinePart[];
};

function partToScriptLinePart(part: SnapshotLinePart, lineId: number | null): DraftScriptLinePart {
  return {
    _id: part._id,
    _uid: part._uid,
    id: part.id,
    line_id: lineId,
    part_index: part.part_index,
    character_id: part.character_id,
    character_group_id: part.character_group_id,
    line_text: part.line_text,
  };
}

/**
 * Convert one snapshot line. `page` is the page the line sits on (the snapshot only
 * knows a line by its position inside a page's array, not the page number).
 */
export function snapshotToScriptLine(page: number | string, line: SnapshotLine): DraftScriptLine {
  return {
    _id: line._id,
    _uid: line._uid,
    id: line.id,
    act_id: line.act_id,
    scene_id: line.scene_id,
    page: Number(page),
    line_type: line.line_type,
    stage_direction_style_id: line.stage_direction_style_id,
    line_parts: line.parts.map((part) => partToScriptLinePart(part, line.id)),
  };
}

export function snapshotPageToScriptLines(
  page: number | string,
  lines: readonly SnapshotLine[]
): DraftScriptLine[] {
  return lines.map((line) => snapshotToScriptLine(page, line));
}

/** Every page of a snapshot record as `ScriptLine`s, keyed the same way (e.g. for MRU sorting). */
export function snapshotPagesToScriptLines(
  pages: Record<string, readonly SnapshotLine[]>
): Record<string, DraftScriptLine[]> {
  return Object.fromEntries(
    Object.entries(pages).map(([page, lines]) => [page, snapshotPageToScriptLines(page, lines)])
  );
}
