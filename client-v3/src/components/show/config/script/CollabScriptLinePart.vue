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
              @update:model-value="v$.$touch()"
            />
          </BFormGroup>
        </BCol>
      </template>
      <template v-else>
        <BCol v-show="part.character_group_id == null">
          <BFormGroup label-size="sm" label="Character">
            <BFormSelect
              :model-value="part.character_id"
              :options="characterOptions"
              :state="characterState"
              @update:model-value="onCharacterChange($event as number | null, null)"
            />
          </BFormGroup>
        </BCol>
        <BCol v-show="part.character_id == null">
          <BFormGroup label-size="sm" label="Character Group">
            <BFormSelect
              :model-value="part.character_group_id"
              :options="characterGroupOptions"
              :state="characterGroupState"
              @update:model-value="onCharacterChange(null, $event as number | null)"
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
            @update:model-value="$emit('stage-direction-style-change', $event as number | null)"
          />
        </BFormGroup>
      </BCol>
      <BCol v-if="showRemoveButton" cols="auto" class="align-self-end mb-3">
        <BButton
          v-b-tooltip.hover.top="'Remove line part'"
          variant="outline-danger"
          size="sm"
          @click="$emit('remove-line-part')"
        >
          <IMdiMinusBox />
        </BButton>
      </BCol>
    </BRow>
    <BRow>
      <BCol style="display: inline-flex">
        <input
          ref="textInputEl"
          type="text"
          class="form-control"
          :class="{ 'is-valid': lineTextState === true, 'is-invalid': lineTextState === false }"
          :value="textField.value.value"
          @input="onTextInput(($event.target as HTMLInputElement).value)"
          @keyup="textField.onCaretActivity"
          @click="textField.onCaretActivity"
          @focus="textField.onCaretActivity"
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
import { ref, computed, onMounted, nextTick } from 'vue';
import { useVuelidate } from '@vuelidate/core';
import { required } from '@vuelidate/validators';
import { LINE_TYPES } from '@/constants/lineTypes';
import { useScriptDraftStore } from '@/stores/scriptDraft';
import { useUserStore } from '@/stores/user';
import { useDraftWriter } from '@/composables/useDraftWriter';
import { useYTextField } from '@/composables/useYTextField';
import { snapshotPagesToScriptLines } from '@/js/yjs/draftAdapter';
import { toast } from '@/js/toast';
import {
  buildMruCharacterOptions,
  buildMruCharacterGroupOptions,
  buildCombinedCharacterOptions,
  type CombinedSelectOption,
} from '@/js/mruSortUtils';
import type { DraftScriptLinePart } from '@/js/yjs/draftAdapter';
import type { StageDirectionStyle } from '@/types/api/script';
import type { Character, CharacterGroup } from '@/types/api/show';

/**
 * Draft-aware sibling of the classic `ScriptLinePart.vue`: writes go straight to the
 * shared Yjs draft (`useDraftWriter`) the moment they happen rather than being staged in
 * local state and emitted up on "Done" — another editor's cursor in the same field needs
 * to see each keystroke, not a batch of them.
 */

const props = defineProps<{
  page: number;
  lineUid: string;
  part: DraftScriptLinePart;
  focusInput: boolean;
  characters: Character[];
  characterGroups: CharacterGroup[];
  showAddButton: boolean;
  enableAddButton: boolean;
  showRemoveButton: boolean;
  lineType: number;
  lineParts: DraftScriptLinePart[];
  stageDirectionStyles?: StageDirectionStyle[];
  stageDirectionStyleId?: number | null;
}>();

const emit = defineEmits<{
  'add-line-part': [];
  'remove-line-part': [];
  'try-finish-line': [];
  'stage-direction-style-change': [id: number | null];
}>();

const draftStore = useScriptDraftStore();
const userStore = useUserStore();
const writer = useDraftWriter();

const textInputEl = ref<HTMLInputElement | null>(null);

function warnIfGone(ok: boolean): void {
  if (!ok) toast.warning('This line part was changed or removed by another editor.');
}

const textField = useYTextField(
  () => writer.getPartText(props.page, props.lineUid, props.part._uid),
  (text: string) => {
    const result = writer.setPartText(props.page, props.lineUid, props.part._uid, text);
    if (result === 'gone') warnIfGone(false);
  }
);

function onTextInput(text: string): void {
  v$.value.line_text.$touch();
  textField.onInput(text);
}

const userSettings = computed(
  () =>
    userStore.userSettings as {
      character_mru_sort?: boolean;
      character_combined_dropdown?: boolean;
    }
);

const tmpScript = computed(() => snapshotPagesToScriptLines(draftStore.pageSnapshots));

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
    if (props.part.character_id != null) return `c:${props.part.character_id}`;
    if (props.part.character_group_id != null) return `g:${props.part.character_group_id}`;
    return null;
  },
  set(val: string | null) {
    if (val == null) {
      onCharacterChange(null, null);
    } else if (val.startsWith('c:')) {
      onCharacterChange(Number.parseInt(val.slice(2), 10), null);
    } else if (val.startsWith('g:')) {
      onCharacterChange(null, Number.parseInt(val.slice(2), 10));
    }
  },
});

function onCharacterChange(characterId: number | null, characterGroupId: number | null): void {
  v$.value.character_id.$touch();
  v$.value.character_group_id.$touch();
  warnIfGone(
    writer.setPartCharacter(
      props.page,
      props.lineUid,
      props.part._uid,
      characterId,
      characterGroupId
    )
  );
}

const isCharacterRequired = computed(
  () => props.lineType === LINE_TYPES.DIALOGUE && props.part.character_group_id == null
);
const isCharacterGroupRequired = computed(
  () => props.lineType === LINE_TYPES.DIALOGUE && props.part.character_id == null
);
const isLineTextRequired = computed(
  () => props.lineParts.length <= 1 || !props.lineParts.some((x) => x.line_text !== '')
);

const rules = computed(() => ({
  character_id: isCharacterRequired.value ? { required } : {},
  character_group_id: isCharacterGroupRequired.value ? { required } : {},
  line_text: isLineTextRequired.value ? { required } : {},
}));

const v$ = useVuelidate(
  rules,
  computed(() => props.part)
);

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

function handleEnterPress(): void {
  v$.value.$touch();
  emit('try-finish-line');
}

defineExpose({ focus: () => textInputEl.value?.focus() });

onMounted(() => {
  textField.inputRef.value = textInputEl.value;
  v$.value.$touch();
  if (props.focusInput) {
    requestAnimationFrame(() => {
      nextTick(() => textInputEl.value?.focus());
    });
  }
});
</script>
