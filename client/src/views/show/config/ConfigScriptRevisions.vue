<template>
  <BContainer class="mx-0" fluid>
    <BRow v-if="!loading">
      <BCol>
        <BTabs content-class="mt-3">
          <BTab title="Revisions" active><ScriptRevisions /></BTab>
          <BTab title="Compiled Scripts"><CompiledScripts /></BTab>
        </BTabs>
      </BCol>
    </BRow>
    <BRow v-else>
      <BCol class="text-center py-5"><BSpinner label="Loading..." /></BCol>
    </BRow>
  </BContainer>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useShowStore } from '@/stores/show';
import ScriptRevisions from '@/components/show/config/script/ScriptRevisions.vue';
import CompiledScripts from '@/components/show/config/script/CompiledScripts.vue';

const showStore = useShowStore();
const loading = ref(true);

onMounted(async () => {
  await showStore.getScriptRevisions();
  loading.value = false;
});
</script>
