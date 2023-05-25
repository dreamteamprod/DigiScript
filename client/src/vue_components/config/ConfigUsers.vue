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
        :show_id="CURRENT_SHOW.id"
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
      <config-rbac :user_id="editUser" />
    </b-modal>
  </b-container>
</template>

<script>
import { mapActions, mapGetters } from 'vuex';

import CreateUser from '@/vue_components/user/CreateUser.vue';
import ConfigRbac from '@/vue_components/user/ConfigRbac.vue';

export default {
  name: 'ConfigUsers',
  components: { CreateUser, ConfigRbac },
  data() {
    return {
      userFields: [
        'username',
        'last_login',
        'is_admin',
        { key: 'btn', label: '' },
      ],
      editUser: null,
    };
  },
  async mounted() {
    await this.GET_USERS();
  },
  methods: {
    resetNewForm() {
      this.$bvModal.hide('new-user');
    },
    setEditUser(userId) {
      this.editUser = userId;
    },
    ...mapActions(['GET_USERS']),
  },
  computed: {
    ...mapGetters(['SHOW_USERS', 'CURRENT_SHOW']),
  },
};
</script>
