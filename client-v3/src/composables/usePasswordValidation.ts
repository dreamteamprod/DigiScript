import { computed } from 'vue';
import { required, minLength, sameAs } from '@vuelidate/validators';
import { maxPasswordByteLength } from '@/js/customValidators';

export function usePasswordValidation() {
  const passwordRules = { required, minLength: minLength(6), maxPasswordByteLength };

  function confirmPasswordRules(getPasswordValue: () => string) {
    return computed(() => ({ required, sameAsPassword: sameAs(getPasswordValue()) }));
  }

  return { passwordRules, confirmPasswordRules };
}
