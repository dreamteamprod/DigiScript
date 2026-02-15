<template>
  <b-container class="mx-0" fluid>
    <template v-if="loaded">
      <b-row>
        <b-col>
          <b-table
            id="shows-table"
            :items="AVAILABLE_SHOWS"
            :fields="showFields"
            :per-page="rowsPerPage"
            :current-page="currentPage"
          >
            <template #head(btn)="data">
              <b-button v-b-modal.show-config variant="success"> Setup New Show </b-button>
            </template>
            <template #cell(btn)="data">
              <b-button
                variant="primary"
                :disabled="
                  isSubmittingLoad || (CURRENT_SHOW != null && CURRENT_SHOW.id === data.item.id)
                "
                @click="loadShow(data.item)"
              >
                {{
                  (CURRENT_SHOW != null && CURRENT_SHOW.id !== data.item.id) || CURRENT_SHOW == null
                    ? 'Load Show'
                    : 'Loaded'
                }}
              </b-button>
            </template>
          </b-table>
          <b-pagination
            v-show="AVAILABLE_SHOWS.length > rowsPerPage"
            v-model="currentPage"
            :total-rows="AVAILABLE_SHOWS.length"
            :per-page="rowsPerPage"
            aria-controls="shows-table"
            class="justify-content-center"
          />
        </b-col>
      </b-row>
    </template>
    <b-row v-else>
      <b-col class="text-center">
        <b-spinner label="Loading shows..." variant="primary" />
      </b-col>
    </b-row>
    <b-modal
      id="show-config"
      ref="modal"
      title="Setup New Show"
      :ok-disabled="isSubmittingShow"
      @show="resetForm"
      @hidden="resetForm"
      @ok="onSubmit"
    >
      <div>
        <b-form ref="form" @submit.stop.prevent="onSubmit">
          <b-form-group id="name-input-group" label="Name" label-for="name-input">
            <b-form-input
              id="name-input"
              v-model="$v.formState.name.$model"
              name="name-input"
              :state="validateState('name')"
              aria-describedby="name-feedback"
            />

            <b-form-invalid-feedback id="name-feedback">
              This is a required field and must be less than 100 characters.
            </b-form-invalid-feedback>
          </b-form-group>

          <b-form-group id="start-input-group" label="Start Date" label-for="start-input">
            <b-form-input
              id="start-input"
              v-model="$v.formState.start.$model"
              name="start-input"
              type="date"
              :state="validateState('start')"
              aria-describedby="start-feedback"
            />
            <b-form-invalid-feedback id="start-feedback">
              This is a required field and must be before or the same as the end date.
            </b-form-invalid-feedback>
          </b-form-group>

          <b-form-group id="end-input-group" label="End Date" label-for="end-input">
            <b-form-input
              id="end-input"
              v-model="$v.formState.end.$model"
              name="end-input"
              type="date"
              :state="validateState('end')"
              aria-describedby="end-feedback"
            />
            <b-form-invalid-feedback id="end-feedback">
              This is a required field and must be after or the same as the start date.
            </b-form-invalid-feedback>
          </b-form-group>
        </b-form>
      </div>
      <hr />
      <div>
        <b-button v-b-toggle.advanced-options-collapse>
          <b-icon icon="gear-wide-connected" /> Advanced Options
        </b-button>
        <b-collapse id="advanced-options-collapse" style="margin-top: 0.5rem">
          <b-card>
            <b-form-group id="script-mode-group" label="Script Mode" label-for="script-mode-input">
              <b-alert variant="secondary" show>
                <p>Change the type of script for this show.</p>
              </b-alert>
              <b-form-select
                id="script-mode-input"
                v-model="$v.formState.script_mode.$model"
                :options="SCRIPT_MODES"
                :state="validateState('script_mode')"
              />
            </b-form-group>
          </b-card>
        </b-collapse>
      </div>
      <template #modal-footer="{ ok, cancel }">
        <b-button variant="secondary" @click.stop="cancel()"> Cancel </b-button>
        <b-button variant="primary" :disabled="isSubmittingShow" @click.stop="saveAndLoad">
          Save and Load
        </b-button>
        <b-button variant="primary" :disabled="isSubmittingShow" @click.stop="ok()">
          Save
        </b-button>
      </template>
    </b-modal>
  </b-container>
</template>

<script>
import { required, maxLength } from 'vuelidate/lib/validators';
import { mapGetters, mapActions } from 'vuex';
import { makeURL } from '@/js/utils';
import log from 'loglevel';

export default {
  name: 'ConfigShows',
  data() {
    return {
      loaded: false,
      showFields: [
        { key: 'id', label: 'ID' },
        'name',
        'start_date',
        'end_date',
        'created_at',
        { key: 'btn', label: '' },
      ],
      rowsPerPage: 15,
      currentPage: 1,
      isSubmittingLoad: false,
      isSubmittingShow: false,
      formState: {
        name: null,
        start: null,
        end: null,
        script_mode: null,
      },
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
        beforeEnd: (value, vm) =>
          value == null && vm.end != null ? false : new Date(value) <= new Date(vm.end),
      },
      end: {
        required,
        afterStart: (value, vm) =>
          value == null && vm.start != null ? false : new Date(value) >= new Date(vm.start),
      },
      script_mode: {
        required,
      },
    },
  },
  computed: {
    ...mapGetters(['AVAILABLE_SHOWS', 'CURRENT_SHOW', 'SCRIPT_MODES']),
  },
  async mounted() {
    await Promise.all([this.GET_AVAILABLE_SHOWS(), this.GET_SCRIPT_MODES()]);
    this.loaded = true;
  },
  methods: {
    async saveAndLoad(event) {
      await this.saveShow(event, true);
    },
    async onSubmit(event) {
      await this.saveShow(event, false);
    },
    async saveShow(event, load) {
      this.$v.formState.$touch();
      if (this.$v.formState.$anyError) {
        event.preventDefault();
        return;
      }

      if (this.isSubmittingShow) {
        event.preventDefault();
        return;
      }

      this.isSubmittingShow = true;

      try {
        const searchParams = new URLSearchParams({
          load,
        });
        const response = await fetch(`${makeURL('/api/v1/show')}?${searchParams}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(this.formState),
        });
        if (response.ok) {
          await this.GET_AVAILABLE_SHOWS();
          this.$toast.success('Created new show!');
          this.$bvModal.hide('show-config');
          this.resetForm();
        } else {
          this.$toast.error('Unable to save show');
          log.error('Unable to create new show');
          event.preventDefault();
        }
      } catch (error) {
        this.$toast.error('Unable to save show');
        log.error('Error creating new show:', error);
        event.preventDefault();
      } finally {
        this.isSubmittingShow = false;
      }
    },
    async loadShow(show) {
      if (this.isSubmittingLoad) {
        return;
      }

      this.isSubmittingLoad = true;

      try {
        const response = await fetch(`${makeURL('/api/v1/settings')}`, {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            current_show: show.id,
          }),
        });
        if (response.ok) {
          this.$toast.success('Loaded show!');
          this.$bvModal.hide('show-load');
        } else {
          this.$toast.error('Unable to load show');
          log.error('Unable to load show');
        }
      } catch (error) {
        this.$toast.error('Unable to load show');
        log.error('Error loading show:', error);
      } finally {
        this.isSubmittingLoad = false;
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
        script_mode: this.SCRIPT_MODES[0].value,
      };
      this.isSubmittingShow = false;

      this.$nextTick(() => {
        this.$v.$reset();
      });
    },
    ...mapActions(['GET_AVAILABLE_SHOWS', 'GET_SCRIPT_MODES']),
  },
};
</script>
