<template>
  <BContainer class="mx-0" fluid>
    <BRow>
      <BCol v-if="loaded">
        <BTabs content-class="mt-3">
          <BTab title="Sessions" active>
            <SessionList />
          </BTab>
          <BTab title="Tags">
            <SessionTagList />
          </BTab>
        </BTabs>
      </BCol>
      <BCol v-else>
        <div class="text-center center-spinner">
          <BSpinner style="width: 10rem; height: 10rem" variant="info" />
        </div>
      </BCol>
    </BRow>
  </BContainer>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useShowStore } from '@/stores/show';
import SessionList from '@/components/show/config/sessions/SessionList.vue';
import SessionTagList from '@/components/show/config/sessions/SessionTagList.vue';

const showStore = useShowStore();
const loaded = ref(false);

onMounted(async () => {
  await Promise.all([
    showStore.getShowSessionData(),
    showStore.getSessionTags(),
    showStore.getScriptRevisions(),
  ]);
  loaded.value = true;
});
</script>
