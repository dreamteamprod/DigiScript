<template>
  <div v-if="!loading" class="config">
    <b-table-simple>
      <b-tbody>
        <b-tr>
          <b-td>
            <b>Current Show</b>
          </b-td>
          <b-td>
            <p v-if="currentShowLoaded">
              {{ $store.state.currentShow['name'] }}
            </p>
            <b v-else>No show loaded</b>
          </b-td>
          <b-td>
            <b-button-group>
              <b-button
                v-b-modal.show-load
                variant="outline-success"
                :disabled="$store.state.system.availableShows.length === 0"
              >
                Load Show
              </b-button>
              <b-button v-b-modal.show-config variant="outline-success"> Setup New Show </b-button>
            </b-button-group>
          </b-td>
        </b-tr>
        <b-tr>
          <b-td>
            <b>Connected Clients</b>
          </b-td>
          <b-td>
            {{ connectedClients.length }}
          </b-td>
          <b-td>
            <b-button v-b-modal.connected-clients variant="outline-success">
              View Clients
            </b-button>
          </b-td>
        </b-tr>
        <b-tr>
          <b-td>
            <b>Version</b>
          </b-td>
          <b-td>
            {{ versionStatus.current_version || 'Unknown' }}
            <b-badge :variant="getVersionStatusVariant()" pill>
              {{ getVersionStatusText() }}
            </b-badge>
            <template v-if="versionStatus.update_available && versionStatus.latest_version">
              <br />
              <small class="text-muted">
                Latest: {{ versionStatus.latest_version }}
                <a
                  v-if="versionStatus.release_url"
                  :href="versionStatus.release_url"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  (Release Notes)
                </a>
              </small>
            </template>
            <template v-if="versionStatus.check_error">
              <br />
              <small class="text-danger">{{ versionStatus.check_error }}</small>
            </template>
          </b-td>
          <b-td>
            <b-button
              variant="outline-success"
              :disabled="isCheckingVersion"
              @click="checkForUpdates"
            >
              <b-spinner v-if="isCheckingVersion" small class="mr-1" />
              Check Now
            </b-button>
          </b-td>
        </b-tr>
      </b-tbody>
    </b-table-simple>
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
    <b-modal id="show-load" ref="load-modal" title="Load Show" size="lg">
      <div class="overflow-auto">
        <b-table
          id="shows-table"
          :items="$store.state.system.availableShows"
          :fields="showFields"
          :per-page="perPage"
          :current-page="currentPageShows"
          small
        >
          <template #cell(btn)="data">
            <b-button variant="primary" :disabled="isSubmittingLoad" @click="loadShow(data.item)">
              Load Show
            </b-button>
          </template>
        </b-table>
        <b-pagination
          v-model="currentPageShows"
          :total-rows="$store.state.system.availableShows.length"
          :per-page="perPage"
          aria-controls="shows-table"
          class="justify-content-center"
        />
      </div>
    </b-modal>
    <b-modal
      id="connected-clients"
      ref="connected-clients-modal"
      title="Connected Clients"
      size="lg"
    >
      <b-table
        id="shows-table"
        :items="connectedClients"
        :fields="clientFields"
        :per-page="perPage"
        :current-page="currentPageClients"
        small
      />
      <b-pagination
        v-model="currentPageClients"
        :total-rows="connectedClients.length"
        :per-page="perPage"
        aria-controls="shows-table"
        class="justify-content-center"
      />
    </b-modal>
  </div>
  <div v-else class="text-center center-spinner">
    <b-spinner style="width: 10rem; height: 10rem" variant="info" />
  </div>
</template>

<script>
import { required, maxLength } from 'vuelidate/lib/validators';
import { mapMutations, mapActions, mapGetters } from 'vuex';
import log from 'loglevel';

import { makeURL } from '@/js/utils';

