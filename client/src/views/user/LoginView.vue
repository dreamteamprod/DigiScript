<template>
  <b-container
    class="mx-0"
    fluid
  >
    <b-row style="margin-top: 1rem">
      <b-col
        cols="4"
        offset="4"
      >
        <h3>Login to DigiScript</h3>
      </b-col>
    </b-row>
    <b-row style="margin-top: 1rem">
      <b-col
        cols="4"
        offset="4"
      >
        <b-form>
          <b-form-group
            id="username-input-group"
            label="Username"
            label-for="username-input"
          >
            <b-form-input
              id="username-input"
              v-model="$v.state.username.$model"
              name="username-input"
              :state="validateState('username')"
              aria-describedby="username-feedback"
            />
            <b-form-invalid-feedback
              id="username-feedback"
            >
              This is a required field.
            </b-form-invalid-feedback>
          </b-form-group>
          <b-form-group
            id="password-input-group"
            label="Password"
            label-for="password-input"
          >
            <b-form-input
              id="password-input"
              v-model="$v.state.password.$model"
              name="password-input"
              :state="validateState('password')"
              aria-describedby="password-feedback"
              type="password"
            />
            <b-form-invalid-feedback
              id="password-feedback"
            >
              This is a required field.
            </b-form-invalid-feedback>
          </b-form-group>
          <b-button
            :disabled="isDisabled"
            @click="doLogin"
          >
            Login
          </b-button>
        </b-form>
      </b-col>
    </b-row>
    <b-row v-if="showLoginFeedback">
      <b-col>
        <b style="color: darkred">
          Login unsuccessful.
        </b>
      </b-col>
    </b-row>
  </b-container>
</template>

<script>
import { required } from 'vuelidate/lib/validators';
import { mapActions } from 'vuex';

export default {
  name: 'LoginView',
  data() {
    return {
      state: {
        username: '',
        password: '',
      },
      showLoginFeedback: false,
    };
  },
  validations: {
    state: {
      username: {
        required,
      },
      password: {
        required,
      },
    },
  },
  methods: {
    validateState(name) {
      const { $dirty, $error } = this.$v.state[name];
      return $dirty ? !$error : null;
    },
    async doLogin(event) {
      this.$v.state.$touch();
      if (this.$v.state.$anyError) {
        event.preventDefault();
      } else {
        this.showLoginFeedback = false;
        const loginSuccess = await this.USER_LOGIN(this.state);
        if (loginSuccess) {
          this.$router.replace('/');
        } else {
          this.showLoginFeedback = true;
        }
      }
    },
    ...mapActions(['USER_LOGIN']),
  },
  computed: {
    isDisabled() {
      return Boolean(this.$v.state.$invalid);
    },
  },
};
</script>

<style scoped>

</style>
