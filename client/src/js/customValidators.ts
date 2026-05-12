export const notNull = (value: unknown): boolean => value != null;
export const notNullAndGreaterThanZero = (value: unknown): boolean =>
  value != null && (value as number) > 0;
