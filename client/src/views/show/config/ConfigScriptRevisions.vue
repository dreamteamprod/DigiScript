<template>
  <b-container class="mx-0" fluid>
    <b-row v-if="!loading">
      <b-col>
        <b-tabs content-class="mt-3">
          <b-tab title="Revisions" active>
            <script-revisions />
          </b-tab>
          <b-tab title="Compiled Scripts">
            <compiled-scripts />
          </b-tab>
        </b-tabs>
      </b-col>
    </b-row>
    <b-row v-else>
      <b-col>
        <div v-if="loading" class="text-center py-5">
          <b-spinner label="Loading" />
        </div>
      </b-col>
    </b-row>
  </b-container>
</template>

<script>
import { mapActions } from 'vuex';

import ScriptRevisions from '@/vue_components/show/config/script/ScriptRevisions.vue';
import CompiledScripts from '@/vue_components/show/config/script/CompiledScripts.vue';

export default {
  name: 'ConfigScriptRevisions',
  components: { CompiledScripts, ScriptRevisions },
  data() {
    return {
      loading: true,
    };
  },
  async mounted() {
    await this.GET_SCRIPT_REVISIONS();
    this.loading = false;
  },
  methods: {
    ...mapActions(['GET_SCRIPT_REVISIONS']),
  },
};
</script>

<style scoped></style>
