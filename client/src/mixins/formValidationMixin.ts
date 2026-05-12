import { defineComponent } from 'vue';

export default defineComponent({
  methods: {
    getValidationState(formStateKey: string, fieldName: string): boolean | null {
      const field = (this as any).$v?.[formStateKey]?.[fieldName];
      if (!field) return null;
      const { $dirty, $error } = field;
      return $dirty ? !$error : null;
    },

    resetForm(formStateKey: string, initialState: Record<string, unknown>): void {
      (this as any)[formStateKey] = { ...initialState };
      this.$nextTick(() => {
        (this as any).$v.$reset();
      });
    },

    hasFormErrors(formStateKey: string): boolean {
      (this as any).$v[formStateKey].$touch();
      return (this as any).$v[formStateKey].$anyError;
    },
  },
});
