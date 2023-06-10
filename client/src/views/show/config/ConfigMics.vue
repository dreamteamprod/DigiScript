<template>
  <b-container
    class="mx-0"
    fluid
  >
    <b-row>
      <b-col>
        <b-tabs content-class="mt-3" >
          <b-tab
            title="Mics"
            active
          >
            <p>Mics</p>
          </b-tab>
          <b-tab
            title="Allocations"
          >
            <p>Allocations</p>
          </b-tab>
        </b-tabs>
      </b-col>
    </b-row>
  </b-container>
</template>

<script>
export default {
  name: 'ConfigMics',
};
</script>
