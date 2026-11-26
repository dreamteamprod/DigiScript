<template>
  <BRow
    class="script-line-row"
    :class="{
      'stage-direction': line.line_type === LINE_TYPES.STAGE_DIRECTION,
      'heading-padding': line.line_type === LINE_TYPES.DIALOGUE && needsHeadingsAll,
      'remote-editing-row': (remoteEditors?.length ?? 0) > 0,
      'line-row-selected': selected,
      'line-row-preview-change': previewed,
      'line-row-editable': canEdit && !isCutMode,
    }"
  >
    <!-- Above the Act/Scene/Line columns, not below them, so it reads as a label on
         top of this row rather than a trailing footnote — see RemoteEditorsBadge's
         own cols="12" note further down for why this doesn't add a second row. -->
    <RemoteEditorsBadge :names="remoteEditors ?? []" />

    <!-- Design E's gutter: a selection checkbox, labelled with the line number, when
         editing is possible — a plain number otherwise. Checkbox and number sit side
         by side rather than swapping on hover: overlaying the two exactly (tried
         first) left a stray element intercepting the checkbox's own click target. -->
    <BCol cols="1" class="line-gutter">
      <!-- A plain native checkbox, not BFormCheckbox: the selection range model
           means a click's resulting `selected` value for THIS checkbox can be the
           same before and after (e.g. collapsing a multi-line range down onto the
           very line that was clicked, or deselecting the only selected line), which
           left it visually wrong in two different ways before this:
           - BFormCheckbox's own internal checked state could fail to re-sync from a
             changed `selected` prop once the user had interacted with it once.
           - Even with a plain native `:checked` binding plus `@click.prevent`,
             Chromium still reverted the input's checked DOM property back to its
             *pre-click* value as part of a prevented click's "canceled activation
             steps" — which runs synchronously right after Vue's own render, so it
             clobbers whatever Vue had just (correctly) written, independently of
             whether preventDefault was called at all.
           Fixed by not fighting the browser's click handling and instead
           force-correcting the DOM in onToggleClick's nextTick, which runs as a
           microtask after that synchronous revert has already happened — so it's
           always the last write, regardless of what the browser did in between. -->
      <label
        v-if="canEdit && !isCutMode"
        class="line-select-checkbox"
        @mouseenter="$emit('hover-checkbox')"
        @mouseleave="$emit('unhover-checkbox')"
      >
        <input
          ref="checkboxEl"
          type="checkbox"
          class="form-check-input"
          :checked="selected"
          :aria-label="`Select line ${lineIndex + 1}`"
          @click.stop="onToggleClick"
          @focus="$emit('hover-checkbox')"
          @blur="$emit('unhover-checkbox')"
        />
        <span class="line-number">{{ lineIndex + 1 }}</span>
      </label>
      <span v-else class="line-number">{{ lineIndex + 1 }}</span>
    </BCol>

    <BCol cols="1">
      <p v-if="showActSceneLabel" class="viewable-line">{{ actLabel }}</p>
    </BCol>
    <BCol cols="1">
      <p v-if="showActSceneLabel" class="viewable-line">{{ sceneLabel }}</p>
    </BCol>

    <!-- Dialogue -->
    <template v-if="line.line_type === LINE_TYPES.DIALOGUE">
      <BCol class="line-content" @click="onContentClick">
        <BRow v-if="needsHeadingsAny">
          <BCol
            v-for="(part, index) in line.line_parts"
            :key="`heading_${lineIndex}_part_${index}`"
            :style="headingStyle"
          >
            <template v-if="needsHeadings[index]">
              <b>
                <template v-if="part.character_id != null">
                  {{ characters.find((c) => c.id === part.character_id)?.name }}
                </template>
                <template v-else>
                  {{ characterGroups.find((g) => g.id === part.character_group_id)?.name }}
                </template>
              </b>
            </template>
            <b v-else>&nbsp;</b>
          </BCol>
        </BRow>
        <BRow>
          <BCol
            v-for="(part, index) in line.line_parts"
            :key="`line_${lineIndex}_part_${index}`"
            :style="dialogueStyle"
          >
            <p
              v-if="!canEdit || !isCutMode"
              class="viewable-line"
              :class="{ 'cut-line-part': linePartCuts.includes(part.id) }"
            >
              {{ part.line_text }}
            </p>
            <a
              v-else
              class="viewable-line-cut"
              :class="{ 'cut-line-part': linePartCuts.includes(part.id) }"
              @click.stop="cutLinePart(index)"
            >
              {{ part.line_text }}
            </a>
          </BCol>
        </BRow>
      </BCol>
    </template>

    <!-- Stage direction -->
    <template v-else-if="line.line_type === LINE_TYPES.STAGE_DIRECTION">
      <BCol class="line-content" :style="{ textAlign: textAlign }" @click="onContentClick">
        <BRow v-if="isTaggedStageDirection && needsHeadingsAny" style="margin-bottom: 1rem">
          <BCol :style="headingStyle">
            <b>{{ taggedStageDirectionHeadingName }}</b>
          </BCol>
        </BRow>
        <i
          v-if="!canEdit || !isCutMode"
          class="viewable-line"
          :style="stageDirectionStylingWithCuts"
        >
          {{ formatStageDirectionText(line.line_parts[0]?.line_text) }}
        </i>
        <a
          v-else
          class="viewable-line-cut"
          :style="stageDirectionStylingWithCuts"
          @click.stop="cutLinePart(0)"
        >
          {{ formatStageDirectionText(line.line_parts[0]?.line_text) }}
        </a>
      </BCol>
    </template>

    <!-- Cue line -->
    <template v-else-if="line.line_type === LINE_TYPES.CUE_LINE">
      <BCol class="line-content" style="text-align: center" @click="onContentClick">
        <BAlert variant="secondary" :model-value="true">
          <p class="text-muted small" style="margin: 0">Cue Line</p>
        </BAlert>
      </BCol>
    </template>

    <!-- Spacing -->
    <template v-else-if="line.line_type === LINE_TYPES.SPACING">
      <BCol class="line-content" style="text-align: center" @click="onContentClick">
        <BAlert variant="secondary" :model-value="true">
          <p class="text-muted small" style="margin: 0">Spacing Line</p>
        </BAlert>
      </BCol>
    </template>

    <BCol v-if="canEdit && !isCutMode" cols="1" align-self="center" class="line-edit-trigger-col">
      <button type="button" class="line-edit-trigger" @click="$emit('editLine')">
        Click to edit
      </button>
    </BCol>
  </BRow>
