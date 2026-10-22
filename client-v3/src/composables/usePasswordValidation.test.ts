import { describe, it, expect } from 'vitest';
import { usePasswordValidation } from './usePasswordValidation';

describe('usePasswordValidation', () => {
  const { passwordRules } = usePasswordValidation();

  it('rejects passwords shorter than 8 characters', () => {
    expect(passwordRules.minLength.$validator('1234567', undefined, undefined)).toBe(false);
  });

  it('accepts passwords of 8 characters or more', () => {
    expect(passwordRules.minLength.$validator('12345678', undefined, undefined)).toBe(true);
  });
});
