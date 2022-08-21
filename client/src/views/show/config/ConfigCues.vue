<template>
  <b-container class="mx-0" fluid>
    <b-row>
      <b-col cols="7">
        <h5>Cues</h5>
      </b-col>
      <b-col cols="5">
        <h5>Cue Types</h5>
        <b-table id="cue-types-table" :items="this.CUE_TYPES" :fields="cueTypeFields" show-empty>
          <template #head(btn)="data">
            <b-button variant="outline-success" v-b-modal.new-cue-type>
              New Cue Type
            </b-button>
          </template>
          <template #cell(colour)="data">
            <p :style="{color: data.item.colour}">
              <b-icon-square-fill />
            </p>
          </template>
          <template #cell(btn)="data">
            <b-button-group>
              <b-button variant="danger" @click="deleteCueType(data)">
                Delete
              </b-button>
            </b-button-group>
          </template>
        </b-table>
      </b-col>
    </b-row>
    <b-modal id="new-cue-type" title="Add Cue Type" ref="new-cue-type" size="md"
             @show="resetNewCueTypeForm" @hidden="resetNewCueTypeForm"
             @ok="onSubmitNewCueType">
      <b-form @submit.stop.prevent="onSubmitNewCueType" ref="new-cue-type-form">
        <b-form-group id="prefix-input-group" label="Prefix" label-for="prefix-input">
          <b-form-input
            id="prefix-input"
            name="prefix-input"
            v-model="$v.newCueTypeForm.prefix.$model"
            :state="validateNewCueTypeState('prefix')"
            aria-describedby="prefix-feedback"
          ></b-form-input>
          <b-form-invalid-feedback
            id="prefix-feedback"
          >This is a required field and must be 5 characters or less.
          </b-form-invalid-feedback>
        </b-form-group>
        <b-form-group id="description-input-group" label="Description"
                      label-for="description-input">
          <b-form-input
            id="description-input"
            name="description-input"
            v-model="$v.newCueTypeForm.description.$model"
            :state="validateNewCueTypeState('description')"
            aria-describedby="description-feedback"
          ></b-form-input>
          <b-form-invalid-feedback
            id="description-feedback"
          >This is a required field and must be 100 characters or less.
          </b-form-invalid-feedback>
        </b-form-group>
        <b-form-group id="colour-input-group" label="Colour" label-for="colour-input">
          <b-form-input
            id="colour-input"
            name="colour-input"
            type="color"
            v-model="$v.newCueTypeForm.colour.$model"
            :state="validateNewCueTypeState('colour')"
            aria-describedby="colour-feedback">
          </b-form-input>
          <b-form-invalid-feedback
            id="colour-feedback"
          >This is a required field.
          </b-form-invalid-feedback>
        </b-form-group>
      </b-form>
    </b-modal>
  </b-container>
</template>

<script>
import { required, maxLength } from 'vuelidate/lib/validators';
import { mapGetters, mapActions } from 'vuex';

export default {
  name: 'ConfigCues',
  data() {
    return {
      cueTypeFields: [
        { key: 'id', label: 'ID' },
        'prefix',
        'description',
        'colour',
        { key: 'btn', label: '' },
      ],
      newCueTypeForm: {
        prefix: '',
        description: '',
        colour: '#000000',
      },
    };
  },
  validations: {
    newCueTypeForm: {
      prefix: {
        required,
        maxLength: maxLength(5),
      },
      description: {
        maxLength: maxLength(100),
      },
      colour: {
        required,
      },
    },
  },
  async mounted() {
    await this.GET_CUE_TYPES();
  },
  methods: {
    ...mapActions(['GET_CUE_TYPES', 'ADD_CUE_TYPE', 'DELETE_CUE_TYPE']),
    resetNewCueTypeForm() {
      this.newCueTypeForm = {
        prefix: '',
        description: '',
        colour: '#000000',
      };

      this.$nextTick(() => {
        this.$v.$reset();
      });
    },
    validateNewCueTypeState(name) {
      const { $dirty, $error } = this.$v.newCueTypeForm[name];
      return $dirty ? !$error : null;
    },
    async onSubmitNewCueType(event) {
      this.$v.newCueTypeForm.$touch();
      if (this.$v.newCueTypeForm.$anyError) {
        event.preventDefault();
      } else {
        await this.ADD_CUE_TYPE(this.newCueTypeForm);
        this.resetNewForm();
      }
    },
    async deleteCueType(cueType) {
      const msg = `Are you sure you want to delete ${cueType.item.prefix}?`;
      const action = await this.$bvModal.msgBoxConfirm(msg, {});
      if (action === true) {
        await this.DELETE_CUE_TYPE(cueType.item.id);
      }
    },
  },
  computed: {
    ...mapGetters(['CUE_TYPES']),
  },
};
</script>