</template>

<script setup lang="ts">
import { computed, nextTick, ref } from 'vue';
import { LINE_TYPES } from '@/constants/lineTypes';
import { useScriptConfigStore } from '@/stores/scriptConfig';
import { useUserStore } from '@/stores/user';
import { useScriptDisplay } from '@/composables/useScriptDisplay';
import { toast } from '@/js/toast';
import RemoteEditorsBadge from './RemoteEditorsBadge.vue';
import type { ScriptLine, StageDirectionStyle } from '@/types/api/script';
import type { Act, Scene, Character, CharacterGroup } from '@/types/api/show';
import type { UserSettings } from '@/types/api/user';

const props = defineProps<{
  line: ScriptLine;
  lineIndex: number;
  page: ScriptLine[];
  previousLine: ScriptLine | null;
  acts: Act[];
  scenes: Scene[];
  characters: Character[];
  characterGroups: CharacterGroup[];
  canEdit: boolean;
  linePartCuts: (number | null)[];
  stageDirectionStyles: StageDirectionStyle[];
  stageDirectionStyleOverrides: StageDirectionStyle[];
  /** Whether this line currently falls within the active selection range. */
  selected?: boolean;
  /** Whether hovering/focusing a checkbox elsewhere means this line's own
   * selected state would flip if that checkbox were clicked right now — see
   * ScriptEditor.vue's isLinePreviewChanging. */
  previewed?: boolean;
  /** Phase 4 Step C: usernames of other room members with this line open. */
  remoteEditors?: string[];
}>();

const emit = defineEmits<{
  'hover-checkbox': [];
  'unhover-checkbox': [];
  editLine: [];
  cutLinePart: [partId: number];
  'toggle-select': [];
}>();

const checkboxEl = ref<HTMLInputElement | null>(null);

/** See the template's own comment on why this, not a plain @click handler:
 * Chromium reverts a clicked checkbox's native `checked` DOM property back to
 * its pre-click value as the last step of handling the click (even though we
 * never actually asked for the native toggle), clobbering whatever Vue had
 * just rendered from the new `selected` prop. nextTick's callback runs as a
 * microtask, strictly after that synchronous revert, so re-asserting the
 * prop's value there is guaranteed to be the last write — regardless of
 * whatever the browser did to the DOM in between. */
