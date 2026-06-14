<template>
  <BModal
    ref="modal"
    title="Jump to Cue"
    :no-header-close="searching || showResults"
    :no-close-on-backdrop="searching || showResults"
    :no-close-on-esc="searching || showResults"
    :ok-disabled="v$.cueSearchForm.$invalid"
    :ok-title="showResults ? undefined : 'Search'"
    :no-footer="showResults"
    @ok.prevent="performCueSearch"
    @hidden="resetCueSearch"
  >
    <div v-if="searching" class="text-center">
      <BSpinner variant="primary" />
      <p class="mt-2">Searching for cue...</p>
    </div>

    <template v-else-if="showResults">
      <template v-if="multipleMatches">
        <p>Multiple matches found — select one:</p>
        <BListGroup>
          <BListGroupItem
            v-for="match in cueSearchResults.exact_matches"
            :key="match.cue.id"
            button
            @click="navigateToMatch(match)"
          >
            {{ match.cue_type.prefix }} {{ match.cue.ident }} — Page {{ match.location.page }}
          </BListGroupItem>
        </BListGroup>
      </template>
      <template v-else-if="showSuggestions">
        <BAlert variant="warning" :model-value="true">
          No exact match found. Did you mean one of these?
        </BAlert>
        <BListGroup>
          <BListGroupItem
            v-for="suggestion in cueSearchResults.suggestions"
            :key="suggestion.cue.id"
            button
            @click="navigateToMatch(suggestion)"
          >
            {{ suggestion.cue_type.prefix }} {{ suggestion.cue.ident }} — Page
            {{ suggestion.location.page }}
            <BBadge variant="info" class="ms-2">
              {{ Math.round(suggestion.similarity_score * 100) }}% match
            </BBadge>
          </BListGroupItem>
        </BListGroup>
      </template>
      <BAlert v-else-if="noMatches" variant="danger" :model-value="true">
        No cues found matching "{{ lastSearchIdent }}".
      </BAlert>
      <div class="mt-3 d-flex gap-2">
        <BButton variant="secondary" @click="resetCueSearch">New Search</BButton>
        <BButton variant="outline-secondary" @click="modal?.hide()">Cancel</BButton>
      </div>
    </template>

    <template v-else>
      <BForm @submit.stop.prevent="performCueSearch">
        <BFormGroup label="Cue Type" label-for="jump-cue-type">
          <BFormSelect
            id="jump-cue-type"
            v-model="v$.cueSearchForm.cueTypeId.$model"
            :options="cueTypeOptions"
            :state="fieldState('cueTypeId')"
          />
          <BFormInvalidFeedback>Please select a cue type.</BFormInvalidFeedback>
        </BFormGroup>
        <BFormGroup label="Identifier" label-for="jump-cue-ident">
          <BFormInput
            id="jump-cue-ident"
            v-model="v$.cueSearchForm.identifier.$model"
            placeholder="e.g., 1, 42, 1.5"
            :state="fieldState('identifier')"
          />
          <BFormInvalidFeedback>This is a required field.</BFormInvalidFeedback>
        </BFormGroup>
        <BAlert v-if="generalError" variant="danger" :model-value="true">
          {{ generalError }}
        </BAlert>
      </BForm>
    </template>
  </BModal>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import type { BModal } from 'bootstrap-vue-next';
import { useVuelidate } from '@vuelidate/core';
import { required } from '@vuelidate/validators';
import { notNull } from '@/js/customValidators';
import { toast } from '@/js/toast';
import { useScriptStore } from '@/stores/script';
import { useShowStore } from '@/stores/show';

interface CueMatch {
  cue: { id: number; ident: string; cue_type_id: number };
  cue_type: { id: number; prefix: string; description: string | null };
  location: { page: number };
  similarity_score?: number;
}

interface SearchResult {
  exact_matches: CueMatch[];
  suggestions: CueMatch[];
}

const emit = defineEmits<{ navigate: [page: number] }>();

const scriptStore = useScriptStore();
const showStore = useShowStore();

const modal = ref<InstanceType<typeof BModal> | null>(null);

const cueSearchForm = ref({ cueTypeId: null as number | null, identifier: '' });
const rules = {
  cueSearchForm: {
    cueTypeId: { required, notNull },
    identifier: { required },
  },
};
const v$ = useVuelidate(rules, { cueSearchForm });

const cueSearchResults = ref<SearchResult | null>(null);
const generalError = ref<string | null>(null);
const searching = ref(false);
const showResults = ref(false);
const lastSearchIdent = ref('');

const cueTypeOptions = computed(() => [
  { value: null, text: 'Select a cue type...', disabled: true },
  ...showStore.cueTypes.map((t) => ({
    value: t.id,
    text: `${t.prefix} - ${t.description ?? 'No description'}`,
  })),
]);

const multipleMatches = computed(() => (cueSearchResults.value?.exact_matches.length ?? 0) > 1);
const showSuggestions = computed(
  () =>
    (cueSearchResults.value?.exact_matches.length ?? 0) === 0 &&
    (cueSearchResults.value?.suggestions.length ?? 0) > 0
);
const noMatches = computed(
  () =>
    (cueSearchResults.value?.exact_matches.length ?? 0) === 0 &&
    (cueSearchResults.value?.suggestions.length ?? 0) === 0
);

function fieldState(field: 'cueTypeId' | 'identifier'): boolean | null {
  const f = v$.value.cueSearchForm[field];
  return f.$dirty ? !f.$error : null;
}

async function performCueSearch(): Promise<void> {
  const valid = await v$.value.$validate();
  if (!valid) return;
  searching.value = true;
  generalError.value = null;
  lastSearchIdent.value = cueSearchForm.value.identifier;
  try {
    const result = (await scriptStore.searchCues({
      identifier: cueSearchForm.value.identifier,
      cueTypeId: cueSearchForm.value.cueTypeId!,
    })) as unknown as SearchResult;
    cueSearchResults.value = result;
    if (result.exact_matches.length === 1) {
      navigateToMatch(result.exact_matches[0]);
    } else {
      showResults.value = true;
    }
  } catch {
    generalError.value = 'Search failed. Please try again.';
  } finally {
    searching.value = false;
  }
}

function navigateToMatch(match: CueMatch): void {
  emit('navigate', match.location.page);
  toast.success(
    `Jumped to ${match.cue_type.prefix} ${match.cue.ident} on page ${match.location.page}`
  );
  modal.value?.hide();
}

function resetCueSearch(): void {
  cueSearchForm.value = { cueTypeId: null, identifier: '' };
  cueSearchResults.value = null;
  generalError.value = null;
  searching.value = false;
  showResults.value = false;
  v$.value.$reset();
}

function show(): void {
  modal.value?.show();
}

defineExpose({ show });
</script>
