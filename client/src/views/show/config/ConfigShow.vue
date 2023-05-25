<template>
  <b-container
    id="show-config"
    class="mx-0"
    fluid
  >
    <b-row>
      <b-col
        cols="12"
        class="text-right"
      >
        <b-button
          variant="warning"
          @click="openEditForm()"
        >
          Edit Show
        </b-button>
      </b-col>
    </b-row>
    <b-row>
      <b-col>
        <b-table-simple>
          <b-tr
            v-for="key in orderedKeys"
            :key="key"
          >
            <b-th>{{ key }}</b-th>
            <b-td>{{ tableData[key] != null ? tableData[key] : 'N/A' }}</b-td>
          </b-tr>
        </b-table-simple>
      </b-col>
    </b-row>
    <b-modal
      id="edit-show"
      ref="edit-show"
      title="Edit Show"
      size="md"
      @hidden="resetEditForm"
      @ok="onSubmitEdit"
    >
      <b-form
        ref="edit-show-form"
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
            This is a required field and must be less than 100 characters.
          </b-form-invalid-feedback>
        </b-form-group>

        <b-form-group
          id="start-input-group"
          label="Start Date"
          label-for="start-input"
        >
          <b-form-input
            id="start-input"
            v-model="$v.editFormState.start_date.$model"
            name="start-input"
            type="date"
            :state="validateEditState('start_date')"
            aria-describedby="start-feedback"
          />
          <b-form-invalid-feedback
            id="start-feedback"
          >
            This is a required field and must be before or the same as the end date.
          </b-form-invalid-feedback>
        </b-form-group>

        <b-form-group
          id="end-input-group"
          label="End Date"
          label-for="end-input"
        >
          <b-form-input
            id="end-input"
            v-model="$v.editFormState.end_date.$model"
            name="end-input"
            type="date"
            :state="validateEditState('end_date')"
            aria-describedby="end-feedback"
          />
          <b-form-invalid-feedback
            id="end-feedback"
          >
            This is a required field and must be after or the same as the start date.
          </b-form-invalid-feedback>
        </b-form-group>

        <b-form-group
          id="act-input-group"
          label="Act"
          label-for="act-input"
        >
          <b-form-select
            id="act-input"
            v-model="$v.editFormState.first_act_id.$model"
            :options="actOptions"
            :state="validateEditState('first_act_id')"
          />
        </b-form-group>
      </b-form>
    </b-modal>
  </b-container>
</template>

<script>
import { required, maxLength } from 'vuelidate/lib/validators';
import { mapGetters, mapActions } from 'vuex';
import { titleCase } from '@/js/utils';

export default {
  name: 'ConfigShow',
  data() {
    return {
      editFormState: {
        name: null,
        start_date: null,
        end_date: null,
        first_act_id: null,
      },
    };
  },
  async mounted() {
    await this.GET_SHOW_DETAILS();
    await this.GET_ACT_LIST();
  },
  validations: {
    editFormState: {
      name: {
        required,
        maxLength: maxLength(100),
      },
      start_date: {
        required,
        beforeEnd: (value, vm) => (value == null && vm.end_date != null ? false
          : new Date(value) <= new Date(vm.end_date)),
      },
      end_date: {
        required,
        afterStart: (value, vm) => (value == null && vm.start_date != null ? false
          : new Date(value) >= new Date(vm.start_date)),
      },
      first_act_id: {},
    },
  },
  methods: {
    titleCase,
    ...mapActions(['GET_SHOW_DETAILS', 'GET_ACT_LIST', 'UPDATE_SHOW']),
    resetEditForm() {
      this.editFormState = {
        name: null,
        start_date: null,
        end_date: null,
        first_act_id: null,
      };

      this.$nextTick(() => {
        this.$v.$reset();
      });
    },
    openEditForm() {
      Object.keys(this.editFormState).forEach(function (key) {
        this.editFormState[key] = this.CURRENT_SHOW[key];
      }, this);
      this.$bvModal.show('edit-show');
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
        await this.UPDATE_SHOW(this.editFormState);
        this.resetEditForm();
      }
    },
  },
  computed: {
    tableData() {
      const data = {};
      Object.keys(this.CURRENT_SHOW).forEach(function (key) {
        data[this.titleCase(key, '_')] = this.CURRENT_SHOW[key];
      }, this);
      return data;
    },
    orderedKeys() {
      return Object.keys(this.tableData).sort();
    },
    actOptions() {
      return [
        { value: null, text: 'N/A', disabled: false },
        ...this.ACT_LIST.map((act) => ({ value: act.id, text: act.name })),
      ];
    },
    ...mapGetters(['CURRENT_SHOW', 'ACT_LIST']),
  },
};
</script>

<style scoped>
.row {
  margin-top: .5em;
  margin-bottom: .5em;
}
</style>
