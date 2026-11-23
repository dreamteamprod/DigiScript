<template>
  <BRow
    class="script-line-row"
    :class="{
      'stage-direction': line.line_type === LINE_TYPES.STAGE_DIRECTION,
      'heading-padding': line.line_type === LINE_TYPES.DIALOGUE && needsHeadingsAll,
      'remote-editing-row': (remoteEditors?.length ?? 0) > 0,
      'line-row-selected': selected,
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
      <BFormCheckbox
        v-if="canEdit && !isCutMode"
        class="line-select-checkbox"
        :model-value="selected"
        :aria-label="`Select line ${lineIndex + 1}`"
        @update:model-value="$emit('toggle-select')"
        @click.stop
      >
        <span class="line-number">{{ lineIndex + 1 }}</span>
      </BFormCheckbox>
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
import { computed } from 'vue';
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
  /** Phase 4 Step C: usernames of other room members with this line open. */
  remoteEditors?: string[];
}>();

const emit = defineEmits<{
  editLine: [];
  cutLinePart: [partId: number];
  'toggle-select': [];
}>();

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
.line-row-editable:hover,
.line-row-editable:focus-within {
  background-color: rgba(255, 255, 255, 0.06);
  border-radius: 4px;
  transition: background-color 0.15s ease;
}
.line-row-selected {
  background-color: rgba(var(--bs-success-rgb), 0.08);
  box-shadow: inset 3px 0 0 var(--bs-success);
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
