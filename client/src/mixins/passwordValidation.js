import { required, minLength, sameAs } from 'vuelidate/lib/validators';

/**
 * Mixin for password validation logic used across multiple components
 * Provides consistent validation rules for password fields
 */
export default {
  methods: {
    /**
     * Validate form field state for Bootstrap Vue feedback
     * @param {string} name - Field name to validate
     * @returns {boolean|null} - true if valid, false if invalid, null if untouched
     */
    validateState(name) {
      const { $dirty, $error } = this.$v.state[name];
      return $dirty ? !$error : null;
    },

    /**
     * Get validation rules for new password field
     * @returns {Object} Vuelidate validation rules
     */
    getPasswordValidations() {
      return {
        required,
        minLength: minLength(6),
      };
    },

    /**
     * Get validation rules for confirm password field
     * @param {string} passwordFieldName - Name of password field to match against
     * @returns {Object} Vuelidate validation rules
     */
    getConfirmPasswordValidations(passwordFieldName = 'newPassword') {
      return {
        required,
        sameAsPassword: sameAs(passwordFieldName),
      };
    },
  },
};
