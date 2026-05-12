declare module 'deep-object-diff' {
  export function detailedDiff(
    a: unknown,
    b: unknown
  ): {
    added: Record<string, unknown>;
    updated: Record<string, unknown>;
    deleted: Record<string, unknown>;
  };
  export function diff(a: unknown, b: unknown): Record<string, unknown>;
}
