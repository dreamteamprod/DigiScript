<template>
  <div class="config">
    <h1>DigiScript Config</h1>
    <b-table-simple>
      <b-tbody>
        <b-tr>
          <b-td>
            <b>Current Show</b>
          </b-td>
          <b-td>
            <p v-if="this.$store.state.system.settings['current_show'] != null">
              {{ this.$store.state.system.settings['current_show'] }}
            </p>
            <b v-else>No show loaded</b>
          </b-td>
          <b-td>
            <b-button-group>
              <b-button variant="outline-success"
                        v-b-modal.show-load
                        :disabled="this.$store.state.system.availableShows.length === 0">
                Load Show
              </b-button>
              <b-button variant="outline-success" v-b-modal.show-config>Setup New Show</b-button>
            </b-button-group>
          </b-td>
        </b-tr>
      </b-tbody>
    </b-table-simple>
    <b-modal id="show-config" title="Setup New Show" ref="modal" @show="resetForm"
             @hidden="resetForm" @ok="onSubmit">
      <b-form @submit.stop.prevent="onSubmit" ref="form">
        <b-form-group id="name-input-group" label="Name" label-for="name-input">
          <b-form-input
            id="name-input"
            name="name-input"
            v-model="$v.formState.name.$model"
            :state="validateState('name')"
            aria-describedby="name-feedback"
          ></b-form-input>

          <b-form-invalid-feedback
            id="name-feedback"
          >This is a required field and must be less than 100 characters.
          </b-form-invalid-feedback>
        </b-form-group>

        <b-form-group id="start-input-group" label="Start Date" label-for="start-input">
          <b-form-input id="start-input" name="start-input" type="date"
                        v-model="$v.formState.start.$model"
                        :state="validateState('start')"
                        aria-describedby="start-feedback">
          </b-form-input>
          <b-form-invalid-feedback
            id="start-feedback"
          >This is a required field.
          </b-form-invalid-feedback>
        </b-form-group>

        <b-form-group id="end-input-group" label="End Date" label-for="end-input">
          <b-form-input id="end-input" name="end-input" type="date"
                        v-model="$v.formState.end.$model"
                        :state="validateState('end')"
                        aria-describedby="end-feedback">
          </b-form-input>
          <b-form-invalid-feedback
            id="end-feedback"
          >This is a required field.
          </b-form-invalid-feedback>
        </b-form-group>
      </b-form>
    </b-modal>
    <b-modal id="show-load" title="Load Show" ref="load-modal" size="lg">
      <div class="overflow-auto">
        <b-table
          id="shows-table"
          :items="this.$store.state.system.availableShows"
          :fields="fields"
          :per-page="perPage"
          :current-page="currentPage"
          small
        >
          <template #cell(btn)="data">
            <b-button variant="primary">Load Show</b-button>
          </template>
        </b-table>
        <b-pagination
          v-model="currentPage"
          :total-rows="this.$store.state.system.availableShows.length"
          :per-page="perPage"
          aria-controls="shows-table"
          class="justify-content-center"
        ></b-pagination>
      </div>
    </b-modal>
  </div>
</template>

<script>
import { required, maxLength } from 'vuelidate/lib/validators';
import { mapMutations } from 'vuex';

export default {
  name: 'ConfigView',
  data() {
    return {
      perPage: 5,
      currentPage: 1,
      formState: {
        name: null,
        start: null,
        end: null,
      },
      fields: [
        { key: 'id', label: 'ID' },
        'name',
        'start_date',
        'end_date',
        'created_at',
        { key: 'btn', label: '' },
      ],
    };
  },
  validations: {
    formState: {
      name: {
        required,
        maxLength: maxLength(100),
      },
      start: {
        required,
      },
      end: {
        required,
      },
    },
  },
  async mounted() {
    await this.getAvailableShows();
  },
  methods: {
    async getAvailableShows() {
      const response = await fetch(`${utils.makeURL('/api/v1/shows')}`);
      if (response.ok) {
        const shows = await response.json();
        this.UPDATE_SHOWS(shows.shows);
      } else {
        console.error('Unable to get available shows');
      }
    },
    validateState(name) {
      const { $dirty, $error } = this.$v.formState[name];
      return $dirty ? !$error : null;
    },
    resetForm() {
      this.formState = {
        name: null,
        start: null,
        end: null,
      };

      this.$nextTick(() => {
        this.$v.$reset();
      });
    },
    async onSubmit(event) {
      this.$v.formState.$touch();
      if (this.$v.formState.$anyError) {
        event.preventDefault();
        return;
      }

      const response = await fetch(`${utils.makeURL('/api/v1/show')}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(this.formState),
      });
      if (response.ok) {
        const settings = await response.json();
        await this.getAvailableShows();
        this.$toast.success('Created new show!');
        this.resetForm();
      } else {
        this.$toast.error('Unable to save show');
        console.error('Unable to create new show');
        event.preventDefault();
      }
    },
    ...mapMutations(['UPDATE_SHOWS']),
  },
};
</script>

<style scoped>

</style>
