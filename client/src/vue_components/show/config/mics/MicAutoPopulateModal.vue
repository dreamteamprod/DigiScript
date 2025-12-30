<template>
  <b-modal
    id="mic-auto-populate-modal"
    ref="mic-auto-populate-modal"
    size="xl"
    title="Auto-Populate Microphones"
    @show="resetState"
    @hidden="resetState"
  >
    <template v-if="modalMode === 'create'">
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
      <hr>
      <div>
        <b-button v-b-toggle.advanced-options-collapse>
          <b-icon icon="gear-wide-connected" /> Advanced Options
        </b-button>
        <b-collapse
          id="advanced-options-collapse"
          style="margin-top: 0.5rem;"
        >
          <b-card>
            <b-form-group
              id="allocation-gap-group"
              label="Single Allocation Gap Mode"
              label-for="allocation-gap-input"
            >
              <b-alert
                variant="secondary"
                show
              >
                <p>
                  Change allocation behaviour for microphones which are only ever assigned to a
                  single character during the whole show.
                </p>
                <p>
                  Two modes of operations: <b>Leave Gaps</b> (default) - only allocate microphones
                  for the scenes the character has lines in. <b>No Gaps</b> - allocate the
                  microphone to the character for all scenes.
                </p>
              </b-alert>
              <b-form-select v-model="formState.gapMode">
                <b-form-select-option value="leave_gaps">
                  Leave Gaps
                </b-form-select-option>
                <b-form-select-option value="no_gaps">
                  No Gaps
                </b-form-select-option>
              </b-form-select>
            </b-form-group>
          </b-card>
        </b-collapse>
      </div>
    </template>
    <template v-else-if="modalMode === 'review'">
      <div>
        <b-alert
          variant="success"
          show
        >
          Microphone allocations have been successfully generated. Check for info or warnings below.
        </b-alert>
        <b-tabs content-class="mt-3">
          <b-tab
            title="Allocations"
            active
          >
            <b-alert
              v-if="allocationHints.length === 0"
              variant="info"
              show
            >
              No warnings or info for microphone allocations.
            </b-alert>
            <div
              v-else
              style="overflow-y: scroll; max-height: 50vh;"
            >
              <b-alert
                v-for="(hint, index) in allocationHints"
                :key="`allocation-hint-${index}`"
                variant="warning"
                show
              >
                <p><b>Character: </b>{{ CHARACTER_BY_ID(hint.character_id).name }}</p>
                <p><b>Message: </b>{{ hint.reason }}</p>
                <p>
                  <b>Scene: </b>
                  {{ `${ACT_BY_ID(SCENE_BY_ID(hint.scene_id).act).name}: ${SCENE_BY_ID(hint.scene_id).name}` }}
                </p>
              </b-alert>
            </div>
          </b-tab>
          <b-tab title="Static Allocations">
            <b-alert
              v-if="staticAllocationHints.length === 0"
              variant="info"
              show
            >
              No warnings or info for static microphone allocations.
            </b-alert>
            <div
              v-else
              style="overflow-y: scroll; max-height: 50vh;"
            >
              <b-alert
                v-for="(hint, index) in staticAllocationHints"
                :key="`static-allocation-hint-${index}`"
                variant="warning"
                show
              >
                <p><b>Character: </b>{{ CHARACTER_BY_ID(hint.character_id).name }}</p>
                <p><b>Message: </b>{{ hint.reason }}</p>
              </b-alert>
            </div>
          </b-tab>
          <b-tab
            v-if="formState.gapMode === 'no_gaps'"
            title="Gap Fill"
          >
            <b-alert
              v-if="gapFillHints.length === 0"
              variant="success"
              show
            >
              No warnings or info for gap fill microphone allocations.
            </b-alert>
            <div
              v-else
              style="overflow-y: scroll; max-height: 50vh;"
            >
              <b-alert
                v-for="(hint, index) in gapFillHints"

                :key="`gap-fill-hint-${index}`"
                variant="info"
                show
              >
                <p><b>Character: </b>{{ CHARACTER_BY_ID(hint.character_id).name }}</p>
                <p><b>Message: </b>{{ hint.reason }}</p>
                <p>
                  <b>Scenes: </b>
                  {{ hint.scenes.map((scene) => (`${ACT_BY_ID(SCENE_BY_ID(scene).act).name}: ${SCENE_BY_ID(scene).name}`)).join(', ') }}
                </p>
              </b-alert>
            </div>
          </b-tab>
        </b-tabs>
      </div>
    </template>
    <template v-else>
      <b-alert
        variant="danger"
        show
      >
        Error occurred while generating mic allocations. Please try again.
      </b-alert>
    </template>
    <template #modal-footer>
      <b-button
        variant="secondary"
        :disabled="submitting"
        @click.stop="$bvModal.hide('mic-auto-populate-modal')"
      >
        Cancel
      </b-button>
      <b-button
        v-if="modalMode === 'create'"
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
          Generate
        </template>
      </b-button>
      <b-button
        v-else-if="modalMode === 'review'"
        variant="primary"
        @click="applyPendingChanges"
      >
        Apply Changes
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
      modalMode: 'create',
      submitting: false,
      excludedMics: [],
      staticCharacters: [],
      formState: {
        excludedMics: [],
        staticCharacters: [],
        gapMode: 'leave_gaps',
      },
      suggestionHints: [],
      allocations: {},
    };
  },
  validations: {
    formState: {
      excludedMics: {},
      staticCharacters: {},
      gapMode: {},
    },
  },
  computed: {
    allocationHints() {
      return this.suggestionHints.filter((hint) => hint.type === 'allocation');
    },
    staticAllocationHints() {
      return this.suggestionHints.filter((hint) => hint.type === 'static');
    },
    gapFillHints() {
      return this.suggestionHints.filter((hint) => hint.type === 'gap_fill');
    },
    ...mapGetters(['MICROPHONES', 'CHARACTER_LIST', 'CHARACTER_BY_ID', 'SCENE_BY_ID', 'ACT_BY_ID']),
  },
  methods: {
    async performGeneration() {
      this.submitting = true;
      try {
        const response = await fetch(`${makeURL('/api/v1/show/microphones/suggest')}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            excluded_mics: this.formState.excludedMics,
            static_characters: this.formState.staticCharacters,
            gap_mode: this.formState.gapMode,
          }),
        });
        if (response.ok) {
          const data = await response.json();
          this.suggestionHints = data.hints;
          this.allocations = data.allocations;
          this.modalMode = 'review';
        } else {
          log.error('Unable to auto populate microphones');
          this.$toast.error('Unable to auto populate microphones');
          this.modalMode = 'error';
        }
      } catch (error) {
        log.error('Error during microphone auto-population:', error);
        this.$toast.error('Error during microphone auto-population');
        this.modalMode = 'error';
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
    resetState() {
      this.modalMode = 'create';
      this.excludedMics = [];
      this.staticCharacters = [];
      this.formState = {
        excludedMics: [],
        staticCharacters: [],
        gapMode: 'leave_gaps',
      };
      this.suggestionHints = [];
      this.allocations = {};
      this.$nextTick(() => {
        this.$v.$reset();
      });
    },
    applyPendingChanges() {
      this.$emit('autoPopulateResult', this.allocations);
      this.$bvModal.hide('mic-auto-populate-modal');
    },
  },
};
</script>

<style scoped>

</style>
