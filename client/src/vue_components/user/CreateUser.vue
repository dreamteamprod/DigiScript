<template>
  <b-form>
    <b-form-group
      id="username-input-group"
      label="Username"
      label-for="username-input"
      :label-cols="true"
    >
      <b-form-input
        id="username-input"
        v-model="$v.state.username.$model"
        name="username-input"
        :state="validateState('username')"
        aria-describedby="username-feedback"
        :disabled="is_first_admin"
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
      :label-cols="true"
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
        This is a required field and must be at least 6 characters.
      </b-form-invalid-feedback>
    </b-form-group>
    <b-form-group
      id="confirm-password-input-group"
      label="Confirm Password"
      label-for="confirm-password-input"
      :label-cols="true"
    >
      <b-form-input
        id="confirm-password-input"
        v-model="$v.state.confirmPassword.$model"
        name="confirm-password-input"
        :state="validateState('confirmPassword')"
        aria-describedby="confirm-password-feedback"
        type="password"
      />
      <b-form-invalid-feedback
        id="confirm-password-feedback"
      >
        Passwords to not match.
      </b-form-invalid-feedback>
    </b-form-group>
    <b-button-group>
      <b-button
        variant="success"
        :disabled="isDisabled"
        @click.stop.prevent="createUser"
      >
        Save
      </b-button>
    </b-button-group>
  </b-form>
</template>

<script>
import { required, minLength, sameAs } from 'vuelidate/lib/validators';
import { mapActions } from 'vuex';

export default {
  name: 'CreateUser',
  props: {
    is_first_admin: {
      type: Boolean,
      default: false,
    },
    show_id: {
      type: Number,
      required: false,
      default: null,
    },
  },
  data() {
    return {
      state: {
        username: this.is_first_admin ? 'admin' : '',
        password: '',
        confirmPassword: '',
        show_id: this.show_id,
        is_admin: this.is_first_admin,
      },
    };
  },
  validations: {
    state: {
      username: {
        required,
      },
      password: {
        required,
        minLength: minLength(6),
      },
      confirmPassword: {
        required,
        sameAsPassword: sameAs('password'),
      },
    },
  },
  methods: {
    validateState(name) {
      const { $dirty, $error } = this.$v.state[name];
      return $dirty ? !$error : null;
    },
    async createUser(event) {
      this.$v.state.$touch();
      if (this.$v.state.$anyError) {
        event.preventDefault();
      } else {
        await this.CREATE_USER(this.state);
        this.$emit('created_user');
      }
    },
    ...mapActions(['CREATE_USER']),
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
