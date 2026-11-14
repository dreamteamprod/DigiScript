<template>
  <BContainer class="mx-0" fluid>
    <BRow>
      <BCol>
        <BTabs content-class="mt-3">
          <BTab title="Script" active>
            <CollabScriptEditor v-if="systemStore.isCollabScriptEditing" />
            <ScriptEditor v-else />
          </BTab>
          <BTab title="Stage Direction Styles"><StageDirectionStyles /></BTab>
        </BTabs>
      </BCol>
    </BRow>
  </BContainer>
</template>

<script setup lang="ts">
import ScriptEditor from '@/components/show/config/script/ScriptEditor.vue';
import CollabScriptEditor from '@/components/show/config/script/CollabScriptEditor.vue';
import { useSystemStore } from '@/stores/system';
import StageDirectionStyles from '@/components/show/config/script/StageDirectionStyles.vue';

const systemStore = useSystemStore();
</script>
