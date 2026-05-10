<template>
  <b-container class="mx-0" fluid>
    <b-row>
      <b-col>
        <b-table id="cast-table" :items="USERS" :fields="userFields" show-empty>
          <template #head(btn)="data">
            <b-button-group>
              <b-button v-b-modal.new-user variant="outline-success"> New User </b-button>
              <b-button v-b-modal.new-admin-user variant="outline-success"> New Admin </b-button>
            </b-button-group>
          </template>
          <template #head(is_admin)="data"> User Type </template>
          <template #cell(last_login)="data">
            {{ data.item.last_login ? data.item.last_login : 'Never' }}
          </template>
          <template #cell(last_seen)="data">
            {{ data.item.last_seen ? data.item.last_seen : 'Never' }}
          </template>
          <template #cell(is_admin)="data">
            <b-badge v-if="data.item.is_admin" variant="primary">Admin</b-badge>
            <b-badge v-else variant="secondary">User</b-badge>
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
                :disabled="
                  (allAdmins.length === 1 && data.item.is_admin) || data.item.id === CURRENT_USER.id
                "
                @click.stop="deleteUser(data)"
              >
                Delete
              </b-button>
            </b-button-group>
          </template>
        </b-table>
      </b-col>
    </b-row>
    <b-modal id="new-user" ref="new-user" title="Add New User" size="md" hide-footer>
      <create-user :is-first-admin="false" @created_user="resetNewForm" />
    </b-modal>
    <b-modal id="new-admin-user" ref="new-admin-user" title="Add New Admin" size="md" hide-footer>
      <create-user :is-first-admin="false" :is-admin="true" @created_user="resetNewAdminForm" />
    </b-modal>
    <b-modal id="user-rbac" ref="user-rbac" title="User RBAC Config" size="xl" hide-footer>
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

<script lang="ts">
import { defineComponent } from 'vue';
import { mapActions, mapGetters } from 'vuex';

import CreateUser from '@/vue_components/user/CreateUser.vue';
import ConfigRbac from '@/vue_components/user/ConfigRbac.vue';
import ResetPassword from '@/vue_components/user/ResetPassword.vue';

export default defineComponent({
  name: 'ConfigUsers',
  components: { CreateUser, ConfigRbac, ResetPassword },
  data() {
    return {
      userFields: ['username', 'last_login', 'last_seen', 'is_admin', { key: 'btn', label: '' }],
      editUser: null as number | null,
      resetUser: null as { id: number; username: string } | null,
      clientTimeout: null as ReturnType<typeof setTimeout> | null,
    };
  },
  computed: {
    allAdmins(): unknown[] {
      return (this.USERS as any[]).filter((user) => user.is_admin);
    },
    ...mapGetters(['USERS', 'CURRENT_SHOW', 'CURRENT_USER']),
  },
  async mounted() {
    await this.getUsers();
  },
  destroyed() {
    clearTimeout(this.clientTimeout ?? undefined);
  },
  methods: {
    resetNewForm(): void {
      (this as any).$bvModal.hide('new-user');
    },
    resetNewAdminForm(): void {
      (this as any).$bvModal.hide('new-admin-user');
    },
    setEditUser(userId: number): void {
      this.editUser = userId;
    },
    setResetUser(user: { id: number; username: string }): void {
      this.resetUser = user;
    },
    async handlePasswordReset(): Promise<void> {
      await this.getUsers();
    },
    closeResetPasswordModal(): void {
      (this as any).$bvModal.hide('reset-password');
      this.resetUser = null;
    },
    async deleteUser(data: any): Promise<void> {
      const msg = `Are you sure you want to delete ${data.item.username}?`;
      const action = await (this as any).$bvModal.msgBoxConfirm(msg, {});
      if (action === true) {
        await (this as any).DELETE_USER(data.item.id);
      }
    },
    async getUsers(): Promise<void> {
      await (this as any).GET_USERS();
      this.clientTimeout = setTimeout(this.getUsers, 5000);
    },
    ...mapActions(['GET_USERS', 'DELETE_USER']),
  },
});
</script>
