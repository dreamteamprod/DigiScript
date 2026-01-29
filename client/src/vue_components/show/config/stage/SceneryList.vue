<template>
  <b-container class="mx-0" fluid>
    <b-row>
      <b-col cols="5">
        <h5>Scenery Types</h5>
        <b-table
          id="scenery-types-table"
          :items="SCENERY_TYPES"
          :fields="sceneryTypeFields"
          :per-page="rowsPerPage"
          :current-page="currentSceneryTypesPage"
          show-empty
        >
          <template #head(btn)="data">
            <b-button v-if="IS_SHOW_EDITOR" v-b-modal.new-scenery-type variant="outline-success">
              New Scenery Type
            </b-button>
          </template>
          <template #cell(btn)="data">
            <b-button-group v-if="IS_SHOW_EDITOR">
              <b-button variant="warning" @click="openEditSceneryTypeForm(data)"> Edit </b-button>
              <b-button variant="danger" @click="deleteSceneryType(data)"> Delete </b-button>
            </b-button-group>
          </template>
        </b-table>
        <b-pagination
          v-show="SCENERY_TYPES.length > rowsPerPage"
          v-model="currentSceneryTypesPage"
          :total-rows="SCENERY_TYPES.length"
          :per-page="rowsPerPage"
          aria-controls="scenery-types-table"
          class="justify-content-center"
        />
      </b-col>
      <b-col cols="7">
        <h5>Scenery List</h5>
        <b-table
          id="scenery-table"
          :items="SCENERY_LIST"
          :fields="sceneryFields"
          :per-page="rowsPerPage"
          :current-page="currentSceneryPage"
          show-empty
        >
          <template #head(btn)="data">
            <b-button v-if="IS_SHOW_EDITOR" v-b-modal.new-scenery variant="outline-success">
              New Scenery Item
            </b-button>
          </template>
          <template #cell(scenery_type_id)="data">
            <span>{{ SCENERY_TYPE_BY_ID(data.item.scenery_type_id).name }}</span>
          </template>
          <template #cell(btn)="data">
            <b-button-group v-if="IS_SHOW_EDITOR">
              <b-button variant="warning" @click="openEditSceneryForm(data)"> Edit </b-button>
              <b-button variant="danger" @click="deleteSceneryItem(data)"> Delete </b-button>
            </b-button-group>
          </template>
        </b-table>
        <b-pagination
          v-show="SCENERY_LIST.length > rowsPerPage"
          v-model="currentSceneryPage"
          :total-rows="SCENERY_LIST.length"
          :per-page="rowsPerPage"
          aria-controls="scenery-table"
          class="justify-content-center"
        />
      </b-col>
    </b-row>
    <b-modal
      id="new-scenery-type"
      ref="new-scenery-type"
      title="Add New Scenery Type"
      size="md"
      @show="resetNewSceneryTypeForm"
      @hidden="resetNewSceneryTypeForm"
      @ok="onSubmitNewSceneryType"
    >
      <b-form ref="new-scenery-type-form" @submit.stop.prevent="onSubmitNewSceneryType">
        <b-form-group id="name-input-group" label="Name" label-for="name-input">
          <b-form-input
            id="name-input"
            v-model="$v.newSceneryTypeFormState.name.$model"
            name="name-input"
            :state="validateNewSceneryTypeState('name')"
            aria-describedby="name-feedback"
          />
          <b-form-invalid-feedback id="name-feedback">
            This is a required field.
          </b-form-invalid-feedback>
        </b-form-group>
        <b-form-group
          id="description-input-group"
          label="Description"
          label-for="description-input"
        >
          <b-form-input
            id="description-input"
            v-model="$v.newSceneryTypeFormState.description.$model"
            name="description-input"
            :state="validateNewSceneryTypeState('description')"
            aria-describedby="name-feedback"
          />
          <b-form-invalid-feedback id="description-feedback">
            This is a required field.
          </b-form-invalid-feedback>
        </b-form-group>
      </b-form>
    </b-modal>
    <b-modal
      id="edit-scenery-type"
      ref="edit-scenery-type"
      title="Edit Scenery Type"
      size="md"
      @hidden="resetEditSceneryTypeForm"
      @ok="onSubmitEditSceneryType"
    >
      <b-form ref="edit-scenery-type-form" @submit.stop.prevent="onSubmitEditSceneryType">
        <b-form-group id="name-input-group" label="Name" label-for="name-input">
          <b-form-input
            id="name-input"
            v-model="$v.editSceneryTypeFormState.name.$model"
            name="name-input"
            :state="validateEditSceneryTypeState('name')"
            aria-describedby="name-feedback"
          />
          <b-form-invalid-feedback id="name-feedback">
            This is a required field.
          </b-form-invalid-feedback>
        </b-form-group>
        <b-form-group
          id="description-input-group"
          label="Description"
          label-for="description-input"
        >
          <b-form-input
            id="description-input"
            v-model="$v.editSceneryTypeFormState.description.$model"
            name="description-input"
            :state="validateEditSceneryTypeState('description')"
            aria-describedby="name-feedback"
          />
          <b-form-invalid-feedback id="description-feedback">
            This is a required field.
          </b-form-invalid-feedback>
        </b-form-group>
      </b-form>
    </b-modal>
    <b-modal
      id="new-scenery"
      ref="new-scenery"
      title="Add New Scenery"
      size="md"
      @show="resetNewSceneryForm"
      @hidden="resetNewSceneryForm"
      @ok="onSubmitNewScenery"
    >
      <b-form ref="new-scenery-form" @submit.stop.prevent="onSubmitNewScenery">
        <b-form-group
          id="scenery-type-input-group"
          label="Scenery Type"
          label-for="scenery-type-input"
        >
          <b-form-select
            id="scenery-type-input"
            v-model="$v.newSceneryFormState.scenery_type_id.$model"
            :options="sceneryTypeOptions"
            :state="validateNewSceneryState('scenery_type_id')"
            aria-describedby="scenery-type-feedback"
          />
          <b-form-invalid-feedback id="scenery-type-feedback">
            This is a required field.
          </b-form-invalid-feedback>
        </b-form-group>
        <b-form-group id="name-input-group" label="Name" label-for="name-input">
          <b-form-input
            id="name-input"
            v-model="$v.newSceneryFormState.name.$model"
            name="name-input"
            :state="validateNewSceneryState('name')"
            aria-describedby="name-feedback"
          />
          <b-form-invalid-feedback id="name-feedback">
            This is a required field.
          </b-form-invalid-feedback>
        </b-form-group>
        <b-form-group
          id="description-input-group"
          label="Description"
          label-for="description-input"
        >
          <b-form-input
            id="description-input"
            v-model="$v.newSceneryFormState.description.$model"
            name="description-input"
            :state="validateNewSceneryState('description')"
            aria-describedby="name-feedback"
          />
          <b-form-invalid-feedback id="description-feedback">
            This is a required field.
          </b-form-invalid-feedback>
        </b-form-group>
      </b-form>
    </b-modal>
    <b-modal
      id="edit-scenery"
      ref="edit-scenery"
      title="Edit Scenery"
      size="md"
      @hidden="resetEditSceneryForm"
      @ok="onSubmitEditScenery"
    >
      <b-form ref="edit-scenery-form" @submit.stop.prevent="onSubmitEditScenery">
        <b-form-group
          id="scenery-type-input-group"
          label="Scenery Type"
          label-for="scenery-type-input"
        >
          <b-form-select
            id="scenery-type-input"
            v-model="$v.editSceneryFormState.scenery_type_id.$model"
            :options="sceneryTypeOptions"
            :state="validateEditSceneryState('scenery_type_id')"
            aria-describedby="scenery-type-feedback"
          />
          <b-form-invalid-feedback id="scenery-type-feedback">
            This is a required field.
          </b-form-invalid-feedback>
        </b-form-group>
        <b-form-group id="name-input-group" label="Name" label-for="name-input">
          <b-form-input
            id="name-input"
            v-model="$v.editSceneryFormState.name.$model"
            name="name-input"
            :state="validateEditSceneryState('name')"
            aria-describedby="name-feedback"
          />
          <b-form-invalid-feedback id="name-feedback">
            This is a required field.
          </b-form-invalid-feedback>
        </b-form-group>
        <b-form-group
          id="description-input-group"
          label="Description"
          label-for="description-input"
        >
          <b-form-input
            id="description-input"
            v-model="$v.editSceneryFormState.description.$model"
            name="description-input"
            :state="validateEditSceneryState('description')"
            aria-describedby="name-feedback"
          />
          <b-form-invalid-feedback id="description-feedback">
            This is a required field.
          </b-form-invalid-feedback>
        </b-form-group>
      </b-form>
    </b-modal>
  </b-container>
