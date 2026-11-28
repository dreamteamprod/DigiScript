import { describe, it, expect } from 'vitest';
import { presenceInitials, presenceColor, SELF_AVATAR_COLOR } from './presenceUtils';

describe('presenceUtils', () => {
  describe('presenceInitials', () => {
    it('takes the first two characters of a bare username', () => {
      expect(presenceInitials('tbradgate')).toBe('TB');
      expect(presenceInitials('admin')).toBe('AD');
    });

    it('takes the first letter of each of the first two words for a "first last" name', () => {
      expect(presenceInitials('Tim Bradgate')).toBe('TB');
      expect(presenceInitials('  Kiran   Patel  ')).toBe('KP');
    });

    it('upper-cases the result', () => {
      expect(presenceInitials('jsmith')).toBe('JS');
    });

    it('handles a single-character name without throwing', () => {
      expect(presenceInitials('a')).toBe('A');
    });

    it('handles an empty string without throwing', () => {
      expect(presenceInitials('')).toBe('');
    });
  });

  describe('presenceColor', () => {
    it('is deterministic for the same name', () => {
      expect(presenceColor('tbradgate')).toBe(presenceColor('tbradgate'));
    });

    it('returns a hex colour from the fixed palette', () => {
      expect(presenceColor('jsmith')).toMatch(/^#[0-9a-f]{6}$/i);
    });

    it('is not the colour reserved for the current user', () => {
      // Every palette entry must differ from SELF_AVATAR_COLOR, or some other
      // member's avatar could be mistaken for "you" — check a spread of inputs
      // rather than relying on knowing the hash's internals.
      const names = ['tbradgate', 'jsmith', 'kpatel', 'admin', 'a', 'zzzzzzzz', ''];
      names.forEach((name) => {
        expect(presenceColor(name).toLowerCase()).not.toBe(SELF_AVATAR_COLOR.toLowerCase());
      });
    });

    it('does not throw for an empty string', () => {
      expect(() => presenceColor('')).not.toThrow();
    });
  });
});
