<template>
  <BModal
    ref="modalRef"
    size="xl"
    title="Auto-Populate Microphones"
    no-footer
    @show="resetState"
    @hidden="resetState"
  >
    <template v-if="modalMode === 'create'">
      <BAlert :model-value="true" variant="info">
        This will attempt to allocate microphones to characters based on priority given to those
        characters with the most lines, whilst attempting to minimise the number of swaps needed to
        be made during the show.
      </BAlert>
      <BForm>
        <BFormGroup label="Excluded Microphones">
          <BAlert :model-value="true" variant="secondary">
            Excluded microphones will not be assigned to any characters during auto-population.
          </BAlert>
          <VueMultiselect
            v-model="excludedMics"
            :multiple="true"
            :options="showStore.microphones"
            track-by="id"
            label="name"
          />
        </BFormGroup>
        <BFormGroup label="Static Allocations" class="mt-3">
          <BAlert :model-value="true" variant="secondary">
            Assign a static microphone to these characters; they will have the same mic for all
            scenes in the show.
          </BAlert>
          <VueMultiselect
            v-model="staticCharacters"
            :multiple="true"
            :options="showStore.characterList"
            track-by="id"
            label="name"
          />
        </BFormGroup>
        <BFormGroup label="Single Allocation Gap Mode" class="mt-3">
          <BAlert :model-value="true" variant="secondary">
            <p>
              Change allocation behaviour for microphones which are only ever assigned to a single
              character during the whole show.
            </p>
            <p class="mb-0">
              <b>Leave Gaps</b> (default) — only allocate microphones for the scenes the character
              has lines in. <b>No Gaps</b> — allocate the microphone for all scenes.
            </p>
          </BAlert>
          <BFormSelect v-model="gapMode">
            <BFormSelectOption value="leave_gaps">Leave Gaps</BFormSelectOption>
            <BFormSelectOption value="no_gaps">No Gaps</BFormSelectOption>
          </BFormSelect>
        </BFormGroup>
      </BForm>
    </template>

    <template v-else-if="modalMode === 'review'">
      <BAlert :model-value="true" variant="success">
        Microphone allocations have been successfully generated. Check for info or warnings below.
      </BAlert>
      <BTabs content-class="mt-3">
        <BTab title="Allocations" active>
          <BAlert v-if="allocationHints.length === 0" :model-value="true" variant="info">
            No warnings or info for microphone allocations.
          </BAlert>
          <div v-else style="overflow-y: scroll; max-height: 50vh">
            <BAlert
              v-for="(hint, index) in allocationHints"
              :key="`allocation-hint-${index}`"
              :model-value="true"
              variant="warning"
            >
              <p><b>Character:</b> {{ showStore.characterById(hint.character_id)?.name }}</p>
              <p><b>Message:</b> {{ hint.reason }}</p>
              <p v-if="hint.scene_id != null">
                <b>Scene:</b>
                {{ sceneLabel(hint.scene_id) }}
              </p>
            </BAlert>
          </div>
        </BTab>
        <BTab title="Static Allocations">
          <BAlert v-if="staticAllocationHints.length === 0" :model-value="true" variant="info">
            No warnings or info for static microphone allocations.
          </BAlert>
          <div v-else style="overflow-y: scroll; max-height: 50vh">
            <BAlert
              v-for="(hint, index) in staticAllocationHints"
              :key="`static-hint-${index}`"
              :model-value="true"
              variant="warning"
            >
              <p><b>Character:</b> {{ showStore.characterById(hint.character_id)?.name }}</p>
              <p><b>Message:</b> {{ hint.reason }}</p>
            </BAlert>
          </div>
        </BTab>
        <BTab v-if="gapMode === 'no_gaps'" title="Gap Fill">
          <BAlert v-if="gapFillHints.length === 0" :model-value="true" variant="success">
            No warnings or info for gap fill microphone allocations.
          </BAlert>
          <div v-else style="overflow-y: scroll; max-height: 50vh">
            <BAlert
              v-for="(hint, index) in gapFillHints"
              :key="`gap-fill-hint-${index}`"
              :model-value="true"
              variant="info"
            >
              <p><b>Character:</b> {{ showStore.characterById(hint.character_id)?.name }}</p>
              <p><b>Message:</b> {{ hint.reason }}</p>
            </BAlert>
          </div>
        </BTab>
      </BTabs>
    </template>

    <template v-else>
      <BAlert :model-value="true" variant="danger">
        Error occurred while generating mic allocations. Please try again.
      </BAlert>
    </template>

    <div class="d-flex justify-content-end gap-2 mt-3">
      <BButton variant="secondary" :disabled="submitting" @click="modalRef?.hide()">
        Cancel
      </BButton>
      <BButton v-if="modalMode === 'error'" variant="warning" @click="modalMode = 'create'">
        Try Again
      </BButton>
      <BButton
        v-else-if="modalMode === 'create'"
        variant="primary"
        :disabled="submitting"
        @click="performGeneration"
      >
        <BSpinner v-if="submitting" small />
        <template v-else>Generate</template>
      </BButton>
      <BButton v-else-if="modalMode === 'review'" variant="success" @click="applyChanges">
        Apply Changes
      </BButton>
    </div>
  </BModal>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import type { BModal } from 'bootstrap-vue-next';
