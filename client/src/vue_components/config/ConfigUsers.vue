<template>
  <b-container class="mx-0" fluid>
    <b-row>
      <b-col>
        <b-table id="cast-table" :items="this.SHOW_USERS" :fields="userFields" show-empty>
          <template #head(btn)="data">
            <b-button variant="outline-success" v-b-modal.new-user>
              New User
            </b-button>
          </template>
          <template #cell(btn)="data">
            <b-button-group>
              <b-button variant="danger" @click="deleteUser(data)" :disabled="true">
                Delete
              </b-button>
            </b-button-group>
          </template>
        </b-table>
      </b-col>
    </b-row>
    <b-modal id="new-user" title="Add New User" ref="new-user" size="md" hide-footer>
      <create-user
        :is_first_admin="false"
        :show_id="CURRENT_SHOW.id"
        v-on:created_user="resetNewForm"
      />
    </b-modal>
  </b-container>
</template>

<script>
import { mapActions, mapGetters } from 'vuex';

import CreateUser from '@/vue_components/user/CreateUser.vue';

export default {
  name: 'ConfigUsers',
  components: { CreateUser },
  data() {
    return {
      userFields: [
        'username',
        'last_login',
        'is_admin',
        { key: 'btn', label: '' },
      ],
    };
  },
  async mounted() {
    await this.GET_USERS();
  },
  methods: {
    resetNewForm() {
      this.$bvModal.hide('new-user');
    },
    async deleteUser() {
      console.log('Delete');
    },
    ...mapActions(['GET_USERS']),
  },
  computed: {
    ...mapGetters(['SHOW_USERS', 'CURRENT_SHOW']),
  },
};
</script>
