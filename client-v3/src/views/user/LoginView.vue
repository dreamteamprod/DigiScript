<template>
  <BContainer class="mx-0" fluid>
    <BRow style="margin-top: 1rem">
      <BCol cols="4" offset="4">
        <h3>Login to DigiScript</h3>
      </BCol>
    </BRow>
    <BRow style="margin-top: 1rem">
      <BCol cols="4" offset="4">
        <BForm @submit.prevent="doLogin">
          <BFormGroup id="username-input-group" label="Username" label-for="username-input">
            <BFormInput
              id="username-input"
              v-model="v$.username.$model"
              name="username-input"
              :state="validationState(v$.username)"
              aria-describedby="username-feedback"
              @keydown.enter="doLogin"
            />
            <BFormInvalidFeedback id="username-feedback">
              This is a required field.
            </BFormInvalidFeedback>
          </BFormGroup>
          <BFormGroup id="password-input-group" label="Password" label-for="password-input">
            <BFormInput
              id="password-input"
              v-model="v$.password.$model"
              name="password-input"
              :state="validationState(v$.password)"
              aria-describedby="password-feedback"
              type="password"
              @keydown.enter="doLogin"
            />
            <BFormInvalidFeedback id="password-feedback">
              This is a required field.
            </BFormInvalidFeedback>
          </BFormGroup>
          <BButton :disabled="v$.$invalid" @click="doLogin"> Login </BButton>
        </BForm>
      </BCol>
    </BRow>
    <BRow v-if="showLoginFeedback">
      <BCol>
        <b style="color: darkred"> Login unsuccessful. </b>
      </BCol>
    </BRow>
  </BContainer>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { useVuelidate } from '@vuelidate/core';
import { required } from '@vuelidate/validators';
import { useUserStore } from '@/stores/user';
import { useFormValidation } from '@/composables/useFormValidation';

const router = useRouter();
const userStore = useUserStore();
const { validationState } = useFormValidation();

const state = ref({ username: '', password: '' });
const rules = { username: { required }, password: { required } };
const v$ = useVuelidate(rules, state);

const showLoginFeedback = ref(false);

async function doLogin(): Promise<void> {
  v$.value.$touch();
  if (v$.value.$invalid) return;
  showLoginFeedback.value = false;
  const success = await userStore.login(state.value.username, state.value.password);
  if (success) {
    router.replace('/');
  } else {
    showLoginFeedback.value = true;
  }
}
</script>

<style scoped></style>
