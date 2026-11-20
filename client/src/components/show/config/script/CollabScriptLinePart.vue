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
        <label :for="`line-part-text-${part._uid}`" class="visually-hidden">Line text</label>
        <input
          :id="`line-part-text-${part._uid}`"
          ref="textInputEl"
          type="text"
          class="form-control"
          :class="{ 'is-valid': lineTextState === true, 'is-invalid': lineTextState === false }"
          :value="textField.value.value"
          @input="onTextInput(($event.target as HTMLInputElement).value)"
          @keyup="textField.onCaretActivity"
          @click="textField.onCaretActivity"
          @focus="textField.onCaretActivity"
          @select="textField.onCaretActivity"
          @keydown.enter="handleEnterPress"
          @compositionstart="textField.onCompositionStart"
          @compositionend="onTextCompositionEnd(($event.target as HTMLInputElement).value)"
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
import { buildCombinedCharacterOptions, type CombinedSelectOption } from '@/js/mruSortUtils';
import {
  characterSelectOptions,
  characterGroupSelectOptions,
  stageDirectionStyleSelectOptions,
} from '@/js/scriptLinePartOptions';
import { fieldState, combinedFieldState } from '@/js/vuelidateFieldState';
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

function onTextCompositionEnd(text: string): void {
  v$.value.line_text.$touch();
  textField.onCompositionEnd(text);
}

const userSettings = computed(
  () =>
    userStore.userSettings as {
      character_mru_sort?: boolean;
      character_combined_dropdown?: boolean;
    }
);

// Gated on the MRU setting, not just unused when it's off: every open part's text
// field changes on every local *and* remote keystroke (scriptDraft.ts replaces the
// page snapshot on every Y change), so converting the whole draft here unconditionally
// would re-run this on every keystroke in every open part, not just the one being typed
// in. The ternary's false branch never touches pageSnapshots, so the computed doesn't
// depend on it (and skips the conversion) while MRU sort is off.
const tmpScript = computed(() =>
  userSettings.value.character_mru_sort ? snapshotPagesToScriptLines(draftStore.pageSnapshots) : {}
);

const characterOptions = computed(() =>
  characterSelectOptions(props.characters, tmpScript.value, !!userSettings.value.character_mru_sort)
);

const characterGroupOptions = computed(() =>
  characterGroupSelectOptions(
    props.characterGroups,
    tmpScript.value,
    !!userSettings.value.character_mru_sort
  )
);

const stageDirectionStyleOptions = computed(() =>
  stageDirectionStyleSelectOptions(props.stageDirectionStyles)
);

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

// A part has a character or a character group, never both (the writer's
// `assertNotBoth` enforces this on write, but a remote peer's part could still arrive
// in that state) — without this, neither field has an active `required` rule once the
// other is set, so both report no error and `combinedFieldState` reads it as valid.
function notBothCharacterFields(_value: unknown, part: DraftScriptLinePart): boolean {
  return !(part.character_id != null && part.character_group_id != null);
}

const rules = computed(() => ({
  character_id: { ...(isCharacterRequired.value ? { required } : {}), notBothCharacterFields },
  character_group_id: {
    ...(isCharacterGroupRequired.value ? { required } : {}),
    notBothCharacterFields,
  },
  line_text: isLineTextRequired.value ? { required } : {},
}));

const v$ = useVuelidate(
  rules,
  computed(() => props.part)
);

const characterState = computed(() => fieldState(v$.value.character_id));
const characterGroupState = computed(() => fieldState(v$.value.character_group_id));
const lineTextState = computed(() => fieldState(v$.value.line_text));
const combinedState = computed(() =>
  combinedFieldState(v$.value.character_id, v$.value.character_group_id)
);

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
