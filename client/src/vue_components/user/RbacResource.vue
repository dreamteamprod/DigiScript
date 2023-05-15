<template>
  <div class="text-center center-spinner" v-if="!loaded">
    <b-spinner style="width: 10rem; height: 10rem;" variant="info" />
  </div>
  <div v-else-if="loaded && error">
    <b>Unable to load RBAC config, please try again!</b>
  </div>
  <b-container v-else class="mx-0" fluid>
    <b-row>
      <b-col>
        <b-table :id="`rbac-table-${resource}`" :items="rbacObjects.map((x) => x[0])"
                 :fields="[...displayFields, ...rbacRoles]" show-empty >
          <template v-for="role in rbacRoles" v-slot:[getCellName(role)]="data">
            <b-button
              :key="role"
              v-if="(rbacObjects[data.index][1] & rbacRolesDict[role]) === 0" variant="primary"
              @click.stop="giveRole(data.item, rbacRolesDict[role])"
              :disabled="processing"
            >
              Grant Role
            </b-button>
            <b-button
              :key="role"
              v-else variant="danger"
              @click.stop="revokeRole(data.item, rbacRolesDict[role])"
              :disabled="processing"
            >
              Revoke Role
            </b-button>
          </template>
        </b-table>
      </b-col>
    </b-row>
  </b-container>
</template>

<script>
import { makeURL } from '@/js/utils';

export default {
  name: 'RbacResource',
  props: {
    resource: {
      required: true,
    },
    user_id: {
      required: true,
    },
  },
  data() {
    return {
      loaded: false,
      error: false,
      rbacObjects: null,
      displayFields: null,
      roles: null,
      processing: false,
    };
  },
  async mounted() {
    await this.getObjects();
    await this.getRoles();
    this.loaded = true;
  },
  methods: {
    getCellName(slot) {
      return `cell(${slot})`;
    },
    async getRoles() {
      try {
        const response = await fetch(`${makeURL('/api/v1/rbac/roles')}`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
        });
        if (response.ok) {
          const rbacRoles = await response.json();
          this.roles = rbacRoles.roles;
        } else {
          this.$toast.error('Unable to fetch RBAC roles');
          this.error = true;
        }
      } catch {
        this.$toast.error('Unable to fetch RBAC roles');
        this.error = true;
      }
    },
    async getObjects() {
      const searchParams = new URLSearchParams({
        resource: this.resource,
        user: this.user_id,
      });
      try {
        const response = await fetch(`${makeURL('/api/v1/rbac/user/objects')}?${searchParams}`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
        });
        if (response.ok) {
          const rbacObjects = await response.json();
          this.rbacObjects = rbacObjects.objects;
          this.displayFields = rbacObjects.display_fields;
        } else {
          this.$toast.error('Unable to fetch RBAC objects for resource');
          this.error = true;
        }
      } catch {
        this.$toast.error('Unable to fetch RBAC objects for resource');
        this.error = true;
      }
    },
    async giveRole(object, role) {
      this.processing = true;
      try {
        const response = await fetch(`${makeURL('/api/v1/rbac/user/roles/grant')}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            resource: this.resource,
            user: this.user_id,
            object,
            role,
          }),
        });
        if (response.ok) {
          this.$toast.success('Granted role to user');
        } else {
          this.$toast.error('Unable to grant role to user');
        }
      } catch {
        this.$toast.error('Unable to grant role to user');
      }
      await this.getObjects();
      this.processing = false;
    },
    async revokeRole(object, role) {
      this.processing = true;
      try {
        const response = await fetch(`${makeURL('/api/v1/rbac/user/roles/revoke')}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            resource: this.resource,
            user: this.user_id,
            object,
            role,
          }),
        });
        if (response.ok) {
          this.$toast.success('Revoked role from user');
        } else {
          this.$toast.error('Unable to revoke role from user');
        }
      } catch {
        this.$toast.error('Unable to revoke role from user');
      }
      await this.getObjects();
      this.processing = false;
    },
  },
  computed: {
    rbacRoles() {
      return this.roles.map((x) => x.key);
    },
    rbacRolesDict() {
      const ret = {};
      this.roles.forEach((role) => {
        ret[role.key] = role.value;
      });
      return ret;
    },
  },
};
</script>
