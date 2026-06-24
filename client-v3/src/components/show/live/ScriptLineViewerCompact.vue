<template>
  <div
    ref="lineContainer"
    style="margin: 0; padding: 0"
    :style="{ paddingTop: spacingBefore + 'rem', '--spacing-before': spacingBefore + 'rem' }"
  >
    <BContainer v-once fluid class="mx-0" style="margin: 0; padding: 0">
      <BRow v-if="needsIntervalBanner" class="interval-header">
        <BCol cols="12" class="interval-banner">
          <BAlert variant="warning" style="margin: 0">
            <h3>{{ previousActLabel }} - Interval</h3>
          </BAlert>
        </BCol>
        <BCol
          v-if="isScriptLeader"
          cols="12"
          class="d-flex align-items-center justify-content-center"
          style="padding-top: 0.5rem; padding-bottom: 0.5rem"
        >
          <BButton variant="primary" @click.stop="startInterval">Start Interval</BButton>
        </BCol>
      </BRow>
      <BRow v-if="needsActSceneLabel" class="act-scene">
        <BCol
          cols="2"
          :class="['cue-column', 'text-end', 'fw-bold', 'cue', { 'first-row': isFirstRowActScene }]"
        >
          <span>{{ actLabel }}</span>
        </BCol>
        <BCol :cols="cueAddMode ? 9 : 10" class="line-part text-start fw-bold cue">
          <span>{{ sceneLabel }}</span>
        </BCol>
        <BCol v-if="cueAddMode" cols="1" class="cue-add-column" />
      </BRow>
      <BRow v-for="(cue, cueIndex) in individualCues" :key="`cue_${cue.id}`">
        <BCol
          cols="2"
          :class="[
            'cue-column',
            'line-part',
            'text-end',
            'fw-bold',
            'cue',
            { 'first-row': isFirstRowCues && cueIndex === 0 },
          ]"
          :style="{ color: cueBackgroundColour(cue) }"
        >
          <span>{{ cuePrefix(cue) }}</span>
        </BCol>
        <BCol
          :cols="cueAddMode ? 9 : 10"
          class="line-part text-start fw-bold cue"
          :style="{ color: cueBackgroundColour(cue) }"
        >
          <span>{{ cue.ident }}</span>
        </BCol>
        <BCol v-if="cueAddMode" cols="1" class="cue-add-column" />
      </BRow>
      <BRow v-for="(grp, groupIndex) in lineGroups" :key="`group_${grp.group.id}`">
        <BCol
          cols="2"
          :class="[
            'cue-column',
            'line-part',
            'text-end',
            'fw-bold',
            'cue',
            { 'first-row': isFirstRowCues && individualCues.length === 0 && groupIndex === 0 },
          ]"
          :style="{ color: cueGroupBackgroundColour(grp.group) }"
        >
          <span>{{ cueGroupPrefix(grp.group) }}</span>
        </BCol>
        <BCol
          :cols="cueAddMode ? 9 : 10"
          class="line-part text-start fw-bold cue"
          :style="{ color: cueGroupBackgroundColour(grp.group) }"
        >
          <span>{{ cueGroupIdentLabel(grp.group, grp.cues) }}</span>
        </BCol>
        <BCol v-if="cueAddMode" cols="1" class="cue-add-column" />
      </BRow>
      <BRow class="line-row">
        <template v-if="line.line_type === LINE_TYPES.DIALOGUE">
          <template v-for="(part, index) in line.line_parts" :key="`part_${lineIndex}_${index}`">
            <BCol
              cols="2"
              class="cue-column line-part text-end"
              :class="{
                'cut-line-part': cuts.includes(part.id),
                'line-part-a': lineIndex % 2 === 0,
                'line-part-b': lineIndex % 2 === 1,
                'first-row': isFirstRowContent && index === 0,
              }"
            >
              <p v-if="needsHeadings[index]">{{ characterOrGroupName(part) }}</p>
            </BCol>
            <BCol
              :cols="cueAddMode ? 9 : 10"
              class="line-part text-start"
              :class="{
                'cut-line-part': cuts.includes(part.id),
                'line-part-a': lineIndex % 2 === 0,
                'line-part-b': lineIndex % 2 === 1,
              }"
            >
              <p class="viewable-line">{{ part.line_text }}</p>
            </BCol>
          </template>
          <BCol
            v-if="cueAddMode && !isLineCut"
            cols="1"
            class="cue-add-column d-flex align-items-center justify-content-center"
          >
            <BButton variant="success" size="sm" class="add-cue-btn" @click.stop="addNewCue"
              ><IMdiPlusBox
            /></BButton>
          </BCol>
        </template>
        <template v-else-if="line.line_type === LINE_TYPES.STAGE_DIRECTION">
          <BCol cols="2" class="cue-column line-part text-end">
            <p v-if="isTaggedStageDirection">{{ characterOrGroupName(line.line_parts[0]) }}</p>
          </BCol>
          <BCol :cols="cueAddMode ? 9 : 10" class="line-part text-start">
            <i class="viewable-line" :style="stageDirectionStylingObj">
              <template v-if="stageDirectionStyle?.text_format === 'upper'">
                {{ line.line_parts[0]?.line_text?.toUpperCase() }}
              </template>
              <template v-else-if="stageDirectionStyle?.text_format === 'lower'">
                {{ line.line_parts[0]?.line_text?.toLowerCase() }}
              </template>
              <template v-else>
                {{ line.line_parts[0]?.line_text }}
              </template>
            </i>
          </BCol>
          <BCol
            v-if="cueAddMode"
            cols="1"
            class="cue-add-column d-flex align-items-center justify-content-center"
          >
            <BButton variant="success" size="sm" class="add-cue-btn" @click.stop="addNewCue"
              ><IMdiPlusBox
            /></BButton>
          </BCol>
        </template>
        <template v-else-if="line.line_type === LINE_TYPES.CUE_LINE">
          <BCol cols="2" class="cue-column" />
          <BCol :cols="cueAddMode ? 9 : 10" class="line-part text-start" />
          <BCol
            v-if="cueAddMode"
            cols="1"
            class="cue-add-column d-flex align-items-center justify-content-center"
          >
            <BButton variant="success" size="sm" class="add-cue-btn" @click.stop="addNewCue"
              ><IMdiPlusBox
            /></BButton>
          </BCol>
        </template>
      </BRow>
    </BContainer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue';