function onToggleClick(): void {
  emit('toggle-select');
  nextTick(() => {
    if (checkboxEl.value) checkboxEl.value.checked = props.selected;
  });
}

const scriptConfigStore = useScriptConfigStore();
const userStore = useUserStore();
const { getStageDirectionStyle, stageDirectionStyling, scriptTextAlign } = useScriptDisplay();

const isCutMode = computed(() => scriptConfigStore.cutMode);
const textAlign = computed(() =>
  scriptTextAlign(userStore.userSettings as Record<string, unknown>)
);
const headingStyle = computed(() => ({ textAlign: textAlign.value }));
const dialogueStyle = computed(() => ({ textAlign: textAlign.value }));

function onContentClick(): void {
  if (props.canEdit && !isCutMode.value) emit('editLine');
}

const showActSceneLabel = computed<boolean>(() => {
  if (!props.previousLine) return true;
  return !(
    props.previousLine.act_id === props.line.act_id &&
    props.previousLine.scene_id === props.line.scene_id
  );
});

const actLabel = computed<string | null>(
  () => props.acts.find((a) => a.id === props.line.act_id)?.name ?? null
);
const sceneLabel = computed<string | null>(
  () => props.scenes.find((s) => s.id === props.line.scene_id)?.name ?? null
);

const needsHeadings = computed<boolean[]>(() => {
  let prev = props.previousLine;
  let prevIdx = props.lineIndex - 1;
  while (
    prev != null &&
    prev.line_type === LINE_TYPES.STAGE_DIRECTION &&
    prev.line_parts[0]?.character_id == null &&
    prev.line_parts[0]?.character_group_id == null
  ) {
    if (prevIdx === 0) break;
    prevIdx -= 1;
    prev = props.page[prevIdx] ?? null;
  }

  return props.line.line_parts.map((part) => {
    if (!prev || prev.line_parts.length !== props.line.line_parts.length) return true;
    const match = prev.line_parts.find((p) => p.part_index === part.part_index);
    if (!match) return true;
    return !(
      match.character_id === part.character_id &&
      match.character_group_id === part.character_group_id
    );
  });
});

const needsHeadingsAny = computed(() => needsHeadings.value.some(Boolean));
const needsHeadingsAll = computed(() => needsHeadings.value.every(Boolean));

const isTaggedStageDirection = computed<boolean>(() => {
  const part = props.line.line_parts?.[0];
  return (
    props.line.line_type === LINE_TYPES.STAGE_DIRECTION &&
    (part?.character_id != null || part?.character_group_id != null)
  );
});

const taggedStageDirectionHeadingName = computed<string>(() => {
  const part = props.line.line_parts?.[0];
  if (!part) return '';
  if (part.character_id != null)
    return props.characters.find((c) => c.id === part.character_id)?.name ?? '';
  return props.characterGroups.find((g) => g.id === part.character_group_id)?.name ?? '';
});

const currentStyle = computed(() =>
  getStageDirectionStyle(props.line, props.stageDirectionStyles, props.stageDirectionStyleOverrides)
);

const stageDirectionStylingWithCuts = computed<Record<string, string>>(() => {
  const base = stageDirectionStyling(currentStyle.value, {
    background_colour: (userStore.userSettings as UserSettings).default_sd_background_colour,
    text_colour: (userStore.userSettings as UserSettings).default_sd_text_colour,
  });
  const firstPartId = props.line.line_parts[0]?.id;
  if (firstPartId != null && props.linePartCuts.includes(firstPartId)) {
    const existing = base['text-decoration-line'];
    base['text-decoration-line'] =
      existing && existing !== 'none' ? `${existing} line-through` : 'line-through';
  }
  return base;
});

function formatStageDirectionText(text: string | null | undefined): string {
  if (text == null) return '';
  if (currentStyle.value?.text_format === 'upper') return text.toUpperCase();
  if (currentStyle.value?.text_format === 'lower') return text.toLowerCase();
  return text;
}

function cutLinePart(partIndex: number): void {
  const part = props.line.line_parts[partIndex];
  if (part?.id != null && part.line_id != null) {
    emit('cutLinePart', part.id);
    return;
  }
  toast.error('Unable to cut line part');
}
</script>

