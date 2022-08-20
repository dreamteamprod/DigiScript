<template>
  <div class="show">
    <h1>{{ this.$store.state.currentShow["name"] }}</h1>
    <b-container class="mx-0" fluid>
      <b-row>
        <b-col cols="2">
          <b-button-group vertical>
            <b-button
              replace :to="{'name': 'show-config'}"
              variant="outline-info" exact-active-class="active">Configure Show
            </b-button>
            <b-button
              replace :to="{'name': 'show-config-cast'}"
              variant="outline-info" active-class="active">Configure Cast
            </b-button>
            <b-button
              replace :to="{'name': 'show-config-characters'}"
              variant="outline-info" active-class="active">Configure Characters
            </b-button>
            <b-button
              replace :to="{'name': 'show-config-acts'}"
              variant="outline-info" active-class="active">Configure Acts
            </b-button>
            <b-button replace :to="{'name': 'show-config-scenes'}" variant="outline-info"
                      active-class="active">Configure Scenes
            </b-button>
            <b-button replace :to="{'name': 'show-config-cues'}" variant="outline-info"
                      active-class="active">Configure Cues
            </b-button>
            <b-button replace :to="{'name': 'show-config-script'}" variant="outline-info"
                      active-class="active">Configure Script
            </b-button>
          </b-button-group>
        </b-col>
        <b-col cols="10">
          <router-view/>
        </b-col>
      </b-row>
    </b-container>
  </div>
</template>

<script>
export default {
  name: 'ShowView',
};
</script>

<style scoped>

</style>
