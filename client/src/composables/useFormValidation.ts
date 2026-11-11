function validationState(field: { $dirty: boolean; $error: boolean } | undefined): boolean | null {
  if (!field) return null;
  return field.$dirty ? !field.$error : null;
}

export function useFormValidation() {
  return { validationState };
}
