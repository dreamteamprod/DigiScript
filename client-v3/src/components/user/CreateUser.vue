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
      <BFormInvalidFeedback>Required, between 8 and 72 characters.</BFormInvalidFeedback>
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

    <BFormGroup v-if="isFirstAdmin" label-cols="4">
      <BFormCheckbox id="telemetry-enabled-input" v-model="state.telemetry_enabled">
        Send anonymous usage statistics to the DigiScript project
      </BFormCheckbox>
      <div class="text-muted small">
        Helps guide development. No show content, user data, or other identifying information is
        ever sent.
        <a href="/help/telemetry" target="_blank" rel="noopener">See what's collected</a>
        — can be changed later in System Settings.
      </div>
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
  // Matches the server's own default (digi_server/settings.py's telemetry_enabled) — this
  // only takes effect when isFirstAdmin, see createUser() below.
  telemetry_enabled: true,
});

const isUsernameUnique = helpers.withMessage(
  'Username already taken',
  (val: string) =>
    val === '' || !users.value.some((u) => u.username.toLowerCase() === val.toLowerCase())
);

const passwordRef = computed(() => state.value.password);

const rules = {
  username: { required, isUsernameUnique },
  password: { required, minLength: minLength(8), maxPasswordByteLength },
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
    // Only meaningful (and only read by the server) on the very first user creation —
    // omitted otherwise so it can never be mistaken for changing an existing install's
    // telemetry setting via the regular "add user" form.
    ...(props.isFirstAdmin ? { telemetry_enabled: state.value.telemetry_enabled } : {}),
  });

  emit('created_user');
}
</script>
