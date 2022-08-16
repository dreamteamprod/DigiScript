<template>
  <b-container>
    <b-row>
      <b-col>
        <b-table id="scene-table" :items="this.SCENE_LIST" :fields="sceneFields" show-empty>
          <template #head(btn)="data">
            <b-button variant="outline-success" v-b-modal.new-scene>
              New Scene
            </b-button>
          </template>
          <template #cell(act)="data">
            {{ data.item.act.name }}
          </template>
          <template #cell(next_scene)="data">
            <p v-if="data.item.next_scene">
              {{ data.item.next_scene.name }}
            </p>
            <p v-else>N/A</p>
          </template>
          <template #cell(previous_scene)="data">
            <p v-if="data.item.previous_scene">
              {{ data.item.previous_scene.name }}
            </p>
            <p v-else>N/A</p>
          </template>
          <template #cell(btn)="data">
            <b-button-group>
              <b-button variant="warning" @click="openEditForm(data)">
                Edit
              </b-button>
              <b-button variant="danger" @click="deleteAct(data)">
                Delete
              </b-button>
            </b-button-group>
          </template>
        </b-table>
        <b-pagination
          v-show="this.SCENE_LIST.length > rowsPerPage"
          v-model="currentPage"
          :total-rows="this.SCENE_LIST.length"
          :per-page="rowsPerPage"
          aria-controls="cast-table"
          class="justify-content-center"
        ></b-pagination>
      </b-col>
    </b-row>
    <b-modal id="new-scene" title="Add New Scene" ref="new-scene" size="md"
             @show="resetNewForm" @hidden="resetNewForm" @ok="onSubmitNew">
      <b-form @submit.stop.prevent="onSubmitNew" ref="new-scene-form">
        <b-form-group id="name-input-group" label="Name" label-for="name-input">
          <b-form-input
            id="name-input"
            name="name-input"
            v-model="$v.newFormState.name.$model"
            :state="validateNewState('name')"
            aria-describedby="name-feedback"
          ></b-form-input>
          <b-form-invalid-feedback
            id="name-feedback"
          >This is a required field.
          </b-form-invalid-feedback>
        </b-form-group>
        <b-form-group id="act-input-group" label="Act" label-for="act-input">
          <b-form-select
            id="act-input"
            :options="actOptions"
            v-model="$v.newFormState.act_id.$model"
            :state="validateNewState('act_id')"
            aria-describedby="act-feedback"/>
          <b-form-invalid-feedback
            id="act-feedback"
          >This is a required field.
          </b-form-invalid-feedback>
        </b-form-group>
        <b-form-group id="next-scene-input-group" label="Next Scene" label-for="next-scene-input">
          <b-form-select
            id="next-scene-input"
            :options="nextSceneOptions"
            v-model="$v.newFormState.next_scene_id.$model"
            :state="validateNewState('next_scene_id')"
            aria-describedby="next-scene-feedback"/>
          <b-form-invalid-feedback
            id="next-scene-feedback"
          >Cannot be the same as previous scene.
          </b-form-invalid-feedback>
        </b-form-group>
        <b-form-group
          id="previous-scene-input-group"
          label="Previous Scene"
          label-for="previous-scene-input">
          <b-form-select
            id="previous-scene-input"
            :options="previousSceneOptions"
            v-model="$v.newFormState.previous_scene_id.$model"
            :state="validateNewState('previous_scene_id')"
            aria-describedby="previous-scene-feedback"/>
          <b-form-invalid-feedback
            id="previous-scene-feedback"
          >Cannot be the same as next scene.
          </b-form-invalid-feedback>
        </b-form-group>
      </b-form>
    </b-modal>
  </b-container>
</template>

<script>
import { required, integer } from 'vuelidate/lib/validators';
import { mapGetters, mapActions } from 'vuex';

export default {
  name: 'ConfigScenes',
  data() {
    return {
      rowsPerPage: 15,
      currentPage: 1,
      sceneFields: [
        { key: 'id', label: 'ID' },
        'name',
        'act',
        { key: 'previous_scene', label: 'Previous Scene' },
        { key: 'next_scene', label: 'Next Scene' },
        { key: 'btn', label: '' },
      ],
      newFormState: {
        name: '',
        act_id: null,
        next_scene_id: null,
        previous_scene_id: null,
      },
    };
  },
  validations: {
    newFormState: {
      name: {
        required,
      },
      act_id: {
        notNullAndGreaterThanZero: (value) => (value != null && value > 0),
      },
      next_scene_id: {
        integer,
        notPreviousScene: (value, vm) => (value == null || vm.previous_scene_id == null ? true
          : value !== vm.previous_scene_id),
      },
      previous_scene_id: {
        integer,
        notNextScene: (value, vm) => (value == null || vm.next_scene_id == null ? true
          : value !== vm.next_scene_id),
      },
    },
  },
  async mounted() {
    await this.GET_SCENE_LIST();
    await this.GET_ACT_LIST();
  },
  methods: {
    resetNewForm() {
      this.newFormState = {
        name: '',
        act_id: null,
        next_scene_id: null,
        previous_scene_id: null,
      };

      this.$nextTick(() => {
        this.$v.$reset();
      });
    },
    validateNewState(name) {
      const { $dirty, $error } = this.$v.newFormState[name];
      return $dirty ? !$error : null;
    },
    async onSubmitNew(event) {
      this.$v.newFormState.$touch();
      if (this.$v.newFormState.$anyError) {
        event.preventDefault();
      } else {
        await this.ADD_SCENE(this.newFormState);
        this.resetNewForm();
      }
    },
    ...mapActions(['GET_SCENE_LIST', 'GET_ACT_LIST', 'ADD_SCENE']),
  },
  computed: {
    ...mapGetters(['SCENE_LIST', 'ACT_LIST']),
    actOptions() {
      return [
        { value: null, text: 'Please select an option', disabled: true },
        ...this.ACT_LIST.map((act) => ({ value: act.id, text: act.name })),
      ];
    },
    nextSceneOptions() {
      return [
        { value: null, text: 'None', disabled: false },
        ...this.SCENE_LIST.filter((scene) => (scene.previous_scene == null), this).map((scene) => ({
          value: scene.id,
          text: `${scene.act.name}: ${scene.name}`,
        })),
      ];
    },
    previousSceneOptions() {
      return [
        { value: null, text: 'None', disabled: false },
        ...this.SCENE_LIST.filter((scene) => (scene.next_scene == null), this).map((scene) => ({
          value: scene.id,
          text: `${scene.act.name}: ${scene.name}`,
        })),
      ];
    },
  },
};
</script>

<style scoped>

</style>
