import { defineComponent } from 'vue';
import { required, minLength, sameAs } from 'vuelidate/lib/validators';
import { maxPasswordByteLength } from '@/js/customValidators';

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
        maxPasswordByteLength,
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
