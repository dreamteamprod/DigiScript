export const notNull = (value: unknown): boolean => value != null;
export const notNullAndGreaterThanZero = (value: unknown): boolean =>
  value != null && (value as number) > 0;
export const maxPasswordByteLength = (value: unknown): boolean =>
  typeof value !== 'string' || new TextEncoder().encode(value).length <= 72;
