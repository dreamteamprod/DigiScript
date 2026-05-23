<template>
  <BCol>
    <BRow v-if="lineType === LINE_TYPES.DIALOGUE || lineType === LINE_TYPES.STAGE_DIRECTION">
      <template v-if="userSettings.character_combined_dropdown">
        <BCol>
          <BFormGroup label-size="sm" label="Character / Character Group">
            <BFormSelect
              v-model="combinedValue"
              :options="combinedOptions"
              :state="combinedState"
              @update:model-value="onStateChange"
            />
          </BFormGroup>
        </BCol>
      </template>
      <template v-else>
        <BCol v-show="state.character_group_id == null">
          <BFormGroup label-size="sm" label="Character">
            <BFormSelect
              v-model="state.character_id"
              :options="characterOptions"
              :state="characterState"
              @update:model-value="onStateChange"
            />
          </BFormGroup>
        </BCol>
        <BCol v-show="state.character_id == null">
          <BFormGroup label-size="sm" label="Character Group">
            <BFormSelect
              v-model="state.character_group_id"
              :options="characterGroupOptions"
              :state="characterGroupState"
              @update:model-value="onStateChange"
            />
          </BFormGroup>
        </BCol>
      </template>
      <BCol
        v-if="lineType === LINE_TYPES.STAGE_DIRECTION && stageDirectionStyles.length > 0"
        cols="3"
      >
        <BFormGroup label-size="sm" label="Style">
          <BFormSelect
            :model-value="stageDirectionStyleId"
            :options="stageDirectionStyleOptions"
            @update:model-value="$emit('stage-direction-style-change', $event)"
          />
        </BFormGroup>
      </BCol>
    </BRow>
    <BRow>
      <BCol style="display: inline-flex">
        <BFormInput
          ref="partInputRef"
          v-model="state.line_text"
          :state="lineTextState"
          @update:model-value="onStateChange"
          @keydown.enter="handleEnterPress"
        />
        <BButton
          v-if="showAddButton && lineType === LINE_TYPES.DIALOGUE"
          v-b-tooltip.hover.top="'Add line part'"
          :disabled="!enableAddButton"
          style="margin-left: 0.5em; float: right"
          @click="$emit('add-line-part')"
        >
          <IMdiPlusBox />
        </BButton>
      </BCol>
    </BRow>
  </BCol>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, nextTick } from 'vue';
import { useVuelidate } from '@vuelidate/core';
import { required } from '@vuelidate/validators';
import { LINE_TYPES } from '@/constants/lineTypes';
import { useShowStore } from '@/stores/show';
import { useScriptConfigStore } from '@/stores/scriptConfig';
import { useUserStore } from '@/stores/user';
import {
  buildMruCharacterOptions,
  buildMruCharacterGroupOptions,
  buildCombinedCharacterOptions,
  type CombinedSelectOption,
} from '@/js/mruSortUtils';
import type { ScriptLinePart } from '@/types/api/script';
import type { Character, CharacterGroup } from '@/types/api/show';
import type { StageDirectionStyle } from '@/types/api/script';

const props = defineProps<{
  focusInput: boolean;
  characters: Character[];
  characterGroups: CharacterGroup[];
  showAddButton: boolean;
  enableAddButton: boolean;
  lineType: number;
  lineParts: ScriptLinePart[];
  stageDirectionStyles?: StageDirectionStyle[];
  stageDirectionStyleId?: number | null;
  modelValue: ScriptLinePart;
}>();

const emit = defineEmits<{
  'update:modelValue': [part: ScriptLinePart];
  'add-line-part': [];
  'try-finish-line': [];
  'stage-direction-style-change': [id: number | null];
}>();

const showStore = useShowStore();
const scriptConfigStore = useScriptConfigStore();
const userStore = useUserStore();

const partInputRef = ref<HTMLInputElement | null>(null);

const state = ref<ScriptLinePart>({ ...props.modelValue });

