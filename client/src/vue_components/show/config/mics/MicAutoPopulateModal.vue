<template>
  <b-modal
    id="mic-auto-populate-modal"
    ref="mic-auto-populate-modal"
    size="xl"
    title="Auto-Populate Microphones"
    @show="resetForm"
    @hidden="resetForm"
  >
    <div>
      <b-alert
        variant="info"
        show
      >
        This will attempt to allocate microphones to characters based on priority given to
        those characters with the most lines, whilst attempting to minimise the number of
        swaps needed to be made during the show.
      </b-alert>
      <b-form>
        <b-form-group
          id="mic-exclusion-group"
          label="Excluded Microphones"
          label-for="mic-exclusion-input"
        >
          <multi-select
            id="mic-exclusion-input"
            v-model="excludedMics"
            name="mic-exclusion-input"
            :multiple="true"
            :options="MICROPHONES"
            track-by="id"
            label="name"
            :state="validateState('excludedMics')"
            @input="newSelectChanged"
          />
        </b-form-group>
      </b-form>
    </div>
    <template #modal-footer>
      <b-button
        variant="secondary"
        :disabled="submitting"
        @click.stop="$bvModal.hide('mic-auto-populate-modal')"
      >
        Cancel
      </b-button>
      <b-button
        variant="primary"
        :disabled="submitting"
        @click="performGeneration"
      >
        <b-spinner
          v-if="submitting"
          variant="info"
          style="width: auto; height: inherit;"
        />
        <template v-else>
          Confirm
        </template>
      </b-button>
    </template>
  </b-modal>
</template>

<script>
import { makeURL } from '@/js/utils';
import { mapGetters } from 'vuex';
import log from 'loglevel';

export default {
  name: 'MicAutoPopulateModal',
  events: ['autoPopulateResult'],
  data() {
    return {
      submitting: false,
      excludedMics: [],
      formState: {
        excludedMics: [],
      },
    };
  },
  validations: {
    formState: {
      excludedMics: {},
    },
  },
  computed: {
    ...mapGetters(['MICROPHONES']),
  },
  methods: {
    async performGeneration() {
      this.submitting = true;
      const response = await fetch(`${makeURL('/api/v1/show/microphones/suggest')}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          excluded_mics: this.formState.excludedMics,
        }),
      });
      if (response.ok) {
        const data = await response.json();
        this.$emit('autoPopulateResult', data);
      } else {
        log.error('Unable to auto populate microphones');
        this.$toast.error('Unable to auto populate microphones');
      }
      this.submitting = false;
    },
    validateState(name) {
      const { $dirty, $error } = this.$v.formState[name];
      return $dirty ? !$error : null;
    },
    newSelectChanged(value, id) {
      this.$v.formState.excludedMics.$model = value.map((mic) => (mic.id));
    },
    resetForm() {
      this.excludedMics = [];
      this.formState = {
        excludedMics: [],
      };
      this.$nextTick(() => {
        this.$v.$reset();
      });
    },
  },
};
</script>

<style scoped>

</style>
