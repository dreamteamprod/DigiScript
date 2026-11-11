type VuelidateField = { $dirty: boolean; $error: boolean };

/** A single Vuelidate field's visual validation state: unset until touched. */
export function fieldState(field: VuelidateField): boolean | null {
  return field.$dirty ? !field.$error : null;
}

/** Combined state for two fields where only one of the pair need be valid (e.g. character or group). */
export function combinedFieldState(a: VuelidateField, b: VuelidateField): boolean | null {
  if (!a.$dirty && !b.$dirty) return null;
  return !(a.$error && b.$error);
}
