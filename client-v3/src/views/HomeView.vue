<template>
  <div class="container mt-5">
    <div class="row justify-content-center">
      <div class="col-md-8 text-center">
        <h1 class="display-4 mb-4">DigiScript</h1>
        <div class="alert alert-info" role="alert">
          <h4 class="alert-heading">Vue 3 Migration in Progress</h4>
          <p class="mb-0">
            This is the new Vue 3 frontend served at <code>/ui-new/</code>. The Vue 2 app remains
            available at <code>/</code> during migration.
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';

export default defineComponent({
  name: 'HomeView',
});
</script>
