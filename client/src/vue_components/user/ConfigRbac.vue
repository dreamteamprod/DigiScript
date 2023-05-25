<template>
  <div
    v-if="!loaded"
    class="text-center center-spinner"
  >
    <b-spinner
      style="width: 10rem; height: 10rem;"
      variant="info"
    />
  </div>
  <div v-else-if="loaded && error">
    <b>Unable to load RBAC config, please try again!</b>
  </div>
  <b-container
    v-else
    class="mx-0"
    fluid
  >
    <b-row>
      <b-col>
        <b-tabs content-class="mt-3">
          <b-tab
            v-for="(resource, index) in rbacResources"
            :key="`rbac_resource_${index}`"
            :active="index === 0"
            :title="resource | capitalize"
          >
            <rbac-resource
              :resource="resource"
              :user_id="user_id"
            />
          </b-tab>
        </b-tabs>
      </b-col>
    </b-row>
  </b-container>
</template>

<script>
import { makeURL } from '@/js/utils';
import RbacResource from '@/vue_components/user/RbacResource.vue';

export default {
  name: 'ConfigRBAC',
  components: { RbacResource },
  props: {
    user_id: {
      required: true,
    },
  },
  data() {
    return {
      loaded: false,
      error: false,
      rbacResources: null,
    };
  },
  async mounted() {
    try {
      const response = await fetch(`${makeURL('/api/v1/rbac/user/resources')}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      if (response.ok) {
        const rbacResources = await response.json();
        this.rbacResources = rbacResources.resources;
      } else {
        this.$toast.error('Unable to fetch RBAC configuration for show');
        this.error = true;
      }
    } catch {
      this.$toast.error('Unable to fetch RBAC configuration for show');
      this.error = true;
    }
    this.loaded = true;
  },
};
</script>
