<template>
  <div class="help-doc">
    <BSpinner v-if="isLoading" variant="info" style="width: 3rem; height: 3rem" />
    <BAlert v-else-if="error" variant="danger" :model-value="true">
      <strong>Error:</strong> {{ error }}
      <br />
      <BButton variant="outline-danger" size="sm" class="mt-2" @click="retry"> Retry </BButton>
    </BAlert>
    <MarkdownRenderer v-else-if="currentDocumentContent" :content="currentDocumentContent" />
  </div>
</template>

<script setup lang="ts">
import { watch } from 'vue';
import { useRoute } from 'vue-router';
import { storeToRefs } from 'pinia';
import { useHelpStore } from '@/stores/help';
import MarkdownRenderer from '@/components/MarkdownRenderer.vue';

const route = useRoute();
const helpStore = useHelpStore();

const { currentDocumentContent, isLoading, error } = storeToRefs(helpStore);

watch(
  () => route.params.slug as string,
  async (slug) => {
    if (slug) {
      if (!helpStore.documentationManifest.length) {
        await helpStore.loadManifest();
      }
      await helpStore.loadDocument(slug);
    }
  },
  { immediate: true }
);

async function retry() {
  const slug = route.params.slug as string;
  if (slug) {
    if (!helpStore.documentationManifest.length) {
      await helpStore.loadManifest();
    }
    await helpStore.loadDocument(slug);
  }
}
</script>
