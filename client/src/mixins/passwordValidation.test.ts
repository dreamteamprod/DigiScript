import { describe, it, expect } from 'vitest';
import passwordValidation from './passwordValidation';

describe('passwordValidation mixin', () => {
  const rules = (passwordValidation as any).methods.getPasswordValidations();

  it('rejects passwords shorter than 8 characters', () => {
    expect(rules.minLength('1234567')).toBe(false);
  });

  it('accepts passwords of 8 characters or more', () => {
    expect(rules.minLength('12345678')).toBe(true);
  });
});
