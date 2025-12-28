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
          <b-alert
            variant="secondary"
            show
          >
            Excluded microphones will not be assigned to any characters during auto-population.
          </b-alert>
          <multi-select
            id="mic-exclusion-input"
            v-model="excludedMics"
            name="mic-exclusion-input"
            :multiple="true"
            :options="MICROPHONES"
            track-by="id"
            label="name"
            :state="validateState('excludedMics')"
            @input="newExcludedMicSelectChanged"
          />
        </b-form-group>
        <b-form-group
          id="static-characters-group"
          label="Static Allocations"
          label-for="static-characters-input"
        >
          <b-alert
            variant="secondary"
            show
          >
            Assign a static microphone to these characters; they will have the same mic for all scenes in the show.
          </b-alert>
          <multi-select
            id="static-characters-input"
            v-model="staticCharacters"
            name="static-characters-input"
            :multiple="true"
            :options="CHARACTER_LIST"
            track-by="id"
            label="name"
            :state="validateState('staticCharacters')"
            @input="newStaticCharacterSelectChanged"
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
      staticCharacters: [],
      formState: {
        excludedMics: [],
        staticCharacters: [],
      },
    };
  },
  validations: {
    formState: {
      excludedMics: {},
      staticCharacters: {},
    },
  },
  computed: {
    ...mapGetters(['MICROPHONES', 'CHARACTER_LIST']),
  },
  methods: {
    async performGeneration() {
      this.submitting = true;
      const response = await fetch(`${makeURL('/api/v1/show/microphones/suggest')}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          excluded_mics: this.formState.excludedMics,
          static_characters: this.formState.staticCharacters,
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
    newExcludedMicSelectChanged(value, id) {
      this.$v.formState.excludedMics.$model = value.map((mic) => (mic.id));
    },
    newStaticCharacterSelectChanged(value, id) {
      this.$v.formState.staticCharacters.$model = value.map((char) => (char.id));
    },
    resetForm() {
      this.excludedMics = [];
      this.staticCharacters = [];
      this.formState = {
        excludedMics: [],
        staticCharacters: [],
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
