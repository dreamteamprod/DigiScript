import { defineComponent } from 'vue';
import { required, minLength, sameAs } from 'vuelidate/lib/validators';

export default defineComponent({
  methods: {
    validateState(name: string): boolean | null {
      const { $dirty, $error } = (this as any).$v.state[name];
      return $dirty ? !$error : null;
    },

    getPasswordValidations() {
      return {
        required,
        minLength: minLength(6),
      };
    },

    getConfirmPasswordValidations(passwordFieldName = 'newPassword') {
      return {
        required,
        sameAsPassword: sameAs(passwordFieldName),
      };
    },
  },
});
