<template>
  <BRow
    :class="{
      'stage-direction': line.line_type === LINE_TYPES.STAGE_DIRECTION,
      'heading-padding': line.line_type === LINE_TYPES.DIALOGUE && needsHeadingsAll,
    }"
  >
    <BCol cols="1">
      <p v-if="showActSceneLabel" class="viewable-line">{{ actLabel }}</p>
    </BCol>
    <BCol cols="1">
      <p v-if="showActSceneLabel" class="viewable-line">{{ sceneLabel }}</p>
    </BCol>

    <!-- Dialogue -->
    <template v-if="line.line_type === LINE_TYPES.DIALOGUE">
      <BCol>
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
              :class="{ 'cut-line-part': linePartCuts.indexOf(part.id) !== -1 }"
            >
              {{ part.line_text }}
            </p>
            <a
              v-else
              class="viewable-line-cut"
              :class="{ 'cut-line-part': linePartCuts.indexOf(part.id) !== -1 }"
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
      <BCol :style="{ textAlign: textAlign }">
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
      <BCol style="text-align: center">
        <BAlert variant="secondary" :model-value="true">
          <p class="text-muted small" style="margin: 0">Cue Line</p>
        </BAlert>
      </BCol>
    </template>

    <!-- Spacing -->
    <template v-else-if="line.line_type === LINE_TYPES.SPACING">
      <BCol style="text-align: center">
        <BAlert variant="secondary" :model-value="true">
          <p class="text-muted small" style="margin: 0">Spacing Line</p>
        </BAlert>
      </BCol>
    </template>

    <BCol cols="1" align-self="end">
      <BButtonGroup v-if="bulkEditMode && canEdit && !isCutMode">
        <BButton
          size="sm"
          :variant="isBulkStart ? 'success' : 'outline-secondary'"
          @click.stop="$emit('set-bulk-start')"
        >
          Start
        </BButton>
        <BButton
          size="sm"
          :variant="isBulkEnd ? 'success' : 'outline-secondary'"
          @click.stop="$emit('set-bulk-end')"
        >
          End
        </BButton>
      </BButtonGroup>
      <BDropdown
        v-else-if="canEdit && !isCutMode"
        split
        text="Edit"
        end
        boundary="window"
        style="padding: 0"
        variant="link"
        @click.prevent.stop="$emit('editLine')"
      >
        <BDropdownItem @click.prevent.stop="$emit('insertDialogue')">Insert Dialogue</BDropdownItem>
        <BDropdownItem @click.prevent.stop="$emit('insertStageDirection')"
          >Insert Stage Direction</BDropdownItem
        >
        <BDropdownItem @click.prevent.stop="$emit('insertCueLine')">Insert Cue Line</BDropdownItem>
        <BDropdownItem @click.prevent.stop="$emit('insertSpacing')">Insert Spacing</BDropdownItem>
        <BDropdownItem variant="danger" @click.prevent.stop="$emit('deleteLine')"
          >Delete</BDropdownItem
        >
      </BDropdown>
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
import type { ScriptLine, StageDirectionStyle } from '@/types/api/script';
import type { Act, Scene, Character, CharacterGroup } from '@/types/api/show';

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
  bulkEditMode?: boolean;
  isBulkStart?: boolean;
  isBulkEnd?: boolean;
}>();

const emit = defineEmits<{
  editLine: [];
  cutLinePart: [partId: number];
  insertDialogue: [];
  insertStageDirection: [];
  insertCueLine: [];
  insertSpacing: [];
  deleteLine: [];
  'set-bulk-start': [];
  'set-bulk-end': [];
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

const needsHeadingsAny = computed(() => needsHeadings.value.some((x) => x));
const needsHeadingsAll = computed(() => needsHeadings.value.every((x) => x));

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
  const base = stageDirectionStyling(currentStyle.value);
  const firstPartId = props.line.line_parts[0]?.id;
  if (firstPartId != null && props.linePartCuts.indexOf(firstPartId) !== -1) {
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
</style>