<style scoped>
.viewable-line {
  margin: 0;
}
.viewable-line-cut {
  margin: 0;
  cursor: pointer;
}
.stage-direction {
  margin-top: 1rem;
  margin-bottom: 1rem;
}
.heading-padding {
  margin-top: 0.5rem;
}
.cut-line-part {
  text-decoration: line-through;
}
/* :focus-within:has(:focus-visible), not plain :focus-within: a mouse click on
   the checkbox leaves it focused (correct — don't steal focus from what the
   user just interacted with), but that shouldn't keep painting this row like
   the mouse is still over it once it's moved on. :focus-visible only matches
   when the browser itself would show a focus ring — keyboard navigation, not
   a mouse click — so tabbing to a row still gets this highlight as a focus
   indicator, a click doesn't leave it stuck. */
.line-row-editable:hover,
.line-row-editable:focus-within:has(:focus-visible) {
  background-color: rgba(255, 255, 255, 0.06);
  border-radius: 4px;
  transition: background-color 0.15s ease;
}
@media (prefers-reduced-motion: reduce) {
  .line-row-editable:hover,
  .line-row-editable:focus-within:has(:focus-visible) {
    transition: none;
  }
}
.line-row-selected {
  background-color: rgba(var(--bs-success-rgb), 0.08);
  box-shadow: inset 3px 0 0 var(--bs-success);
}
/* .stage-direction/.heading-padding's own margin is outside this background's
   paintable box, so a selected run of lines showed a hairline gap of bare
   page background cutting through the highlight wherever one occurred.
   Swapping that margin for the exact same padding here closes the gap — the
   margin-box stays the same overall size (so nothing else's layout shifts),
   it's just paintable background from here instead of bare margin. */
.line-row-selected.stage-direction {
  margin-top: 0;
  margin-bottom: 0;
  padding-top: 1rem;
  padding-bottom: 1rem;
}
.line-row-selected.heading-padding {
  margin-top: 0;
  padding-top: 0.5rem;
}
/* Hovering (or Tab-focusing) a checkbox elsewhere previews what ticking it
   right now would do to the rest of the range — a dashed outline, not a
   background fill, so it reads as "about to change" rather than "already
   selected" even on a line that's both (e.g. a shrink preview on the line
   that would be dropped). outline, not border: doesn't affect layout or
   this row's size. */
.line-row-preview-change {
  outline: 1px dashed var(--bs-success);
  outline-offset: -1px;
}
.line-content {
  cursor: default;
}
.line-row-editable .line-content {
  cursor: pointer;
}
.line-gutter {
  text-align: center;
  color: var(--bs-secondary-color);
}
.line-select-checkbox {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.line-select-checkbox .line-number {
  margin-left: 0.4em;
}
/* "Click to edit": a real, always-focusable button so the row is operable from the
   keyboard, visually revealed only on hover/focus (always shown under `@media
   (hover: none)`, matching the gutter checkbox's own touch fallback). */
.line-edit-trigger-col {
  text-align: right;
}
.line-edit-trigger {
  background: none;
  border: none;
  padding: 0;
  color: var(--bs-secondary-color);
  font-size: 0.8125rem;
  opacity: 0;
  cursor: pointer;
}
.line-row-editable:hover .line-edit-trigger,
.line-edit-trigger:focus-visible {
  opacity: 1;
}
@media (hover: none) {
  .line-edit-trigger {
    opacity: 1;
  }
}
/* Phase 4 Step C: another room member has this line open — border/tint match the
   orange "editing" avatar badge so the two read as the same status. */
.remote-editing-row {
  border: 1.5px solid rgba(var(--bs-warning-rgb), 0.65);
  border-radius: 4px;
  background-color: rgba(var(--bs-warning-rgb), 0.1);
}
/* "Jump to" from the presence popover (CollabScriptEditor.vue) briefly flags the
   line it scrolled to, so landing on the right one is obvious even once scrolling
   has already stopped. */
.jump-highlight {
  animation: jump-highlight-flash 2s ease-out;
}
@keyframes jump-highlight-flash {
  0%,
  40% {
    background-color: rgba(var(--bs-success-rgb), 0.25);
    border-radius: 4px;
  }
  100% {
    background-color: transparent;
  }
}
</style>
