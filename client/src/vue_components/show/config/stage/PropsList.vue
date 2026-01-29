<template>
  <b-container class="mx-0" fluid>
    <b-row>
      <b-col cols="5">
        <h5>Prop Types</h5>
        <b-table
          id="prop-type-table"
          :items="PROP_TYPES"
          :fields="propTypesFields"
          :per-page="rowsPerPage"
          :current-page="currentPropPage"
          show-empty
        >
          <template #head(btn)="data">
            <b-button v-if="IS_SHOW_EDITOR" v-b-modal.new-prop-type variant="outline-success">
              New Prop Type
            </b-button>
          </template>
          <template #cell(btn)="data">
            <b-button-group v-if="IS_SHOW_EDITOR">
              <b-button variant="warning" @click="openEditPropTypeForm(data)"> Edit </b-button>
              <b-button variant="danger" @click="deletePropType(data)"> Delete </b-button>
            </b-button-group>
          </template>
        </b-table>
        <b-pagination
          v-show="PROP_TYPES.length > rowsPerPage"
          v-model="currentPropTypePage"
          :total-rows="PROP_TYPES.length"
          :per-page="rowsPerPage"
          aria-controls="prop-type-table"
          class="justify-content-center"
        />
      </b-col>
      <b-col cols="7">
        <h5>Props List</h5>
        <b-table
          id="props-table"
          :items="PROPS_LIST"
          :fields="propsFields"
          :per-page="rowsPerPage"
          :current-page="currentPropPage"
          show-empty
        >
          <template #head(btn)="data">
            <b-button v-if="IS_SHOW_EDITOR" v-b-modal.new-props variant="outline-success">
              New Props Item
            </b-button>
          </template>
          <template #cell(prop_type_id)="data">
            <span>{{ PROP_TYPE_BY_ID(data.item.prop_type_id).name }}</span>
          </template>
          <template #cell(btn)="data">
            <b-button-group v-if="IS_SHOW_EDITOR">
              <b-button variant="warning" @click="openEditPropForm(data)"> Edit </b-button>
              <b-button variant="danger" @click="deletePropsItem(data)"> Delete </b-button>
            </b-button-group>
          </template>
        </b-table>
        <b-pagination
          v-show="PROPS_LIST.length > rowsPerPage"
          v-model="currentPropPage"
          :total-rows="PROPS_LIST.length"
          :per-page="rowsPerPage"
          aria-controls="props-table"
          class="justify-content-center"
        />
      </b-col>
    </b-row>
    <b-modal
      id="new-prop-type"
      ref="new-prop-type"
      title="Add New Prop Type"
      size="md"
      @show="resetNewPropTypeForm"
      @hidden="resetNewPropTypeForm"
      @ok="onSubmitNewPropType"
    >
      <b-form ref="new-prop-type-form" @submit.stop.prevent="onSubmitNewPropType">
        <b-form-group id="name-input-group" label="Name" label-for="name-input">
          <b-form-input
            id="name-input"
            v-model="$v.newPropTypeFormState.name.$model"
            name="name-input"
            :state="validateNewPropTypeState('name')"
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
            v-model="$v.newPropTypeFormState.description.$model"
            name="description-input"
            :state="validateNewPropTypeState('description')"
            aria-describedby="name-feedback"
          />
          <b-form-invalid-feedback id="description-feedback">
            This is a required field.
          </b-form-invalid-feedback>
        </b-form-group>
      </b-form>
    </b-modal>
    <b-modal
      id="edit-prop-type"
      ref="edit-prop-type"
      title="Edit Prop Type"
      size="md"
      @hidden="resetEditPropTypeForm"
      @ok="onSubmitEditPropType"
    >
      <b-form ref="edit-prop-type-form" @submit.stop.prevent="onSubmitEditPropType">
        <b-form-group id="name-input-group" label="Name" label-for="name-input">
          <b-form-input
            id="name-input"
            v-model="$v.editPropTypeFormState.name.$model"
            name="name-input"
            :state="validateEditPropTypeState('name')"
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
            v-model="$v.editPropTypeFormState.description.$model"
            name="description-input"
            :state="validateEditPropTypeState('description')"
            aria-describedby="name-feedback"
          />
          <b-form-invalid-feedback id="description-feedback">
            This is a required field.
          </b-form-invalid-feedback>
        </b-form-group>
      </b-form>
    </b-modal>
    <b-modal
      id="new-props"
      ref="new-props"
      title="Add New Prop"
      size="md"
      @show="resetNewPropForm"
      @hidden="resetNewPropForm"
      @ok="onSubmitNewProp"
    >
      <b-form ref="new-props-form" @submit.stop.prevent="onSubmitNewProp">
        <b-form-group id="prop-type-input-group" label="Prop Type" label-for="prop-type-input">
          <b-form-select
            id="prop-type-input"
            v-model="$v.newPropFormState.prop_type_id.$model"
            :options="propTypeOptions"
            :state="validateNewPropState('prop_type_id')"
            aria-describedby="prop-type-feedback"
          />
          <b-form-invalid-feedback id="prop-type-feedback">
            This is a required field.
          </b-form-invalid-feedback>
        </b-form-group>
        <b-form-group id="name-input-group" label="Name" label-for="name-input">
          <b-form-input
            id="name-input"
            v-model="$v.newPropFormState.name.$model"
            name="name-input"
            :state="validateNewPropState('name')"
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
            v-model="$v.newPropFormState.description.$model"
            name="description-input"
            :state="validateNewPropState('description')"
            aria-describedby="name-feedback"
          />
          <b-form-invalid-feedback id="description-feedback">
            This is a required field.
          </b-form-invalid-feedback>
        </b-form-group>
      </b-form>
    </b-modal>
    <b-modal
      id="edit-props"
      ref="edit-props"
      title="Edit Props"
      size="md"
      @hidden="resetEditPropForm"
      @ok="onSubmitEditProp"
    >
      <b-form ref="edit-props-form" @submit.stop.prevent="onSubmitEditProp">
        <b-form-group id="prop-type-input-group" label="Prop Type" label-for="prop-type-input">
          <b-form-select
            id="prop-type-input"
            v-model="$v.editPropFormState.prop_type_id.$model"
            :options="propTypeOptions"
            :state="validateEditPropState('prop_type_id')"
            aria-describedby="prop-type-feedback"
          />
          <b-form-invalid-feedback id="prop-type-feedback">
            This is a required field.
          </b-form-invalid-feedback>
        </b-form-group>
        <b-form-group id="name-input-group" label="Name" label-for="name-input">
          <b-form-input
            id="name-input"
            v-model="$v.editPropFormState.name.$model"
            name="name-input"
            :state="validateEditPropState('name')"
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
            v-model="$v.editPropFormState.description.$model"
            name="description-input"
            :state="validateEditPropState('description')"
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
  name: 'PropsList',
  data() {
    return {
      propTypesFields: ['name', 'description', { key: 'btn', label: '' }],
      propsFields: [
        'name',
        'description',
        { key: 'prop_type_id', label: 'Prop Type' },
        { key: 'btn', label: '' },
      ],
      newPropTypeFormState: {
        name: '',
        description: '',
      },
      newPropFormState: {
        name: '',
        description: '',
        prop_type_id: null,
      },
      rowsPerPage: 15,
      currentPropPage: 1,
      currentPropTypePage: 1,
      editPropTypeFormState: {
        id: null,
        name: '',
        description: '',
      },
      editPropFormState: {
        id: null,
        name: '',
        description: '',
        prop_type_id: null,
      },
    };
  },
  validations: {
    newPropTypeFormState: {
      name: {
        required,
      },
      description: {},
    },
    newPropFormState: {
      name: {
        required,
      },
      description: {},
      prop_type_id: {
        required,
        notNull,
      },
    },
    editPropTypeFormState: {
      name: {
        required,
      },
      description: {},
    },
    editPropFormState: {
      name: {
        required,
      },
      description: {},
      prop_type_id: {
        required,
        notNull,
      },
    },
  },
  computed: {
    propTypeOptions() {
      return [
        { value: null, text: 'Please select an option', disabled: true },
        ...this.PROP_TYPES.map((propType) => ({ value: propType.id, text: propType.name })),
      ];
    },
    ...mapGetters(['PROPS_LIST', 'PROP_TYPES', 'IS_SHOW_EDITOR', 'PROP_TYPE_BY_ID']),
  },
  async mounted() {
    await this.GET_PROP_TYPES();
    await this.GET_PROPS_LIST();
  },
  methods: {
    resetNewPropTypeForm() {
      this.newPropTypeFormState = {
        name: '',
        description: '',
      };

      this.$nextTick(() => {
        this.$v.$reset();
      });
    },
    resetNewPropForm() {
      this.newPropFormState = {
        name: '',
        description: '',
        prop_type: null,
      };

      this.$nextTick(() => {
        this.$v.$reset();
      });
    },
    async onSubmitNewPropType(event) {
      this.$v.newPropTypeFormState.$touch();
      if (this.$v.newPropTypeFormState.$anyError) {
        event.preventDefault();
      } else {
        await this.ADD_PROP_TYPE(this.newPropTypeFormState);
        this.resetNewPropTypeForm();
      }
    },
    async onSubmitNewProp(event) {
      this.$v.newPropFormState.$touch();
      if (this.$v.newPropFormState.$anyError) {
        event.preventDefault();
      } else {
        await this.ADD_PROP(this.newPropFormState);
        this.resetNewPropForm();
      }
    },
    validateNewPropTypeState(name) {
      const { $dirty, $error } = this.$v.newPropTypeFormState[name];
      return $dirty ? !$error : null;
    },
    validateNewPropState(name) {
      const { $dirty, $error } = this.$v.newPropFormState[name];
      return $dirty ? !$error : null;
    },
    openEditPropTypeForm(propType) {
      if (propType != null) {
        this.editPropTypeFormState.id = propType.item.id;
        this.editPropTypeFormState.name = propType.item.name;
        this.editPropTypeFormState.description = propType.item.description;
        this.$bvModal.show('edit-prop-type');
      }
    },
    openEditPropForm(propsMember) {
      if (propsMember != null) {
        this.editPropFormState.id = propsMember.item.id;
        this.editPropFormState.name = propsMember.item.name;
        this.editPropFormState.description = propsMember.item.description;
        this.editPropFormState.prop_type_id = propsMember.item.prop_type_id;
        this.$bvModal.show('edit-props');
      }
    },
    resetEditPropTypeForm() {
      this.editPropTypeFormState = {
        id: null,
        name: '',
        description: '',
      };

      this.$nextTick(() => {
        this.$v.$reset();
      });
    },
    resetEditPropForm() {
      this.editPropFormState = {
        id: null,
        name: '',
        description: '',
        prop_type_id: null,
      };

      this.$nextTick(() => {
        this.$v.$reset();
      });
    },
    async onSubmitEditPropType(event) {
      this.$v.editPropTypeFormState.$touch();
      if (this.$v.editPropTypeFormState.$anyError) {
        event.preventDefault();
      } else {
        await this.UPDATE_PROP_TYPE(this.editPropTypeFormState);
        this.resetEditPropTypeForm();
      }
    },
    async onSubmitEditProp(event) {
      this.$v.editPropFormState.$touch();
      if (this.$v.editPropFormState.$anyError) {
        event.preventDefault();
      } else {
        await this.UPDATE_PROP(this.editPropFormState);
        this.resetEditPropForm();
      }
    },
    validateEditPropTypeState(name) {
      const { $dirty, $error } = this.$v.editPropTypeFormState[name];
      return $dirty ? !$error : null;
    },
    validateEditPropState(name) {
      const { $dirty, $error } = this.$v.editPropFormState[name];
      return $dirty ? !$error : null;
    },
    async deletePropType(propType) {
      const propsDeleted = this.PROPS_LIST.filter(
        (prop) => prop.prop_type_id === propType.item.id
      ).length;
      let msg = `Are you sure you want to delete ${propType.item.name}?`;
      if (propsDeleted > 0) {
        msg = `${msg} This will also delete ${propsDeleted} props.`;
      }
      const action = await this.$bvModal.msgBoxConfirm(msg, {});
      if (action === true) {
        await this.DELETE_PROP_TYPE(propType.item.id);
      }
    },
    async deletePropsItem(propsMember) {
      const msg = `Are you sure you want to delete ${propsMember.item.name}?`;
      const action = await this.$bvModal.msgBoxConfirm(msg, {});
      if (action === true) {
        await this.DELETE_PROP(propsMember.item.id);
      }
    },
    ...mapActions([
      'GET_PROP_TYPES',
      'GET_PROPS_LIST',
      'ADD_PROP_TYPE',
      'ADD_PROP',
      'DELETE_PROP_TYPE',
      'DELETE_PROP',
      'UPDATE_PROP_TYPE',
      'UPDATE_PROP',
    ]),
  },
};
</script>
