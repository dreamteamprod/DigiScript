<template>
  <b-container class="mx-0" fluid>
    <b-row>
      <b-col>
        <b-tabs content-class="mt-3">
          <b-tab title="Acts" active>
            <config-acts />
          </b-tab>
          <b-tab title="Scenes">
            <config-scenes />
          </b-tab>
        </b-tabs>
      </b-col>
    </b-row>
  </b-container>
</template>

<script>
import ConfigActs from '@/vue_components/show/config/acts_and_scenes/ConfigActs.vue';
import ConfigScenes from '@/vue_components/show/config/acts_and_scenes/ConfigScenes.vue';

export default {
  name: 'ConfigActsAndScenes',
  components: { ConfigScenes, ConfigActs },
};
</script>