import VueMultiselect from 'vue-multiselect';
import 'vue-multiselect/dist/vue-multiselect.css';
import log from 'loglevel';
import { toast } from '@/js/toast';
import { makeURL } from '@/js/utils';
import { useShowStore } from '@/stores/show';
import type { Microphone } from '@/types/api/microphones';
import type { Character } from '@/types/api/show';

interface SuggestionHint {
  type: 'allocation' | 'static' | 'gap_fill';
  character_id: number;
  reason: string;
  scene_id?: number;
  scenes?: number[];
}

const emit = defineEmits<{ autoPopulateResult: [allocations: Record<string, unknown>] }>();

const showStore = useShowStore();

const modalRef = ref<InstanceType<typeof BModal>>();
const modalMode = ref<'create' | 'review' | 'error'>('create');
const submitting = ref(false);

const excludedMics = ref<Microphone[]>([]);
const staticCharacters = ref<Character[]>([]);
const gapMode = ref<'leave_gaps' | 'no_gaps'>('leave_gaps');
const suggestionHints = ref<SuggestionHint[]>([]);
const allocations = ref<Record<string, unknown>>({});

const allocationHints = computed(() =>
  suggestionHints.value.filter((h) => h.type === 'allocation')
);
const staticAllocationHints = computed(() =>
  suggestionHints.value.filter((h) => h.type === 'static')
);
const gapFillHints = computed(() => suggestionHints.value.filter((h) => h.type === 'gap_fill'));

function sceneLabel(sceneId: number): string {
  const scene = showStore.sceneById(sceneId);
  if (!scene) return String(sceneId);
  const act = showStore.actById(scene.act);
  return act ? `${act.name}: ${scene.name}` : (scene.name ?? String(sceneId));
}

function resetState(): void {
  modalMode.value = 'create';
  excludedMics.value = [];
  staticCharacters.value = [];
  gapMode.value = 'leave_gaps';
  suggestionHints.value = [];
  allocations.value = {};
  submitting.value = false;
}

async function performGeneration(): Promise<void> {
  submitting.value = true;
  try {
    const response = await fetch(makeURL('/api/v1/show/microphones/suggest'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        excluded_mics: excludedMics.value.map((m) => m.id),
        static_characters: staticCharacters.value.map((c) => c.id),
        gap_mode: gapMode.value,
      }),
    });
    if (response.ok) {
      const data = await response.json();
      suggestionHints.value = data.hints ?? [];
      allocations.value = data.allocations ?? {};
      modalMode.value = 'review';
    } else {
      log.error('Unable to auto-populate microphones');
      toast.error('Unable to auto-populate microphones');
      modalMode.value = 'error';
    }
  } catch (e) {
    log.error('Error during microphone auto-population:', e);
    toast.error('Error during microphone auto-population');
    modalMode.value = 'error';
  } finally {
    submitting.value = false;
  }
}

function applyChanges(): void {
  emit('autoPopulateResult', allocations.value);
  modalRef.value?.hide();
}

defineExpose({ show: () => modalRef.value?.show() });
</script>
