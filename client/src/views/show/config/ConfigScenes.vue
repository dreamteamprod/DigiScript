<template>
  <b-container
    class="mx-0"
    fluid
  >
    <b-row>
      <b-col cols="8">
        <h5>Scene List</h5>
        <b-table
          id="scene-table"
          :items="sceneTableItems"
          :fields="sceneFields"
          :per-page="rowsPerPage"
          :current-page="currentPage"
          show-empty
        >
          <template #head(btn)="data">
            <b-button
              v-b-modal.new-scene
              variant="outline-success"
            >
              New Scene
            </b-button>
          </template>
          <template #cell(act)="data">
            {{ ACT_BY_ID(data.item.act).name }}
          </template>
          <template #cell(next_scene)="data">
            <p v-if="data.item.next_scene">
              {{ SCENE_BY_ID(data.item.next_scene).name }}
            </p>
            <p v-else>
              N/A
            </p>
          </template>
          <template #cell(previous_scene)="data">
            <p v-if="data.item.previous_scene">
              {{ SCENE_BY_ID(data.item.previous_scene).name }}
            </p>
            <p v-else>
              N/A
            </p>
          </template>
          <template #cell(btn)="data">
            <b-button-group>
              <b-button
                variant="warning"
                @click="openEditForm(data)"
              >
                Edit
              </b-button>
              <b-button
                variant="danger"
                @click="deleteAct(data)"
              >
                Delete
              </b-button>
            </b-button-group>
          </template>
        </b-table>
        <b-pagination
          v-show="sceneTableItems.length > rowsPerPage"
          v-model="currentPage"
          :total-rows="sceneTableItems.length"
          :per-page="rowsPerPage"
          aria-controls="scene-table"
          class="justify-content-center"
        />
      </b-col>
      <b-col cols="4">
        <h5>Act First Scenes</h5>
        <b-table
          id="first-scenes-table"
          :items="ACT_LIST"
          :fields="firstSceneFields"
          show-empty
        >
          <template #cell(first_scene)="data">
            <p v-if="data.item.first_scene">
              {{ SCENE_BY_ID(data.item.first_scene).name }}
            </p>
            <p v-else>
              N/A
            </p>
          </template>
          <template #cell(btn)="data">
            <b-button-group>
              <b-button
                variant="success"
                @click="openFirstSceneEdit(data)"
              >
                Set
              </b-button>
            </b-button-group>
          </template>
        </b-table>
      </b-col>
    </b-row>
    <b-modal
      id="new-scene"
      ref="new-scene"
      title="Add New Scene"
      size="md"
      @show="resetNewForm"
      @hidden="resetNewForm"
      @ok="onSubmitNew"
    >
      <b-form
        ref="new-scene-form"
        @submit.stop.prevent="onSubmitNew"
      >
        <b-form-group
          id="name-input-group"
          label="Name"
          label-for="name-input"
        >
          <b-form-input
            id="name-input"
            v-model="$v.newFormState.name.$model"
            name="name-input"
            :state="validateNewState('name')"
            aria-describedby="name-feedback"
          />
          <b-form-invalid-feedback
            id="name-feedback"
          >
            This is a required field.
          </b-form-invalid-feedback>
        </b-form-group>
        <b-form-group
          id="act-input-group"
          label="Act"
          label-for="act-input"
        >
          <b-form-select
            id="act-input"
            v-model="$v.newFormState.act_id.$model"
            :options="actOptions"
            :state="validateNewState('act_id')"
            aria-describedby="act-feedback"
          />
          <b-form-invalid-feedback
            id="act-feedback"
          >
            This is a required field.
          </b-form-invalid-feedback>
        </b-form-group>
        <b-form-group
          id="previous-scene-input-group"
          label="Previous Scene"
          label-for="previous-scene-input"
        >
          <b-form-select
            id="previous-scene-input"
            v-model="$v.newFormState.previous_scene_id.$model"
            :options="previousSceneOptions[$v.newFormState.act_id.$model]"
            aria-describedby="previous-scene-feedback"
          />
        </b-form-group>
      </b-form>
    </b-modal>
    <b-modal
      id="edit-scene"
      ref="edit-scene"
      title="Edit Scene"
      size="md"
      @hidden="resetEditForm"
      @ok="onSubmitEdit"
    >
      <b-form
        ref="edit-act-form"
        @submit.stop.prevent="onSubmitEdit"
      >
        <b-form-group
          id="name-input-group"
          label="Name"
          label-for="name-input"
        >
          <b-form-input
            id="name-input"
            v-model="$v.editFormState.name.$model"
            name="name-input"
            :state="validateEditState('name')"
            aria-describedby="name-feedback"
          />
          <b-form-invalid-feedback
            id="name-feedback"
          >
            This is a required field.
          </b-form-invalid-feedback>
        </b-form-group>
        <b-form-group
          id="act-input-group"
          label="Act"
          label-for="act-input"
        >
          <b-form-select
            id="act-input"
            v-model="$v.editFormState.act_id.$model"
            :options="actOptions"
            :state="validateEditState('act_id')"
            aria-describedby="act-feedback"
            @change="editActChanged"
          />
          <b-form-invalid-feedback
            id="act-feedback"
          >
            This is a required field.
          </b-form-invalid-feedback>
        </b-form-group>
        <b-form-group
          id="previous-scene-input-group"
          label="Previous Scene"
          label-for="previous-scene-input"
        >
          <b-form-select
            id="previous-scene-input"
            v-model="$v.editFormState.previous_scene_id.$model"
            :options="editFormPrevScenes"
            :state="validateEditState('previous_scene_id')"
            aria-describedby="previous-scene-feedback"
          />
          <b-form-invalid-feedback
            id="previous-scene-feedback"
          >
            This cannot form a circular dependency between scenes.
          </b-form-invalid-feedback>
        </b-form-group>
      </b-form>
    </b-modal>
    <b-modal
      id="set-first-scene"
      ref="set-first-scene"
      title="Set First Scene"
      size="md"
      @hidden="resetFirstSceneForm"
      @ok="onSubmitFirstScene"
    >
      <b-form
        ref="set-first-scene-form"
        @submit.stop.prevent="onSubmitFirstScene"
      >
        <b-form-group
          id="first-scene-input-group"
          :label="firstSceneModalLabel"
          label-for="first-scene-input"
        >
          <b-form-select
            id="first-scene-input"
            v-model="firstSceneFormState.scene_id"
            :options="firstSceneOptions[firstSceneFormState.act_id]"
          />
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
        'name',
        'act',
        { key: 'previous_scene', label: 'Previous Scene' },
        { key: 'next_scene', label: 'Next Scene' },
        { key: 'btn', label: '' },
      ],
      newFormState: {
        name: '',
        act_id: null,
        previous_scene_id: null,
      },
      firstSceneFields: [
        { key: 'name', label: 'Act' },
        { key: 'first_scene', label: 'First Scene' },
        { key: 'btn', label: '' },
      ],
      firstSceneFormState: {
        act_id: null,
        scene_id: null,
      },
      editSceneID: null,
      editFormState: {
        scene_id: null,
        name: '',
        act_id: null,
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
      previous_scene_id: {
        integer,
      },
    },
    firstSceneFormState: {},
    editFormState: {
      name: {
        required,
      },
      act_id: {
        notNullAndGreaterThanZero: (value) => (value != null && value > 0),
      },
      previous_scene_id: {
        integer,
        noLoops(value) {
          const sceneIndexes = [this.editFormState.scene_id];
          let currentScene = this.SCENE_BY_ID(value);
          while (currentScene != null && currentScene.previous_scene != null) {
            if (sceneIndexes.includes(currentScene.previous_scene)) {
              return false;
            }
            currentScene = this.SCENE_BY_ID(currentScene.previous_scene);
          }
          return true;
        },
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
    async deleteAct(act) {
      const msg = `Are you sure you want to delete ${act.item.name}?`;
      const action = await this.$bvModal.msgBoxConfirm(msg, {});
      if (action === true) {
        await this.DELETE_SCENE(act.item.id);
      }
    },
    resetFirstSceneForm() {
      this.firstSceneFormState = {
        act_id: null,
        scene_id: null,
      };

      this.$nextTick(() => {
        this.$v.$reset();
      });
    },
    openFirstSceneEdit(act) {
      if (act != null) {
        this.firstSceneFormState.act_id = act.item.id;
        if (act.item.first_scene != null) {
          this.firstSceneFormState.scene_id = act.item.first_scene;
        }
        this.$bvModal.show('set-first-scene');
      }
    },
    async onSubmitFirstScene(event) {
      this.$v.firstSceneFormState.$touch();
      if (this.$v.firstSceneFormState.$anyError) {
        event.preventDefault();
      } else {
        await this.SET_ACT_FIRST_SCENE(this.firstSceneFormState);
        this.resetFirstSceneForm();
      }
    },
    resetEditForm() {
      this.editSceneID = null;
      this.editFormState = {
        scene_id: null,
        name: '',
        act_id: null,
        previous_scene_id: null,
      };

      this.$nextTick(() => {
        this.$v.$reset();
      });
    },
    openEditForm(scene) {
      if (scene != null) {
        this.editSceneID = scene.item.id;
        this.editFormState.scene_id = scene.item.id;
        this.editFormState.name = scene.item.name;
        if (scene.item.act != null) {
          this.editFormState.act_id = scene.item.act;
        }
        if (scene.item.previous_scene != null) {
          this.editFormState.previous_scene_id = scene.item.previous_scene;
        }
        this.$bvModal.show('edit-scene');
      }
    },
    validateEditState(name) {
      const { $dirty, $error } = this.$v.editFormState[name];
      return $dirty ? !$error : null;
    },
    async onSubmitEdit(event) {
      this.$v.editFormState.$touch();
      if (this.$v.editFormState.$anyError) {
        event.preventDefault();
      } else {
        await this.UPDATE_SCENE(this.editFormState);
        this.resetEditForm();
      }
    },
    editActChanged(newActID) {
      const editScene = this.SCENE_LIST.find((s) => (s.id === this.editSceneID));
      if (newActID !== editScene.act) {
        this.editFormState.previous_scene_id = null;
      } else if (editScene.previous_scene != null) {
        this.editFormState.previous_scene_id = editScene.previous_scene;
      } else {
        this.editFormState.previous_scene_id = null;
      }
    },
    ...mapActions(['GET_SCENE_LIST', 'GET_ACT_LIST', 'ADD_SCENE', 'DELETE_SCENE',
      'SET_ACT_FIRST_SCENE', 'UPDATE_SCENE']),
  },
  computed: {
    ...mapGetters(['SCENE_LIST', 'ACT_LIST', 'CURRENT_SHOW', 'SCENE_BY_ID', 'ACT_BY_ID']),
    sceneTableItems() {
      // Get ordering of Acts
      const acts = [];
      if (this.CURRENT_SHOW.first_act_id != null && this.ACT_LIST.length > 0) {
        let act = this.ACT_BY_ID(this.CURRENT_SHOW.first_act_id);
        while (act != null) {
          // eslint-disable-next-line no-loop-func
          acts.push(act.id);
          act = this.ACT_BY_ID(act.next_act);
        }
      }
      this.ACT_LIST.forEach((act) => {
        if (!acts.includes(act.id)) {
          acts.push(act.id);
        }
      });
      const ret = [];
      acts.forEach((actId) => {
        const act = this.ACT_LIST.find((a) => (a.id === actId));
        if (act.first_scene != null) {
          let scene = this.SCENE_BY_ID(act.first_scene);
          while (scene != null) {
            // eslint-disable-next-line no-loop-func
            ret.push(this.SCENE_BY_ID(scene.id));
            scene = this.SCENE_BY_ID(scene.next_scene);
          }
        }
        const sceneIds = ret.map((s) => (s.id));
        this.SCENE_LIST.filter((s) => (s.act === actId)).forEach((scene) => {
          if (!sceneIds.includes(scene.id)) {
            ret.push(scene);
          }
        });
      });
      return ret;
    },
    actOptions() {
      return [
        { value: null, text: 'Please select an option', disabled: true },
        ...this.ACT_LIST.map((act) => ({ value: act.id, text: act.name })),
      ];
    },
    previousSceneOptions() {
      const ret = {
        null: [{ value: null, text: 'None', disabled: false }],
      };
      this.ACT_LIST.forEach((act) => {
        ret[act.id] = [
          {
            value: null, text: 'None', disabled: false,
          },
          ...this.SCENE_LIST.filter((scene) => (
            scene.act === act.id && scene.next_scene == null
            && this.ACT_BY_ID(scene.act) != null), this).map((scene) => ({
            value: scene.id,
            text: `${this.ACT_BY_ID(scene.act).name}: ${scene.name}`,
          }))];
      }, this);

      return ret;
    },
    firstSceneOptions() {
      const ret = {};
      this.ACT_LIST.forEach((act) => {
        ret[act.id] = [{
          value: null,
          text: 'None',
          disabled: false,
        }, ...act.scene_list.filter((scene) => (
          this.SCENE_BY_ID(scene) != null
          && this.SCENE_BY_ID(scene).previous_scene == null), this).map((scene) => ({
          value: scene,
          text: `${act.name}: ${this.SCENE_BY_ID(scene).name}`,
        }))];
      }, this);
      return ret;
    },
    firstSceneModalLabel() {
      if (this.firstSceneFormState.act_id == null) {
        return '';
      }
      return `${this.ACT_LIST.find((act) => (act.id === this.firstSceneFormState.act_id)).name} First Scene`;
    },
    editFormPrevScenes() {
      const ret = [];
      ret.push(...this.previousSceneOptions[this.editFormState.act_id].filter(
        (scene) => (scene.value !== this.editFormState.scene_id),
      ));
      if (this.editFormState.previous_scene_id != null) {
        const scene = this.SCENE_LIST.find(
          (s) => (s.id === this.editFormState.previous_scene_id),
        );
        ret.push({
          value: this.editFormState.previous_scene_id,
          text: `${this.ACT_BY_ID(scene.act).name}: ${scene.name}`,
          disabled: false,
        });
      }
      return ret;
    },
  },
};
</script>

<style scoped>

</style>
