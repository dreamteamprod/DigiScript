import { computed } from 'vue';
import { required, minLength, sameAs } from '@vuelidate/validators';

export function usePasswordValidation() {
  const passwordRules = { required, minLength: minLength(6) };

  function confirmPasswordRules(getPasswordValue: () => string) {
    return computed(() => ({ required, sameAsPassword: sameAs(getPasswordValue()) }));
  }

  return { passwordRules, confirmPasswordRules };
}
