<template>
  <div class="config">
    <b>DigiScript Config</b>
    <b-table-simple>
      <b-tbody>
        <b-tr>
          <b-td>Current Show</b-td>
          <b-td>
            <p v-if="this.$store.state.system.settings['current_show'] != null">
              {{ this.$store.state.system.settings['current_show'] }}
            </p>
            <b-button v-else>Setup Show</b-button>
          </b-td>
        </b-tr>
      </b-tbody>
    </b-table-simple>
  </div>
</template>

<script>
export default {
  name: 'ConfigView',
};
</script>

<style scoped>

</style>
