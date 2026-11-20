<template>
  <div v-if="!loaded" class="text-center">
    <BSpinner style="width: 10rem; height: 10rem" variant="info" />
  </div>
  <div v-else-if="error">
    <strong>Unable to load RBAC config, please try again!</strong>
  </div>
  <BContainer v-else fluid class="mx-0">
    <BRow>
      <BCol>
        <BTabs content-class="mt-3">
          <BTab
            v-for="(resource, index) in rbacResources"
            :key="`rbac_resource_${index}`"
            :active="index === 0"
            :title="capitalize(resource)"
          >
            <RbacResource :resource="resource" :user-id="userId" />
          </BTab>
        </BTabs>
      </BCol>
    </BRow>
  </BContainer>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { makeURL } from '@/js/utils';
import { toast } from '@/js/toast';
import RbacResource from '@/components/user/RbacResource.vue';

const props = defineProps<{ userId: number }>();

const loaded = ref(false);
const error = ref(false);
const rbacResources = ref<string[]>([]);

function capitalize(str: string): string {
  return str.charAt(0).toUpperCase() + str.slice(1);
}

onMounted(async () => {
  try {
    const response = await fetch(makeURL('/api/v1/rbac/user/resources'));
    if (response.ok) {
      const data = await response.json();
      rbacResources.value = data.resources;
    } else {
      toast.error('Unable to fetch RBAC configuration');
      error.value = true;
    }
  } catch {
    toast.error('Unable to fetch RBAC configuration');
    error.value = true;
  }
  loaded.value = true;
});
</script>
