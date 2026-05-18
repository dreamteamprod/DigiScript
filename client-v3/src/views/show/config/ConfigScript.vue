<template>
  <BContainer class="mx-0" fluid>
    <BRow>
      <BCol>
        <BTabs content-class="mt-3">
          <BTab title="Script" active><ScriptEditor /></BTab>
          <BTab title="Stage Direction Styles"><StageDirectionStyles /></BTab>
        </BTabs>
      </BCol>
    </BRow>
  </BContainer>
</template>

<script setup lang="ts">
import ScriptEditor from '@/components/show/config/script/ScriptEditor.vue';
import StageDirectionStyles from '@/components/show/config/script/StageDirectionStyles.vue';
</script>
