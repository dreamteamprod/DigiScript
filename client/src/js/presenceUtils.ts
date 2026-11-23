/**
 * A fixed, hash-stable palette for other room members' avatars. Deliberately
 * excludes green (`SELF_AVATAR_COLOR`, reserved for "you"), orange (the
 * editing-badge colour used by `CollabScriptLineEditor`/`ScriptLineViewer`) and
 * blue (the cutting-badge colour) so an avatar's own colour is never mistaken for
 * one of those status badges. Easy to retune: add, remove or reorder entries —
 * `presenceColor` below only depends on the array's length and order being
 * consistent across clients, not on any particular value.
 */
const PRESENCE_PALETTE = [
  '#f06ea9', // pink
  '#c4a3f5', // lilac
  '#b4d33a', // lime
  '#4fb8a8', // teal
  '#8d7bf0', // indigo
  '#f2876b', // coral
] as const;

/** Always used for the current user's own avatar, never drawn from the hash below. */
export const SELF_AVATAR_COLOR = '#54b98f';

/**
 * Deterministic initials for a presence avatar: the first letter of each of the
 * first two words for a "first last"-style name, or the first two characters of a
 * single bare username (e.g. `"tbradgate"` -> `"TB"`) — this app's usernames are
 * plain login names with no spaces, so the second form is the common case.
 */
export function presenceInitials(name: string): string {
  const trimmed = name.trim();
  const words = trimmed.split(/\s+/).filter(Boolean);
  if (words.length >= 2) {
    return (words[0]![0]! + words[1]![0]!).toUpperCase();
  }
  return trimmed.slice(0, 2).toUpperCase();
}

/**
 * A stable colour for `name`, picked from `PRESENCE_PALETTE` by a simple string
 * hash — the same name always maps to the same colour on every client, with no
 * shared state needed to agree on it.
 */
export function presenceColor(name: string): string {
  let hash = 0;
  for (let i = 0; i < name.length; i += 1) {
    hash = (hash * 31 + name.charCodeAt(i)) | 0;
  }
  const index = Math.abs(hash) % PRESENCE_PALETTE.length;
  return PRESENCE_PALETTE[index]!;
}
