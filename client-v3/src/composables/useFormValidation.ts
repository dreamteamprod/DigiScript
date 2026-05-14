export function useFormValidation() {
  function validationState(
    field: { $dirty: boolean; $error: boolean } | undefined
  ): boolean | null {
    if (!field) return null;
    return field.$dirty ? !field.$error : null;
  }

  return { validationState };
}