import { useScriptNavigation } from '@/composables/useScriptNavigation';
import { useScriptDisplay } from '@/composables/useScriptDisplay';
import { useCueDisplay } from '@/composables/useCueDisplay';
import { useScriptStore } from '@/stores/script';
import { isWholeLineCut } from '@/js/scriptUtils';
import { LINE_TYPES } from '@/constants/lineTypes';
import type { ScriptLine, ScriptCut, StageDirectionStyle } from '@/types/api/script';
import type { Act, Scene, Character, CharacterGroup } from '@/types/api/show';
import type { Cue, CueType } from '@/types/api/cues';

const props = defineProps<{
  line: ScriptLine;
  lineIndex: number;
  previousLine: ScriptLine | null;
  previousLineIndex: number | null;
  acts: Act[];
  scenes: Scene[];
  characters: Character[];
  characterGroups: CharacterGroup[];
  cueTypes: CueType[];
  cues: Cue[];
  cuts: ScriptCut[];
  stageDirectionStyles: StageDirectionStyle[];
  stageDirectionStyleOverrides: StageDirectionStyle[];
  isScriptLeader: boolean;
  cueAddMode: boolean;
  spacingBefore?: number;
}>();

const emit = defineEmits<{
  'last-line-change': [page: number, lineIndex: number];
  'first-line-change': [page: number, lineIndex: number, previousLineRef: string | null];
  'start-interval': [actId: number];
  'add-cue': [lineId: number];
}>();

const scriptStore = useScriptStore();
const { needsHeadings: computeNeedsHeadings, needsActSceneLabel: computeNeedsActSceneLabel } =
  useScriptNavigation();
const { getStageDirectionStyle, stageDirectionStyling: computeStyling } = useScriptDisplay();
const {
  cuePrefix,
  cueBackgroundColour,
  cueGroupBackgroundColour,
  cueGroupPrefix,
  cueGroupIdentLabel,
} = useCueDisplay();

const individualCues = computed(() => props.cues.filter((c) => c.group_id == null));
const lineGroups = computed(() => scriptStore.groupedCuesForLine(props.line.id).groups);

const lineContainer = ref<HTMLElement | null>(null);
let observer: MutationObserver | null = null;

const needsHeadings = computed(() =>
  computeNeedsHeadings(props.line, props.previousLine, props.cuts, scriptStore.getScriptPage)
);

const needsActSceneLabel = computed(() =>
  computeNeedsActSceneLabel(props.line, props.previousLine, props.cuts, scriptStore.getScriptPage)
);

const needsIntervalBanner = computed(() => {
  let prev: ScriptLine | null = props.previousLine;
  while (prev != null && isWholeLineCut(prev, props.cuts)) {
    const prevPage = scriptStore.getScriptPage(prev.page ?? 0);
    const idx = prevPage.indexOf(prev);
    prev = idx > 0 ? prevPage[idx - 1] : null;
  }
  if (prev == null || prev.act_id === props.line.act_id) return false;
  const prevAct = props.acts.find((a) => a.id === prev!.act_id);
  return prevAct?.interval_after === true;
});

