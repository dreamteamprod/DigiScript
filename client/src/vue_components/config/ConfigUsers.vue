<template>
  <b-container
    class="mx-0"
    fluid
  >
    <b-row>
      <b-col>
        <b-table
          id="cast-table"
          :items="SHOW_USERS"
          :fields="userFields"
          show-empty
        >
          <template #head(btn)="data">
            <b-button
              v-b-modal.new-user
              variant="outline-success"
            >
              New User
            </b-button>
          </template>
          <template #cell(btn)="data">
            <b-button-group>
              <b-button
                v-b-modal.user-rbac
                variant="warning"
                :disabled="data.item.is_admin"
                @click.stop="setEditUser(data.item.id)"
              >
                RBAC
              </b-button>
              <b-button
                v-b-modal.reset-password
                variant="info"
                :disabled="data.item.id === CURRENT_USER.id"
                @click.stop="setResetUser(data.item)"
              >
                Reset Password
              </b-button>
              <b-button
                variant="danger"
                :disabled="data.item.is_admin"
                @click.stop="deleteUser(data)"
              >
                Delete
              </b-button>
            </b-button-group>
          </template>
        </b-table>
      </b-col>
    </b-row>
    <b-modal
      id="new-user"
      ref="new-user"
      title="Add New User"
      size="md"
      hide-footer
    >
      <create-user
        :is_first_admin="false"
        @created_user="resetNewForm"
      />
    </b-modal>
    <b-modal
      id="user-rbac"
      ref="user-rbac"
      title="User RBAC Config"
      size="xl"
      hide-footer
    >
      <config-rbac :user-id="editUser" />
    </b-modal>
    <b-modal
      id="reset-password"
      ref="reset-password"
      title="Reset User Password"
      size="md"
      hide-footer
    >
      <reset-password
        v-if="resetUser"
        :user-id="resetUser.id"
        :username="resetUser.username"
        @cancel="closeResetPasswordModal"
        @password-reset="handlePasswordReset"
        @done="closeResetPasswordModal"
      />
    </b-modal>
  </b-container>
</template>

<script>
import { mapActions, mapGetters } from 'vuex';

import CreateUser from '@/vue_components/user/CreateUser.vue';
import ConfigRbac from '@/vue_components/user/ConfigRbac.vue';
import ResetPassword from '@/vue_components/user/ResetPassword.vue';

export default {
  name: 'ConfigUsers',
  components: { CreateUser, ConfigRbac, ResetPassword },
  data() {
    return {
      userFields: [
        'username',
        'last_login',
        'last_seen',
        'is_admin',
        { key: 'btn', label: '' },
      ],
      editUser: null,
      resetUser: null,
      clientTimeout: null,
    };
  },
  computed: {
    ...mapGetters(['SHOW_USERS', 'CURRENT_SHOW', 'CURRENT_USER']),
  },
  async mounted() {
    await this.getUsers();
  },
  destroyed() {
    clearTimeout(this.clientTimeout);
  },
  methods: {
    resetNewForm() {
      this.$bvModal.hide('new-user');
    },
    setEditUser(userId) {
      this.editUser = userId;
    },
    setResetUser(user) {
      this.resetUser = user;
    },
    async handlePasswordReset() {
      await this.getUsers();
    },
    closeResetPasswordModal() {
      this.$bvModal.hide('reset-password');
      this.resetUser = null;
    },
    async deleteUser(data) {
      const msg = `Are you sure you want to delete ${data.item.username}?`;
      const action = await this.$bvModal.msgBoxConfirm(msg, {});
      if (action === true) {
        await this.DELETE_USER(data.item.id);
      }
    },
    async getUsers() {
      await this.GET_USERS();
      this.clientTimeout = setTimeout(this.getUsers, 5000);
    },
    ...mapActions(['GET_USERS', 'DELETE_USER']),
  },
};
</script>
