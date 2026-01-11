<template>
  <b-modal
    id="jump-to-cue"
    ref="jump-to-cue"
    title="Jump to Cue"
    size="md"
    :hide-header-close="searching || showResults"
    :hide-footer="searching"
    :no-close-on-backdrop="searching"
    :no-close-on-esc="searching"
    @ok="performCueSearch"
    @hidden="resetCueSearch"
  >
    <!-- Search Form -->
    <b-form v-if="!showResults" v-show="!searching" @submit.stop.prevent="performCueSearch">
      <b-form-group
        label="Cue Type"
        label-for="cue-type-input"
        :invalid-feedback="cueTypeError"
        :state="cueTypeErrorState"
      >
        <b-form-select
          id="cue-type-input"
          v-model="$v.cueSearchForm.cueTypeId.$model"
          :options="cueTypeOptions"
          :state="cueTypeErrorState"
          :disabled="searching"
        />
      </b-form-group>

      <b-form-group
        label="Identifier"
        label-for="identifier-input"
        :invalid-feedback="identifierError"
        :state="identifierErrorState"
      >
        <b-form-input
          id="identifier-input"
          v-model="$v.cueSearchForm.identifier.$model"
          placeholder="e.g., 1, 42, 1.5"
          :state="identifierErrorState"
          :disabled="searching"
        />
      </b-form-group>

      <!-- General Error Message -->
      <b-alert v-if="generalError" variant="danger" show>
        {{ generalError }}
      </b-alert>
    </b-form>

    <!-- Loading Spinner -->
    <div v-if="searching" class="text-center">
      <b-spinner variant="primary" label="Searching..." />
      <p class="mt-2">Searching for cue...</p>
    </div>

    <!-- Multiple Matches - Selection List -->
    <div v-else-if="multipleMatches">
      <p>
        Found {{ cueSearchResults.exact_matches.length }} cues matching "{{
          cueSearchForm.identifier
        }}":
      </p>
      <b-list-group>
        <b-list-group-item
          v-for="(match, idx) in cueSearchResults.exact_matches"
          :key="idx"
          button
          @click="navigateToMatch(match)"
        >
          <strong>{{ match.cue_type.prefix }} {{ match.cue.ident }}</strong>
          - Page {{ match.location.page }}
        </b-list-group-item>
      </b-list-group>
    </div>

    <!-- Suggestions (No Exact Match) -->
    <div v-else-if="showSuggestions">
      <b-alert variant="warning" show>
        No exact match found for "{{ cueSearchForm.identifier }}"
      </b-alert>
      <p>Did you mean one of these?</p>
      <b-list-group>
        <b-list-group-item
          v-for="(suggestion, idx) in cueSearchResults.suggestions"
          :key="idx"
          button
          @click="navigateToMatch(suggestion)"
        >
          <strong>{{ suggestion.cue_type.prefix }} {{ suggestion.cue.ident }}</strong>
          - Page {{ suggestion.location.page }}
          <b-badge variant="secondary" class="float-right">
            {{ Math.round(suggestion.similarity_score * 100) }}% match
          </b-badge>
        </b-list-group-item>
      </b-list-group>
    </div>

    <!-- No Matches At All -->
    <div v-else-if="noMatches">
      <b-alert variant="danger" show>
        No cues found matching "{{ cueSearchForm.identifier }}" for the selected cue type.
      </b-alert>
    </div>

    <!-- Footer for results -->
    <template v-if="showResults" #modal-footer>
      <b-button variant="secondary" @click="resetCueSearch"> New Search </b-button>
      <b-button variant="primary" @click="$bvModal.hide('jump-to-cue')"> Cancel </b-button>
    </template>
  </b-modal>
</template>

<script>
import { required } from 'vuelidate/lib/validators';
import { mapActions, mapGetters } from 'vuex';
import log from 'loglevel';
import Vue from 'vue';
import { notNull } from '@/js/customValidators';

export default {
  name: 'JumpToCueModal',
  data() {
    return {
      cueSearchForm: {
        cueTypeId: null,
        identifier: '',
      },
      cueSearchResults: null,
      generalError: null,
      searching: false,
      showResults: false,
    };
  },
  validations: {
    cueSearchForm: {
      cueTypeId: {
        required,
        notNull,
      },
      identifier: {
        required,
      },
    },
  },
  computed: {
    ...mapGetters(['CUE_TYPES']),
    cueTypeOptions() {
      const options = [{ value: null, text: 'Select a cue type...', disabled: true }];
      this.CUE_TYPES.forEach((type) => {
        options.push({
          value: type.id,
          text: `${type.prefix} - ${type.description || 'No description'}`,
        });
      });
      return options;
    },
    multipleMatches() {
      return this.cueSearchResults?.exact_matches?.length > 1;
    },
    showSuggestions() {
      return (
        this.cueSearchResults?.exact_matches?.length === 0 &&
        this.cueSearchResults?.suggestions?.length > 0
      );
    },
    noMatches() {
      return (
        this.cueSearchResults?.exact_matches?.length === 0 &&
        this.cueSearchResults?.suggestions?.length === 0
      );
    },
    cueTypeErrorState() {
      const { $dirty, $error } = this.$v.cueSearchForm.cueTypeId;
      return $dirty ? !$error : null;
    },
    cueTypeError() {
      if (this.$v.cueSearchForm.cueTypeId.$dirty) {
        if (!this.$v.cueSearchForm.cueTypeId.required || !this.$v.cueSearchForm.cueTypeId.notNull) {
          return 'Cue type is required';
        }
      }
      return '';
    },
    identifierErrorState() {
      const { $dirty, $error } = this.$v.cueSearchForm.identifier;
      return $dirty ? !$error : null;
    },
    identifierError() {
      if (this.$v.cueSearchForm.identifier.$dirty && !this.$v.cueSearchForm.identifier.required) {
        return 'Identifier is required';
      }
      return '';
    },
  },
  methods: {
    ...mapActions(['SEARCH_CUES']),
    async performCueSearch(event) {
      if (event) {
        event.preventDefault();
      }
      this.$v.$touch();
      if (this.$v.$anyError) {
        return;
      }

      this.searching = true;
      this.generalError = null;
      try {
        const result = await this.SEARCH_CUES({
          identifier: this.cueSearchForm.identifier.trim(),
          cueTypeId: this.cueSearchForm.cueTypeId,
        });
        this.cueSearchResults = result;

        if (result.exact_matches?.length === 1) {
          await this.navigateToMatch(result.exact_matches[0]);
          this.$bvModal.hide('jump-to-cue');
        } else {
          this.showResults = true;
        }
      } catch (error) {
        this.generalError = 'Search failed. Please try again.';
        log.error('Cue search error:', error);
      } finally {
        this.searching = false;
      }
    },
    async navigateToMatch(match) {
      const targetPage = match.location.page;
      this.$emit('navigate', targetPage);
      Vue.$toast.success(
        `Jumped to ${match.cue_type.prefix} ${match.cue.ident} on page ${targetPage}`
      );
    },
    resetCueSearch() {
      this.cueSearchForm.identifier = '';
      this.cueSearchForm.cueTypeId = null;
      this.cueSearchResults = null;
      this.generalError = null;
      this.showResults = false;
      this.$v.$reset();
    },
  },
};
</script>