export default {
  name: 'ConfigSystem',
  data() {
    return {
      perPage: 5,
      currentPageShows: 1,
      isSubmittingShow: false,
      isSubmittingLoad: false,
      formState: {
        name: null,
        start: null,
        end: null,
        script_mode: null,
      },
      showFields: [
        { key: 'id', label: 'ID' },
        'name',
        'start_date',
        'end_date',
        'created_at',
        { key: 'btn', label: '' },
      ],
      connectedClients: [],
      currentPageClients: 1,
      clientFields: [
        { key: 'internal_id', label: 'UUID' },
        { key: 'remote_ip', label: 'IP' },
        { key: 'is_editor', label: 'Editing Script' },
        'last_ping',
        'last_pong',
      ],
      clientTimeout: null,
      loading: true,
      versionStatus: {
        current_version: null,
        latest_version: null,
        update_available: false,
        release_url: null,
        last_checked: null,
        check_error: null,
      },
      isCheckingVersion: false,
      currentTime: Date.now(),
      timeUpdateInterval: null,
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
    currentShowLoaded() {
      return (
        this.$store.state.system.settings.current_show != null &&
        this.$store.state.currentShow != null
      );
    },
    ...mapGetters(['SCRIPT_MODES']),
  },
  async mounted() {
    await Promise.all([
      this.getAvailableShows(),
      this.getConnectedClients(),
      this.GET_SCRIPT_MODES(),
      this.getVersionStatus(),
    ]);
    this.loading = false;

    // Start time update interval for reactive "time ago" display
    this.timeUpdateInterval = setInterval(() => {
      this.currentTime = Date.now();
    }, 1000);
  },
  destroyed() {
    clearTimeout(this.clientTimeout);
    if (this.timeUpdateInterval) {
      clearInterval(this.timeUpdateInterval);
      this.timeUpdateInterval = null;
    }
  },
  methods: {
    async getAvailableShows() {
      const response = await fetch(`${makeURL('/api/v1/shows')}`);
      if (response.ok) {
        const shows = await response.json();
        this.UPDATE_SHOWS(shows.shows);
      } else {
        log.error('Unable to get available shows');
      }
    },
    async getConnectedClients() {
      const response = await fetch(`${makeURL('/api/v1/ws/sessions')}`);
      if (response.ok) {
        const sessions = await response.json();
        this.connectedClients = sessions.sessions;
      } else {
        log.error('Unable to get available shows');
      }
      this.clientTimeout = setTimeout(this.getConnectedClients, 1000);
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
          const settings = await response.json();
          await this.getAvailableShows();
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
    async getVersionStatus() {
      try {
        const response = await fetch(`${makeURL('/api/v1/version/status')}`);
        if (response.ok) {
          this.versionStatus = await response.json();
        } else {
          log.error('Unable to get version status');
        }
      } catch (error) {
        log.error('Error fetching version status:', error);
      }
    },
    async checkForUpdates() {
      if (this.isCheckingVersion) {
        return;
      }

      this.isCheckingVersion = true;

      try {
        const response = await fetch(`${makeURL('/api/v1/version/check')}`, {
          method: 'POST',
        });
        if (response.ok) {
          this.versionStatus = await response.json();
          if (this.versionStatus.update_available) {
            this.$toast.info(`Update available: ${this.versionStatus.latest_version}`);
          } else if (!this.versionStatus.check_error) {
            this.$toast.success('You are running the latest version');
          }
        } else {
          this.$toast.error('Unable to check for updates');
          log.error('Unable to check for updates');
        }
      } catch (error) {
        this.$toast.error('Unable to check for updates');
        log.error('Error checking for updates:', error);
      } finally {
        this.isCheckingVersion = false;
      }
    },
    getVersionStatusVariant() {
      if (!this.versionStatus.current_version) {
        return 'secondary';
      }
      if (this.versionStatus.check_error) {
        return 'danger';
      }
      if (this.versionStatus.update_available) {
        return 'warning';
      }
      return 'success';
    },
    getVersionStatusText() {
      if (!this.versionStatus.current_version) {
        return 'Loading...';
      }
      if (this.versionStatus.check_error) {
        return 'Unable to check';
      }
      if (this.versionStatus.update_available) {
        return 'Update Available';
      }
      return 'Up to date';
    },
    formatTimeAgo(isoTimestamp) {
      if (!isoTimestamp) {
        return 'Never';
      }

      const timestamp = new Date(isoTimestamp).getTime();
      const seconds = Math.floor((this.currentTime - timestamp) / 1000);

      if (seconds < 10) {
        return 'Just now';
      }
      if (seconds < 60) {
        return `${seconds} seconds ago`;
      }
      if (seconds < 3600) {
        return `${Math.floor(seconds / 60)} minutes ago`;
      }
      if (seconds < 86400) {
        return `${Math.floor(seconds / 3600)} hours ago`;
      }
      return `${Math.floor(seconds / 86400)} days ago`;
    },
    ...mapMutations(['UPDATE_SHOWS']),
    ...mapActions(['GET_SCRIPT_MODES']),
  },
};
</script>
