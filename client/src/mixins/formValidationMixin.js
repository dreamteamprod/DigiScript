/**
 * Mixin providing common form validation helper methods for Vuelidate.
 *
 * This mixin centralizes the repeated validation and form reset patterns used
 * across multiple components that handle new/edit forms.
 *
 * Usage:
 * 1. Import and include in your component's mixins array
 * 2. Define your form state properties (e.g., newFormState, editFormState)
 * 3. Define your validations object as usual
 * 4. Use the helper methods in your template and component logic
 *
 * Example:
 *   import formValidationMixin from '@/mixins/formValidationMixin';
 *
 *   export default {
 *     mixins: [formValidationMixin],
 *     data() {
 *       return {
 *         newFormState: { name: '' },
 *         editFormState: { id: null, name: '' },
 *       };
 *     },
 *     validations: {
 *       newFormState: { name: { required } },
 *       editFormState: { name: { required } },
 *     },
 *     methods: {
 *       resetNewForm() {
 *         this.resetForm('newFormState', { name: '' });
 *       },
 *     },
 *   };
 */
export default {
  methods: {
    /**
     * Get Bootstrap validation state for a form field.
     *
     * @param {string} formStateKey - The validation group key (e.g., 'newFormState', 'editFormState')
     * @param {string} fieldName - The field name within the validation group
     * @returns {boolean|null} - true if valid, false if invalid, null if pristine
     */
    getValidationState(formStateKey, fieldName) {
      const field = this.$v[formStateKey][fieldName];
      if (!field) {
        return null;
      }
      const { $dirty, $error } = field;
      return $dirty ? !$error : null;
    },

    /**
     * Reset a form to its initial state and reset validation.
     *
     * @param {string} formStateKey - The data property key (e.g., 'newFormState')
     * @param {Object} initialState - The initial state object to reset to
     */
    resetForm(formStateKey, initialState) {
      this[formStateKey] = { ...initialState };
      this.$nextTick(() => {
        this.$v.$reset();
      });
    },

    /**
     * Check if a form has validation errors after touching all fields.
     *
     * @param {string} formStateKey - The validation group key
     * @returns {boolean} - true if the form has any validation errors
     */
    hasFormErrors(formStateKey) {
      this.$v[formStateKey].$touch();
      return this.$v[formStateKey].$anyError;
    },
  },
};
