<template>
  <b-container>
    <b-row>
      <b-col>
        <b-table id="cast-table" :items="this.ACT_LIST" :fields="actFields" show-empty>
          <template #head(btn)="data">
            <b-button variant="outline-success" v-b-modal.new-act>
              New Act
            </b-button>
          </template>
          <template #cell(interval_after)="data">
            <b-icon-check-square-fill variant="success" v-if="data.item.interval_after"/>
            <b-icon-x-square-fill v-else variant="danger" />
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
          v-show="this.ACT_LIST.length > rowsPerPage"
          v-model="currentPage"
          :total-rows="this.ACT_LIST.length"
          :per-page="rowsPerPage"
          aria-controls="cast-table"
          class="justify-content-center"
        ></b-pagination>
      </b-col>
    </b-row>
    <b-modal id="new-act" title="Add New Act" ref="new-act" size="md"
             @show="resetNewForm" @hidden="resetNewForm" @ok="onSubmitNew">
      <b-form @submit.stop.prevent="onSubmitNew" ref="new-act-form">
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
        <b-form-group id="interval-input-group" label="Interval After" label-for="interval-input">
          <b-form-checkbox id="interval-input" name="interval-input"
                           v-model="newFormState.interval_after">
          </b-form-checkbox>
        </b-form-group>
      </b-form>
    </b-modal>
  </b-container>
</template>

<script>
import { required } from 'vuelidate/lib/validators';
import { mapGetters, mapActions } from 'vuex';

export default {
  name: 'ConfigActs',
  data() {
    return {
      rowsPerPage: 15,
      currentPage: 1,
      actFields: [
        { key: 'id', label: 'ID' },
        'name',
        { key: 'interval_after', label: 'Interval After' },
        { key: 'btn', label: '' },
      ],
      newFormState: {
        name: '',
        interval_after: false,
      },
    };
  },
  validations: {
    newFormState: {
      name: {
        required,
      },
    },
  },
  async mounted() {
    await this.GET_ACT_LIST();
  },
  methods: {
    resetNewForm() {
      this.newFormState = {
        name: '',
        interval_after: false,
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
        await this.ADD_ACT(this.newFormState);
        this.resetNewForm();
      }
    },
    ...mapActions(['GET_ACT_LIST', 'ADD_ACT', 'DELETE_ACT', 'UPDATE_ACT']),
  },
  computed: {
    ...mapGetters(['ACT_LIST']),
  },
};
</script>

<style scoped>

</style>