const userSettings = computed(
  () =>
    userStore.userSettings as {
      character_mru_sort?: boolean;
      character_combined_dropdown?: boolean;
    }
);

const tmpScript = computed(() => scriptConfigStore.tmpScript);

const characterOptions = computed(() => {
  if (userSettings.value.character_mru_sort) {
    const sorted = buildMruCharacterOptions(props.characters, tmpScript.value);
    if (sorted) return sorted;
  }
  return [
    { value: null, text: 'N/A' },
    ...props.characters.map((c) => ({ value: c.id, text: c.name })),
  ];
});

const characterGroupOptions = computed(() => {
  if (userSettings.value.character_mru_sort) {
    const sorted = buildMruCharacterGroupOptions(props.characterGroups, tmpScript.value);
    if (sorted) return sorted;
  }
  return [
    { value: null, text: 'N/A' },
    ...props.characterGroups.map((g) => ({ value: g.id, text: g.name })),
  ];
});

const stageDirectionStyleOptions = computed<{ value: number | null; text: string }[]>(() => [
  { value: null, text: 'N/A' },
  ...(props.stageDirectionStyles ?? []).map((s) => ({ value: s.id, text: s.description })),
]);

const combinedOptions = computed<CombinedSelectOption[]>(() =>
  buildCombinedCharacterOptions(
    props.characters,
    props.characterGroups,
    tmpScript.value,
    !!userSettings.value.character_mru_sort
  )
);

const combinedValue = computed<string | null>({
  get() {
    if (state.value.character_id != null) return `c:${state.value.character_id}`;
    if (state.value.character_group_id != null) return `g:${state.value.character_group_id}`;
    return null;
  },
  set(val: string | null) {
    if (val == null) {
      state.value.character_id = null;
      state.value.character_group_id = null;
    } else if (val.startsWith('c:')) {
      state.value.character_id = Number.parseInt(val.slice(2), 10);
      state.value.character_group_id = null;
    } else if (val.startsWith('g:')) {
      state.value.character_id = null;
      state.value.character_group_id = Number.parseInt(val.slice(2), 10);
    }
    v$.value.$touch();
  },
});

const isCharacterRequired = computed(
  () => props.lineType === LINE_TYPES.DIALOGUE && state.value.character_group_id == null
);
const isCharacterGroupRequired = computed(
  () => props.lineType === LINE_TYPES.DIALOGUE && state.value.character_id == null
);
const isLineTextRequired = computed(
  () => props.lineParts.length <= 1 || !props.lineParts.some((x) => x.line_text !== '')
);

const rules = computed(() => ({
  character_id: isCharacterRequired.value ? { required } : {},
  character_group_id: isCharacterGroupRequired.value ? { required } : {},
  line_text: isLineTextRequired.value ? { required } : {},
}));

const v$ = useVuelidate(rules, state);

const characterState = computed<boolean | null>(() => {
  const f = v$.value.character_id;
  return f.$dirty ? !f.$error : null;
});

const characterGroupState = computed<boolean | null>(() => {
  const f = v$.value.character_group_id;
  return f.$dirty ? !f.$error : null;
});

const lineTextState = computed<boolean | null>(() => {
  const f = v$.value.line_text;
  return f.$dirty ? !f.$error : null;
});

const combinedState = computed<boolean | null>(() => {
  const cF = v$.value.character_id;
  const gF = v$.value.character_group_id;
  if (!cF.$dirty && !gF.$dirty) return null;
  return !(cF.$error && gF.$error);
});

function onStateChange(): void {
  v$.value.$touch();
  emit('update:modelValue', { ...state.value });
  nextTick(() => partInputRef.value?.focus());
}

function handleEnterPress(): void {
  v$.value.$touch();
  emit('try-finish-line');
}

onMounted(() => {
  v$.value.$touch();
  if (props.focusInput) {
    requestAnimationFrame(() => {
      nextTick(() => partInputRef.value?.focus());
    });
  }
});

watch(
  () => props.modelValue,
  (val) => {
    state.value = { ...val };
  },
  { deep: true }
);
</script>