const previousActLabel = computed(
  () => props.acts.find((a) => a.id === props.previousLine?.act_id)?.name ?? null
);
const actLabel = computed(() => props.acts.find((a) => a.id === props.line.act_id)?.name ?? null);
const sceneLabel = computed(
  () => props.scenes.find((s) => s.id === props.line.scene_id)?.name ?? null
);

const stageDirectionStyle = computed(() =>
  getStageDirectionStyle(props.line, props.stageDirectionStyles, props.stageDirectionStyleOverrides)
);
const stageDirectionStylingObj = computed(() => computeStyling(stageDirectionStyle.value));

const isTaggedStageDirection = computed(() => {
  const part = props.line.line_parts?.[0];
  return (
    props.line.line_type === LINE_TYPES.STAGE_DIRECTION &&
    (part?.character_id != null || part?.character_group_id != null)
  );
});

const isLineCut = computed(() => isWholeLineCut(props.line, props.cuts));
const hasAnyCues = computed(() => individualCues.value.length > 0 || lineGroups.value.length > 0);
const isFirstRowActScene = computed(() => needsActSceneLabel.value);
const isFirstRowCues = computed(() => !needsActSceneLabel.value && hasAnyCues.value);
const isFirstRowContent = computed(() => !needsActSceneLabel.value && !hasAnyCues.value);

function characterOrGroupName(part: ScriptLine['line_parts'][number]): string {
  if (part.character_id != null) {
    return props.characters.find((c) => c.id === part.character_id)?.name ?? '';
  }
  return props.characterGroups.find((g) => g.id === part.character_group_id)?.name ?? '';
}

function addNewCue(): void {
  emit('add-cue', props.line.id);
}

function startInterval(): void {
  if (!props.previousLine) return;
  const actId = props.acts.find((a) => a.id === props.previousLine!.act_id)?.id;
  if (actId != null) emit('start-interval', actId);
}

function onClassChange(classAttrValue: string | null, oldClassAttrValue: string | null): void {
  const classList = classAttrValue?.split(' ') ?? [];
  const oldClassList = oldClassAttrValue?.split(' ') ?? [];
  if (classList.includes('last-script-element') && !oldClassList.includes('last-script-element')) {
    emit('last-line-change', props.line.page ?? 0, props.lineIndex);
  }
  if (
    classList.includes('first-script-element') &&
    !oldClassList.includes('first-script-element')
  ) {
    const prev = props.previousLine;
    const prevRef = prev == null ? null : `page_${prev.page}_line_${props.previousLineIndex}`;
    emit('first-line-change', props.line.page ?? 0, props.lineIndex, prevRef);
  }
}

onMounted(() => {
  if (lineContainer.value) {
    observer = new MutationObserver((mutations) => {
      for (const m of mutations) {
        const newValue = (m.target as Element).getAttribute(m.attributeName!);
        onClassChange(newValue, m.oldValue);
      }
    });
    observer.observe(lineContainer.value, {
      attributes: true,
      attributeOldValue: true,
      attributeFilter: ['class'],
    });
  }
});

onUnmounted(() => {
  observer?.disconnect();
});
</script>

<style scoped>
.cue-column {
  border-right: 0.1rem solid #3498db;
  margin-top: -1rem;
  margin-bottom: -1rem;
  padding-top: 1rem;
  padding-bottom: 1rem;
}

.cue-column.first-row {
  margin-top: calc(-1rem - var(--spacing-before, 0rem));
  padding-top: calc(1rem + var(--spacing-before, 0rem));
}

.cut-line-part {
  text-decoration: line-through;
}

.line-part {
  font-size: 1.5rem;
}

.cue {
  font-size: 2rem;
}

.line-part-a {
  color: white;
}

.line-part-b {
  color: gray;
}

.act-scene {
  color: #f401fe;
}

.current-line {
  background: #3498db54;
}

.interval-header {
  background: var(--bs-body-bg);
  margin-top: 1rem;
  padding-bottom: 1rem;
}

.interval-banner {
  margin-top: -1rem;
  margin-bottom: -1rem;
  padding-top: 1rem;
  padding-bottom: 1rem;
}

.cue-add-column {
  border-left: 0.1rem solid #3498db;
}

.line-row:has(.add-cue-btn:hover) {
  background-color: rgba(255, 255, 255, 0.06);
  border-radius: 4px;
  transition: background-color 0.15s ease;
}
</style>