</template>

<script>
import { required } from 'vuelidate/lib/validators';
import { mapGetters, mapActions } from 'vuex';
import { notNull } from '@/js/customValidators';

export default {
  name: 'SceneryList',
  data() {
    return {
      sceneryTypeFields: ['name', 'description', { key: 'btn', label: '' }],
      sceneryFields: [
        'name',
        'description',
        { key: 'scenery_type_id', label: 'Scenery Type' },
        { key: 'btn', label: '' },
      ],
      newSceneryTypeFormState: {
        name: '',
        description: '',
      },
      newSceneryFormState: {
        name: '',
        description: '',
        scenery_type_id: null,
      },
      rowsPerPage: 15,
      currentSceneryPage: 1,
      currentSceneryTypesPage: 1,
      editSceneryTypeFormState: {
        id: null,
        name: '',
        description: '',
      },
      editSceneryFormState: {
        id: null,
        name: '',
        description: '',
        scenery_type_id: null,
      },
    };
  },
  validations: {
    newSceneryTypeFormState: {
      name: {
        required,
      },
      description: {},
    },
    newSceneryFormState: {
      name: {
        required,
      },
      description: {},
      scenery_type_id: {
        required,
        notNull,
      },
    },
    editSceneryTypeFormState: {
      name: {
        required,
      },
      description: {},
    },
    editSceneryFormState: {
      name: {
        required,
      },
      description: {},
      scenery_type_id: {
        required,
        notNull,
      },
    },
  },
  computed: {
    sceneryTypeOptions() {
      return [
        { value: null, text: 'Please select an option', disabled: true },
        ...this.SCENERY_TYPES.map((sceneryType) => ({
          value: sceneryType.id,
          text: sceneryType.name,
        })),
      ];
    },
    ...mapGetters(['SCENERY_LIST', 'SCENERY_TYPES', 'IS_SHOW_EDITOR', 'SCENERY_TYPE_BY_ID']),
  },
  async mounted() {
    await this.GET_SCENERY_TYPES();
    await this.GET_SCENERY_LIST();
  },
  methods: {
    resetNewSceneryTypeForm() {
      this.newSceneryTypeFormState = {
        name: '',
        description: '',
      };

      this.$nextTick(() => {
        this.$v.$reset();
      });
    },
    resetNewSceneryForm() {
      this.newSceneryFormState = {
        name: '',
        description: '',
      };

      this.$nextTick(() => {
        this.$v.$reset();
      });
    },
    async onSubmitNewSceneryType(event) {
      this.$v.newSceneryTypeFormState.$touch();
      if (this.$v.newSceneryTypeFormState.$anyError) {
        event.preventDefault();
      } else {
        await this.ADD_SCENERY_TYPE(this.newSceneryTypeFormState);
        this.resetNewSceneryTypeForm();
      }
    },
    async onSubmitNewScenery(event) {
      this.$v.newSceneryFormState.$touch();
      if (this.$v.newSceneryFormState.$anyError) {
        event.preventDefault();
      } else {
        await this.ADD_SCENERY(this.newSceneryFormState);
        this.resetNewSceneryForm();
      }
    },
    validateNewSceneryTypeState(name) {
      const { $dirty, $error } = this.$v.newSceneryTypeFormState[name];
      return $dirty ? !$error : null;
    },
    validateNewSceneryState(name) {
      const { $dirty, $error } = this.$v.newSceneryFormState[name];
      return $dirty ? !$error : null;
    },
    openEditSceneryTypeForm(sceneryType) {
      if (sceneryType != null) {
        this.editSceneryTypeFormState.id = sceneryType.item.id;
        this.editSceneryTypeFormState.name = sceneryType.item.name;
        this.editSceneryTypeFormState.description = sceneryType.item.description;
        this.$bvModal.show('edit-scenery-type');
      }
    },
    openEditSceneryForm(sceneryMember) {
      if (sceneryMember != null) {
        this.editSceneryFormState.id = sceneryMember.item.id;
        this.editSceneryFormState.name = sceneryMember.item.name;
        this.editSceneryFormState.description = sceneryMember.item.description;
        this.$bvModal.show('edit-scenery');
      }
    },
    resetEditSceneryTypeForm() {
      this.editSceneryTypeFormState = {
        id: null,
        name: '',
        description: '',
      };

      this.$nextTick(() => {
        this.$v.$reset();
      });
    },
    resetEditSceneryForm() {
      this.editSceneryFormState = {
        id: null,
        name: '',
        description: '',
      };

      this.$nextTick(() => {
        this.$v.$reset();
      });
    },
    async onSubmitEditSceneryType(event) {
      this.$v.editSceneryTypeFormState.$touch();
      if (this.$v.editSceneryTypeFormState.$anyError) {
        event.preventDefault();
      } else {
        await this.UPDATE_SCENERY_TYPE(this.editSceneryTypeFormState);
        this.resetEditSceneryTypeForm();
      }
    },
    async onSubmitEditScenery(event) {
      this.$v.editSceneryFormState.$touch();
      if (this.$v.editSceneryFormState.$anyError) {
        event.preventDefault();
      } else {
        await this.UPDATE_SCENERY(this.editSceneryFormState);
        this.resetEditSceneryForm();
      }
    },
    validateEditSceneryTypeState(name) {
      const { $dirty, $error } = this.$v.editSceneryTypeFormState[name];
      return $dirty ? !$error : null;
    },
    validateEditSceneryState(name) {
      const { $dirty, $error } = this.$v.editSceneryFormState[name];
      return $dirty ? !$error : null;
    },
    async deleteSceneryType(sceneryType) {
      const sceneryDeleted = this.SCENERY_LIST.filter(
        (scenery) => scenery.scenery_type_id === sceneryType.item.id
      ).length;
      let msg = `Are you sure you want to delete ${sceneryType.item.name}?`;
      if (sceneryDeleted > 0) {
        msg = `${msg} This will also delete ${sceneryDeleted} scenery items.`;
      }
      const action = await this.$bvModal.msgBoxConfirm(msg, {});
      if (action === true) {
        await this.DELETE_SCENERY_TYPE(sceneryType.item.id);
      }
    },
    async deleteSceneryItem(sceneryMember) {
      const msg = `Are you sure you want to delete ${sceneryMember.item.name}?`;
      const action = await this.$bvModal.msgBoxConfirm(msg, {});
      if (action === true) {
        await this.DELETE_SCENERY(sceneryMember.item.id);
      }
    },
    ...mapActions([
      'GET_SCENERY_TYPES',
      'GET_SCENERY_LIST',
      'ADD_SCENERY_TYPE',
      'ADD_SCENERY',
      'DELETE_SCENERY_TYPE',
      'DELETE_SCENERY',
      'UPDATE_SCENERY_TYPE',
      'UPDATE_SCENERY',
    ]),
  },
};
</script>
