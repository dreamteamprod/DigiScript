<template>
  <b-container
    class="mx-0"
    fluid
  >
    <b-row>
      <b-col v-if="loaded">
        <b-tabs content-class="mt-3">
          <b-tab
            title="Mics"
            active
          >
            <mic-list />
          </b-tab>
          <b-tab
            title="Allocations"
          >
            <mic-allocations />
          </b-tab>
        </b-tabs>
      </b-col>
      <b-col v-else>
        <div
          class="text-center center-spinner"
        >
          <b-spinner
            style="width: 10rem; height: 10rem;"
            variant="info"
          />
        </div>
      </b-col>
    </b-row>
  </b-container>
</template>

<script>
import { mapActions } from 'vuex';
import MicList from '@/vue_components/show/config/mics/MicList.vue';
import MicAllocations from '@/vue_components/show/config/mics/MicAllocations.vue';

export default {
  name: 'ConfigMics',
  components: { MicAllocations, MicList },
  data() {
    return {
      loaded: false,
    };
  },
  async mounted() {
    await this.GET_SCENE_LIST();
    await this.GET_ACT_LIST();
    await this.GET_CHARACTER_LIST();
    await this.GET_MICROPHONE_LIST();
    await this.GET_MIC_ALLOCATIONS();
    this.loaded = true;
  },
  methods: {
    ...mapActions(['GET_SCENE_LIST', 'GET_ACT_LIST', 'GET_CHARACTER_LIST',
      'GET_MICROPHONE_LIST', 'GET_MIC_ALLOCATIONS']),
  },
};
</script>
