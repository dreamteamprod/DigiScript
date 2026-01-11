<template>
  <b-container
    class="mx-0"
    fluid
  >
    <b-row>
      <b-col>
        <b-tabs content-class="mt-3">
          <b-tab
            title="Revisions"
            active
          >
            <script-revisions />
          </b-tab>
          <b-tab title="Stage Direction Styles">
            <stage-direction-configs />
          </b-tab>
          <b-tab title="Script">
            <script-config />
          </b-tab>
        </b-tabs>
      </b-col>
    </b-row>
  </b-container>
</template>

<script>
import ScriptConfig from '@/vue_components/show/config/script/ScriptEditor.vue';
import StageDirectionStyles from '@/vue_components/show/config/script/StageDirectionStyles.vue';
import ScriptRevisions from "@/vue_components/show/config/script/ScriptRevisions.vue";

export default {
  name: 'ConfigScript',
  components: {
    ScriptRevisions,
    ScriptConfig,
    StageDirectionConfigs: StageDirectionStyles,
  },
};
</script>

<style scoped>

</style>
