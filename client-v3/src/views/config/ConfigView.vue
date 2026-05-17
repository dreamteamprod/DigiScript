<template>
  <BContainer fluid class="mx-0">
    <BRow>
      <BCol>
        <h1>DigiScript Config</h1>
        <BTabs content-class="mt-3" lazy>
          <BTab active title="Shows"><ConfigShows /></BTab>
          <BTab title="System"><ConfigSystem /></BTab>
          <BTab title="Settings"><ConfigSettings /></BTab>
          <BTab title="Users"><ConfigUsers /></BTab>
          <BTab title="Logs"><ConfigLogs /></BTab>
          <BTab title="Backups"><ConfigBackups /></BTab>
        </BTabs>
      </BCol>
    </BRow>
  </BContainer>
</template>

<script setup lang="ts">
import ConfigShows from '@/components/config/ConfigShows.vue';
import ConfigSystem from '@/components/config/ConfigSystem.vue';
import ConfigSettings from '@/components/config/ConfigSettings.vue';
import ConfigUsers from '@/components/config/ConfigUsers.vue';
import ConfigLogs from '@/components/config/ConfigLogs.vue';
import ConfigBackups from '@/components/config/ConfigBackups.vue';
</script>
