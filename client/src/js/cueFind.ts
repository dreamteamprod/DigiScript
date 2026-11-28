import type { CueType } from '@/types/api/cues';

export type FindQuery =
  | { kind: 'empty' }
  /** A number was typed with no cue type: ask which type it is. */
  | { kind: 'needs-type'; number: string }
  /** A cue type prefix was typed with no number: ask for one. */
  | { kind: 'needs-number'; types: CueType[] }
  | { kind: 'search'; types: CueType[]; number: string };

/**
 * Parse text such as "LX 13.5": the longest cue type prefix at the start
 * (ignoring case) is the type, and the rest, trimmed, is the number. Several types
 * sharing that prefix are all searched.
 */
export function parseFindQuery(input: string, cueTypes: readonly CueType[]): FindQuery {
  const text = input.trim();
  if (!text) return { kind: 'empty' };

  const lower = text.toLowerCase();
  let longest = 0;
  for (const type of cueTypes) {
    const prefix = type.prefix?.trim().toLowerCase();
    if (prefix && lower.startsWith(prefix)) longest = Math.max(longest, prefix.length);
  }
  if (longest === 0) return { kind: 'needs-type', number: text };

  const types = cueTypes.filter((t) => {
    const prefix = (t.prefix ?? '').trim().toLowerCase();
    // `longest` is at least 1, so a blank prefix never matches.
    return prefix.length === longest && lower.startsWith(prefix);
  });
  const number = text.slice(longest).trim();
  return number ? { kind: 'search', types, number } : { kind: 'needs-number', types };
}

export interface FindLocation {
  page: number | null;
  line_id: number;
  act_id: number | null;
  scene_id: number | null;
}

export interface FindMatch {
  cue: { id: number; ident: string | null; cue_type_id: number | null };
  cue_type: CueType;
  location: FindLocation;
  similarity_score?: number;
}

export interface FindResponse {
  exact_matches: FindMatch[];
  suggestions: FindMatch[];
}

/** Merge the responses for several cue types sharing a prefix. */
export function mergeFindResponses(responses: readonly FindResponse[]): FindResponse {
  const exact = responses.flatMap((r) => r.exact_matches ?? []);
  const suggestions = responses
    .flatMap((r) => r.suggestions ?? [])
    .sort((a, b) => (b.similarity_score ?? 0) - (a.similarity_score ?? 0))
    .slice(0, 5);
  return { exact_matches: exact, suggestions };
}
