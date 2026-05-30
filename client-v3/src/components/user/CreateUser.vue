<template>
  <BForm @submit.prevent="createUser">
    <BFormGroup label="Username" label-for="username-input" label-cols="4">
      <BFormInput
        id="username-input"
        v-model="state.username"
        name="username-input"
        :state="fieldState('username')"
        :disabled="isFirstAdmin"
      />
      <BFormInvalidFeedback>Required and must be a unique username.</BFormInvalidFeedback>
    </BFormGroup>

    <BFormGroup label="Password" label-for="password-input" label-cols="4">
      <BFormInput
        id="password-input"
        v-model="state.password"
        name="password-input"
        type="password"
        :state="fieldState('password')"
      />
      <BFormInvalidFeedback>Required, between 6 and 72 characters.</BFormInvalidFeedback>
    </BFormGroup>

    <BFormGroup label="Confirm Password" label-for="confirm-password-input" label-cols="4">
      <BFormInput
        id="confirm-password-input"
        v-model="state.confirmPassword"
        name="confirm-password-input"
        type="password"
        :state="fieldState('confirmPassword')"
      />
      <BFormInvalidFeedback>Passwords do not match.</BFormInvalidFeedback>
    </BFormGroup>

    <BButtonGroup>
      <BButton variant="success" :disabled="v$.$invalid" @click.stop.prevent="createUser">
        Save
      </BButton>
    </BButtonGroup>
  </BForm>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { useVuelidate } from '@vuelidate/core';
import { required, minLength, sameAs, helpers } from '@vuelidate/validators';
import { maxPasswordByteLength } from '@/js/customValidators';
import { storeToRefs } from 'pinia';
import { useUserStore } from '@/stores/user';

const props = withDefaults(
  defineProps<{
    isFirstAdmin?: boolean;
    isAdmin?: boolean;
  }>(),
  { isFirstAdmin: false, isAdmin: false }
);

const emit = defineEmits<{ (e: 'created_user'): void }>();

const userStore = useUserStore();
const { users } = storeToRefs(userStore);

const state = ref({
  username: props.isFirstAdmin ? 'admin' : '',
  password: '',
  confirmPassword: '',
  is_admin: props.isFirstAdmin || props.isAdmin,
});

const isUsernameUnique = helpers.withMessage(
  'Username already taken',
  (val: string) =>
    val === '' || !users.value.some((u) => u.username.toLowerCase() === val.toLowerCase())
);

const passwordRef = computed(() => state.value.password);

const rules = {
  username: { required, isUsernameUnique },
  password: { required, minLength: minLength(6), maxPasswordByteLength },
  confirmPassword: { required, sameAs: sameAs(passwordRef) },
};

const v$ = useVuelidate(rules, state);

function fieldState(key: 'username' | 'password' | 'confirmPassword'): boolean | null {
  const field = v$.value[key];
  return field.$dirty ? !field.$error : null;
}

async function createUser(): Promise<void> {
  const valid = await v$.value.$validate();
  if (!valid) return;

  await userStore.createUser({
    username: state.value.username,
    password: state.value.password,
    is_admin: state.value.is_admin,
  });

  emit('created_user');
}
</script>
