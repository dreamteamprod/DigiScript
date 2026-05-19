<template>
  <BRow
    ref="scriptContainerRow"
    :aria-hidden="intervalActive ? 'true' : null"
    :style="{ 'margin-right': stageManagerMode ? '0px' : '-15px' }"
  >
    <BCol
      id="script-container"
      cols="12"
      class="script-container"
      :data-following="isScriptFollowing"
    >
      <div v-if="!initialLoad" class="text-center center-spinner">
        <BSpinner style="width: 10rem; height: 10rem" variant="info" />
      </div>
      <template v-else>
        <template v-if="scriptMode === 2">
          <template v-for="page in pageIter" :key="`page_${page}`">
            <ScriptLineViewerCompact
              v-for="(line, index) in scriptStore.getScriptPage(page)"
              v-show="
                !isWholeLineCut(line, scriptStore.cuts) && line.line_type !== LINE_TYPES.SPACING
              "
              :id="`page_${page}_line_${index}`"
              :key="`page_${page}_line_${index}_ADDMODE:${cueAddMode}_CUES:${scriptStore.cuesForLine(line.id).length}`"
              class="script-item"
              :line-index="index"
              :line="line"
              :acts="showStore.actList"
              :scenes="showStore.sceneList"
              :characters="showStore.characterList"
              :character-groups="showStore.characterGroupList"
              :previous-line="getPreviousLineForIndex(page, index)"
              :previous-line-index="getPreviousLineIndex(page, index)"
              :cue-types="showStore.cueTypes"
              :cues="scriptStore.cuesForLine(line.id)"
              :cuts="scriptStore.cuts"
              :stage-direction-styles="scriptStore.stageDirectionStyles"
              :stage-direction-style-overrides="userStore.stageDirectionStyleOverrides"
              :is-script-leader="isScriptLeader"
              :cue-add-mode="cueAddMode"
              :spacing-before="getSpacingBefore(page, index)"
              @last-line-change="handleLastLineChange"
              @first-line-change="handleFirstLineChange"
              @start-interval="configureInterval"
              @add-cue="openNewCueModal"
            />
          </template>
        </template>
        <template v-else>
          <template v-for="page in pageIter" :key="`page_${page}`">
            <ScriptLineViewer
              v-for="(line, index) in scriptStore.getScriptPage(page)"
              v-show="
                !isWholeLineCut(line, scriptStore.cuts) && line.line_type !== LINE_TYPES.SPACING
              "
              :id="`page_${page}_line_${index}`"
              :key="`page_${page}_line_${index}_ADDMODE:${cueAddMode}_CUES:${scriptStore.cuesForLine(line.id).length}`"
              class="script-item"
              :line-index="index"
              :line="line"
              :acts="showStore.actList"
              :scenes="showStore.sceneList"
              :characters="showStore.characterList"
              :character-groups="showStore.characterGroupList"
              :previous-line="getPreviousLineForIndex(page, index)"
              :previous-line-index="getPreviousLineIndex(page, index)"
              :cue-types="showStore.cueTypes"
              :cues="scriptStore.cuesForLine(line.id)"
              :cuts="scriptStore.cuts"
              :stage-direction-styles="scriptStore.stageDirectionStyles"
              :stage-direction-style-overrides="userStore.stageDirectionStyleOverrides"
              :is-script-leader="isScriptLeader"
              :cue-add-mode="cueAddMode"
              :spacing-before="getSpacingBefore(page, index)"
              @last-line-change="handleLastLineChange"
              @first-line-change="handleFirstLineChange"
              @start-interval="configureInterval"
              @add-cue="openNewCueModal"
            />
          </template>
        </template>
        <BRow class="script-footer">
          <BCol>
            <BButtonGroup>
              <BButton variant="danger" :disabled="stoppingSession" @click.stop="stopShow">
                End Show
              </BButton>
            </BButtonGroup>
          </BCol>
        </BRow>
      </template>
    </BCol>

    <!-- Start Interval Modal -->
    <BModal
      ref="intervalModal"
      title="Start Interval"
      size="md"
      ok-title="Start"
      :ok-disabled="intervalTimerLength === 0"
      ok-only
      ok-variant="success"
      @show="
        intervalModalOpen = true;
        resetIntervalState();
      "
      @hidden="
        intervalModalOpen = false;
        resetIntervalState();
      "
      @ok="startInterval"
    >
      <BContainer fluid class="mx-0">
        <BRow class="justify-content-center mb-3">
          <BCol md="auto">
            <div class="d-flex align-items-center gap-2">
              <div class="text-center">
                <label class="form-label">Hours</label>
                <BFormInput
                  v-model.number="intervalHours"
                  type="number"
                  min="0"
                  max="23"
                  style="width: 5rem; text-align: center"
                />
              </div>
              <span class="fs-4 pt-3">:</span>
              <div class="text-center">
                <label class="form-label">Minutes</label>
                <BFormInput
                  v-model.number="intervalMinutes"
                  type="number"
                  min="0"
                  max="59"
                  style="width: 5rem; text-align: center"
                />
              </div>
              <span class="fs-4 pt-3">:</span>
              <div class="text-center">
                <label class="form-label">Seconds</label>
                <BFormInput
                  v-model.number="intervalSeconds"
                  type="number"
                  min="0"
                  max="59"
                  style="width: 5rem; text-align: center"
                />
              </div>
            </div>
          </BCol>
        </BRow>
        <BRow class="justify-content-center">
          <BCol md="auto">
            <BAlert variant="info" :model-value="true">
              Select the length of the interval (HH:MM:SS)
            </BAlert>
          </BCol>
        </BRow>
      </BContainer>
    </BModal>

    <!-- Add Cue Modal -->
    <BModal
      ref="newCueModal"
      title="Add New Cue"
      size="md"
      :ok-disabled="v$.newCueFormState.$invalid || submittingNewCue"
      @show="newCueModalOpen = true"
      @hidden="
        newCueModalOpen = false;
        resetNewCueForm();
      "
      @ok="onSubmitNewCue"
    >
      <BForm @submit.stop.prevent="onSubmitNewCue">
        <BFormGroup label="Cue Type" label-for="cue-type-input">
          <BFormSelect
            id="cue-type-input"
            v-model="v$.newCueFormState.cueType.$model"
            :options="cueTypeOptions"
            :state="validateFieldState('cueType')"
          />
          <BFormInvalidFeedback>This is a required field.</BFormInvalidFeedback>
        </BFormGroup>
        <BFormGroup label="Identifier" label-for="ident-input">
          <BFormInput
            id="ident-input"
            v-model="v$.newCueFormState.ident.$model"
            :state="validateFieldState('ident')"
          />
          <BFormInvalidFeedback>This is a required field.</BFormInvalidFeedback>
          <BFormText v-if="isDuplicateCue" class="text-warning">
            A cue with this identifier already exists for this cue type
          </BFormText>
        </BFormGroup>
      </BForm>
    </BModal>
  </BRow>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue';
import { useVuelidate } from '@vuelidate/core';
import { required } from '@vuelidate/validators';
import { debounce } from 'lodash';
import log from 'loglevel';

import { makeURL } from '@/js/utils';
import { isWholeLineCut } from '@/js/scriptUtils';
import { LINE_TYPES } from '@/constants/lineTypes';
import { useShowStore } from '@/stores/show';
import { useScriptStore } from '@/stores/script';
import { useUserStore } from '@/stores/user';
import { useSystemStore } from '@/stores/system';
import { useWebSocket } from '@/composables/useWebSocket';
import { toast } from '@/js/toast';
import ScriptLineViewer from './ScriptLineViewer.vue';
import ScriptLineViewerCompact from './ScriptLineViewerCompact.vue';
import type { ScriptLine } from '@/types/api/script';

const props = defineProps<{
  isScriptFollowing: boolean;
  isScriptLeader: boolean;
  sessionFollowData: Record<string, unknown>;
  initialLineRef: string | null;
  intervalActive: boolean;
  scriptMode: number;
  stageManagerMode: boolean;
}>();

const emit = defineEmits<{
  'page-change': [page: number];
  'script-loaded': [];
}>();

const showStore = useShowStore();
const scriptStore = useScriptStore();
const userStore = useUserStore();
const systemStore = useSystemStore();
const { sendObj } = useWebSocket();

// Template refs
const intervalModal = ref<InstanceType<(typeof import('bootstrap-vue-next'))['BModal']> | null>(
  null
);
const newCueModal = ref<InstanceType<(typeof import('bootstrap-vue-next'))['BModal']> | null>(null);

// Page loading state
const currentLoadedPage = ref(0);
const currentMaxPage = ref(0);
const currentFirstPage = ref(1);
const currentLastPage = ref(1);
const currentMinLoadedPage = ref<number | null>(null);
const pageBatchSize = 3;
const assignedLastLine = ref(false);

// Script load state
const initialLoad = ref(false);
const fullLoad = ref(false);

// Navigation state
const currentPage = ref(1);
const currentLineOnPage = ref(0);
const currentLine = ref<string | null>(null);
const previousLine = ref<string | null>(null);
const isScrollingProgrammatically = ref(false);

// UI state
const cueAddMode = ref(false);
const intervalModalOpen = ref(false);
const newCueModalOpen = ref(false);

// Cue modal state
const newCueFormState = ref({
  cueType: null as number | null,
  ident: null as string | null,
  lineId: null as number | null,
});
const submittingNewCue = ref(false);

// Interval modal state
const intervalActId = ref<number | null>(null);
const intervalHours = ref(0);
const intervalMinutes = ref(0);
const intervalSeconds = ref(0);

// Session control
const stoppingSession = ref(false);

// Vuelidate
const rules = {
  newCueFormState: {
    cueType: { required },
    ident: { required },
    lineId: { required },
  },
};
const v$ = useVuelidate(rules, { newCueFormState });

// Computed
const pageIter = computed(() => [...Array(currentMaxPage.value).keys()].map((i) => i + 1));

const intervalTimerLength = computed(
  () => intervalHours.value * 3600 + intervalMinutes.value * 60 + intervalSeconds.value
);

const cueTypeOptions = computed(() => [
  { value: null, text: 'N/A' },
  ...showStore.cueTypes.map((ct) => ({ value: ct.id, text: `${ct.prefix}: ${ct.description}` })),
]);

const isDuplicateCue = computed(() => {
  if (!newCueFormState.value.ident || !newCueFormState.value.cueType) return false;
  const allCues = Object.values(scriptStore.cues).flat();
  return allCues.some(
    (cue) =>
      cue.cue_type_id === newCueFormState.value.cueType && cue.ident === newCueFormState.value.ident
  );
});

// Debounced resize handler
const debounceContentSize = debounce(computeContentSize, 100);

// --- Navigation ---

function getPreviousLineForIndex(pageIndex: number, lineIndex: number): ScriptLine | null {
  if (lineIndex > 0) {
    return scriptStore.getScriptPage(pageIndex)[lineIndex - 1] ?? null;
  }
  let loopPageNo = pageIndex - 1;
  while (loopPageNo >= 1) {
    const loopPage = scriptStore.getScriptPage(loopPageNo);
    if (loopPage.length > 0) return loopPage[loopPage.length - 1];
    loopPageNo--;
  }
  return null;
}

function getPreviousLineIndex(pageIndex: number, lineIndex: number): number | null {
  if (lineIndex > 0) return lineIndex - 1;
  let loopPageNo = pageIndex - 1;
  while (loopPageNo >= 1) {
    const loopPage = scriptStore.getScriptPage(loopPageNo);
    if (loopPage.length > 0) return loopPage.length - 1;
    loopPageNo--;
  }
  return null;
}

function getSpacingBefore(page: number, index: number): number {
  let spacingCount = 0;
  let currentPageIdx = page;
  let currentIndex = index - 1;

  while (currentPageIdx >= 1) {
    if (currentIndex < 0) {
      currentPageIdx--;
      if (currentPageIdx < 1) break;
      const prevPageLines = scriptStore.getScriptPage(currentPageIdx);
      if (!prevPageLines || prevPageLines.length === 0) break;
      currentIndex = prevPageLines.length - 1;
      continue;
    }
    const pageLines = scriptStore.getScriptPage(currentPageIdx);
    if (!pageLines || currentIndex >= pageLines.length) break;
    const line = pageLines[currentIndex];
    if (line.line_type === LINE_TYPES.SPACING) {
      spacingCount++;
      currentIndex--;
    } else {
      break;
    }
  }
  return spacingCount;
}

function scrollToElement(element: Element | null): void {
  const container = document.getElementById('script-container');
  if (!container || !element) return;
  const elementRect = element.getBoundingClientRect();
  const containerRect = container.getBoundingClientRect();
  container.scrollTop = elementRect.top - containerRect.top + container.scrollTop;
}

function findContextElement(
  targetPage: number,
  targetLineOnPage: number,
  contextLines: number
): Element | null {
  let curPage = targetPage;
  let curLine = targetLineOnPage;
  let visibleLinesFound = 0;

  while (visibleLinesFound < contextLines && curPage >= 1) {
    curLine--;
    if (curLine < 0) {
      curPage--;
      if (curPage < 1) return document.getElementById('page_1_line_0');
      const prevPageLines = scriptStore.getScriptPage(curPage);
      if (!prevPageLines || prevPageLines.length === 0) continue;
      curLine = prevPageLines.length - 1;
    }
    const pageLines = scriptStore.getScriptPage(curPage);
    if (pageLines && curLine < pageLines.length) {
      const line = pageLines[curLine];
      if (!isWholeLineCut(line, scriptStore.cuts)) {
        visibleLinesFound++;
        if (visibleLinesFound >= contextLines) {
          return document.getElementById(`page_${curPage}_line_${curLine}`);
        }
      }
    }
  }
  if (visibleLinesFound > 0) {
    return document.getElementById(`page_${curPage}_line_${curLine}`);
  }
  return null;
}

function navigateTo(targetPage: number, targetLineOnPage: number, preventScroll = false): boolean {
  if (targetPage > currentLoadedPage.value) return false;
  const pageLines = scriptStore.getScriptPage(targetPage);
  if (!pageLines || targetLineOnPage >= pageLines.length) return false;

  currentPage.value = targetPage;
  currentLineOnPage.value = targetLineOnPage;
  emit('page-change', targetPage);

  const targetElementId = `page_${targetPage}_line_${targetLineOnPage}`;
  const targetElement = document.getElementById(targetElementId);
  if (!targetElement) {
    log.error(`Could not find element for line: ${targetElementId}`);
    return false;
  }

  document.querySelectorAll('.script-item').forEach((el) => el.classList.remove('current-line'));
  targetElement.classList.add('current-line');

  previousLine.value = currentLine.value;
  currentLine.value = targetElementId;

  if (!preventScroll) {
    isScrollingProgrammatically.value = true;
    const contextElement = findContextElement(targetPage, targetLineOnPage, 3);
    scrollToElement(contextElement ?? targetElement);

    if (fullLoad.value) {
      sendObj({
        OP: 'SCRIPT_SCROLL',
        DATA: { previous_line: previousLine.value, current_line: currentLine.value },
      });
    }

    setTimeout(() => {
      isScrollingProgrammatically.value = false;
      computeScriptBoundaries();
    }, 50);
  }

  return true;
}

function navigateRelative(deltaLine: number): boolean {
  if (deltaLine === 0) return true;
  const direction = deltaLine > 0 ? 1 : -1;
  let newPage = currentPage.value;
  let newLineOnPage = currentLineOnPage.value;
  let visibleLinesMoved = 0;

  while (visibleLinesMoved < Math.abs(deltaLine)) {
    newLineOnPage += direction;
    if (newLineOnPage < 0) {
      newPage--;
      if (newPage < 1) {
        newPage = 1;
        newLineOnPage = 0;
        break;
      }
      const prevPageLines = scriptStore.getScriptPage(newPage);
      if (!prevPageLines) break;
      newLineOnPage = prevPageLines.length - 1;
      if (newLineOnPage < 0) newLineOnPage = 0;
    } else {
      const currentPageLines = scriptStore.getScriptPage(newPage);
      if (!currentPageLines) break;
      if (newLineOnPage >= currentPageLines.length) {
        newPage++;
        if (newPage > currentLoadedPage.value) {
          newPage = currentLoadedPage.value;
          newLineOnPage = currentPageLines.length - 1;
          break;
        }
        newLineOnPage = 0;
      }
    }
    const pageLines = scriptStore.getScriptPage(newPage);
    if (pageLines && newLineOnPage < pageLines.length) {
      if (!isWholeLineCut(pageLines[newLineOnPage], scriptStore.cuts)) {
        visibleLinesMoved++;
      }
      if (visibleLinesMoved >= Math.abs(deltaLine)) break;
    } else {
      break;
    }
  }
  return navigateTo(newPage, newLineOnPage);
}

// --- Keyboard/wheel handlers ---

function handleKeyPress(event: KeyboardEvent): void {
  if (event.key === 'ArrowUp' || event.key === 'ArrowDown') {
    handleKeyNavigation(event);
  } else if (event.key === 'PageUp' || event.key === 'PageDown') {
    handlePageNavigation(event);
  } else if (event.key === 'C') {
    handleCueEditToggle(event);
  }
}

function handleCueEditToggle(event: KeyboardEvent): void {
  event.preventDefault();
  if (systemStore.isShowEditor) {
    cueAddMode.value = !cueAddMode.value;
  } else {
    cueAddMode.value = false;
  }
}

function handleKeyNavigation(event: KeyboardEvent): void {
  if (
    !props.isScriptLeader ||
    !initialLoad.value ||
    isScrollingProgrammatically.value ||
    props.intervalActive ||
    intervalModalOpen.value ||
    newCueModalOpen.value
  )
    return;
  event.preventDefault();
  navigateRelative(event.key === 'ArrowDown' ? 1 : -1);
}

function handlePageNavigation(event: KeyboardEvent): void {
  if (
    !props.isScriptLeader ||
    !initialLoad.value ||
    isScrollingProgrammatically.value ||
    props.intervalActive ||
    intervalModalOpen.value ||
    newCueModalOpen.value
  )
    return;
  event.preventDefault();
  const isPageDown = event.key === 'PageDown';
  let targetPage = currentPage.value + (isPageDown ? 1 : -1);
  if (targetPage < 1) targetPage = 1;
  else if (targetPage > currentLoadedPage.value) return;
  navigateTo(targetPage, 0);
}

function handleWheelNavigation(event: WheelEvent): void {
  if (
    !props.isScriptLeader ||
    !initialLoad.value ||
    isScrollingProgrammatically.value ||
    props.intervalActive ||
    intervalModalOpen.value ||
    newCueModalOpen.value
  )
    return;
  const scriptContainer = document.getElementById('script-container');
  if (!scriptContainer) return;
  const isAtTop = scriptContainer.scrollTop === 0;
  const isAtBottom =
    scriptContainer.scrollHeight - scriptContainer.scrollTop === scriptContainer.clientHeight;
  if ((event.deltaY > 0 && !isAtBottom) || (event.deltaY < 0 && !isAtTop)) {
    event.preventDefault();
    navigateRelative(event.deltaY > 0 ? 1 : -1);
  }
}

// --- Follow watcher ---

function handleFollowDataChange(): void {
  const followData = props.sessionFollowData;
  if (props.isScriptFollowing && followData.current_line) {
    const lineRef = followData.current_line as string;
    const currentLineElement = document.getElementById(lineRef);
    if (currentLineElement != null) {
      const idParts = lineRef.split('_');
      const page = parseInt(idParts[1], 10);
      const line = parseInt(idParts[3], 10);

      document
        .querySelectorAll('.script-item')
        .forEach((el) => el.classList.remove('current-line'));
      currentLineElement.classList.add('current-line');

      const contextElement = findContextElement(page, line, 3);
      scrollToElement(contextElement ?? currentLineElement);

      currentPage.value = page;
      emit('page-change', page);
      computeScriptBoundaries();
    }
  }
}

// --- Script boundaries ---

function computeScriptBoundaries(): void {
  if (isScrollingProgrammatically.value) return;
  const scriptContainer = document.getElementById('script-container');
  if (!scriptContainer) return;

  const containerRect = scriptContainer.getBoundingClientRect();
  const cutoffTop = containerRect.top;
  const cutoffBottom = containerRect.top + scriptContainer.clientHeight;
  const scriptItems = scriptContainer.querySelectorAll<HTMLElement>('.script-item');

  let firstAssigned = false;
  scriptItems.forEach((el) => el.classList.remove('first-script-element'));
  for (const el of Array.from(scriptItems)) {
    const rect = el.getBoundingClientRect();
    if (rect.top >= cutoffTop) {
      el.classList.add('first-script-element');
      firstAssigned = true;
      break;
    }
  }
  if (!firstAssigned && scriptItems.length > 0) {
    scriptItems[0].classList.add('first-script-element');
  }

  let lastObject: HTMLElement | null = null;
  let assignedLast = false;
  scriptItems.forEach((el) => el.classList.remove('last-script-element'));
  for (const el of Array.from(scriptItems)) {
    const rect = el.getBoundingClientRect();
    if (rect.top >= cutoffBottom) {
      el.classList.add('last-script-element');
      assignedLast = true;
      break;
    }
    if (rect.top < cutoffBottom) lastObject = el;
  }
  assignedLastLine.value = assignedLast;
  if (!assignedLast && lastObject) {
    lastObject.classList.add('last-script-element');
  }
}

function computeContentSize(): void {
  const scriptContainer = document.getElementById('script-container');
  if (!scriptContainer) return;
  const startPos = scriptContainer.getBoundingClientRect().top;
  const boxHeight = document.documentElement.clientHeight - startPos;
  scriptContainer.style.height = `${boxHeight - 10}px`;
  computeScriptBoundaries();
}

// --- Script loading ---

async function loadCompiledScript(): Promise<boolean> {
  const response = await fetch(makeURL('/api/v1/show/script/compiled'));
  if (!response.ok) return false;
  const respJson = await response.json();
  let maxLoadedPage = 1;
  let minLoadedPage = Number.POSITIVE_INFINITY;
  Object.entries(respJson).forEach(([pageStr, pageContents]) => {
    const pageNumber = parseInt(pageStr, 10);
    if (pageNumber > maxLoadedPage) maxLoadedPage = pageNumber;
    if (pageNumber < minLoadedPage) minLoadedPage = pageNumber;
    scriptStore.script[String(pageNumber)] = pageContents as ScriptLine[];
  });
  currentLoadedPage.value = maxLoadedPage;
  currentMinLoadedPage.value = minLoadedPage;
  return true;
}

async function loadNextPage(): Promise<void> {
  if (currentLoadedPage.value < currentMaxPage.value) {
    currentLoadedPage.value++;
    await scriptStore.loadScriptPage(currentLoadedPage.value);
  }
}

// --- Lazy-load handlers from line components ---

async function handleLastLineChange(lastPage: number, _lineIndex: number): Promise<void> {
  currentLastPage.value = lastPage;
  const cutoffPage = currentLoadedPage.value - pageBatchSize;
  if (lastPage >= cutoffPage && currentLoadedPage.value < currentMaxPage.value) {
    for (let i = 0; i < pageBatchSize; i++) await loadNextPage();
    computeScriptBoundaries();
    while (!assignedLastLine.value && currentLoadedPage.value <= currentMaxPage.value) {
      await loadNextPage();
      computeScriptBoundaries();
      await nextTick();
    }
  }
  await nextTick();
}

async function handleFirstLineChange(
  firstPage: number,
  lineIndex: number,
  prevLine: string | null
): Promise<void> {
  currentFirstPage.value = firstPage;
  previousLine.value = prevLine;
  currentLine.value = `page_${firstPage}_line_${lineIndex}`;

  const cutoffPage = firstPage - pageBatchSize;
  if ((currentMinLoadedPage.value ?? 0) > cutoffPage) {
    for (let i = 0; i < pageBatchSize; i++) {
      if ((currentMinLoadedPage.value ?? 0) > 1) {
        currentMinLoadedPage.value = (currentMinLoadedPage.value ?? 1) - 1;
        await scriptStore.loadScriptPage(currentMinLoadedPage.value);
      }
    }
  }
}

// --- Interval modal ---

function configureInterval(actId: number): void {
  intervalActId.value = actId;
  (intervalModal.value as any)?.show();
}

function resetIntervalState(): void {
  intervalHours.value = 0;
  intervalMinutes.value = 0;
  intervalSeconds.value = 0;
}

function startInterval(): void {
  sendObj({
    OP: 'BEGIN_INTERVAL',
    DATA: { actId: intervalActId.value, length: intervalTimerLength.value },
  });
  toast.success('Interval started!');
}

// --- Cue modal ---

function openNewCueModal(lineId: number): void {
  resetNewCueForm();
  newCueFormState.value.lineId = lineId;
  (newCueModal.value as any)?.show();
}

function resetNewCueForm(): void {
  newCueFormState.value = { cueType: null, ident: null, lineId: null };
  submittingNewCue.value = false;
  nextTick(() => v$.value.$reset());
}

function validateFieldState(field: 'cueType' | 'ident'): boolean | null {
  const f = v$.value.newCueFormState[field];
  return f.$dirty ? !f.$error : null;
}

async function onSubmitNewCue(event: Event): Promise<void> {
  v$.value.newCueFormState.$touch();
  if (v$.value.newCueFormState.$invalid || submittingNewCue.value) {
    event.preventDefault();
    return;
  }
  submittingNewCue.value = true;
  try {
    await scriptStore.addNewCue({
      cueType: newCueFormState.value.cueType!,
      ident: newCueFormState.value.ident!,
      lineId: newCueFormState.value.lineId!,
    });
    (newCueModal.value as any)?.hide();
    resetNewCueForm();
  } catch (error) {
    log.error('Error submitting new cue:', error);
    event.preventDefault();
  } finally {
    submittingNewCue.value = false;
  }
}

// --- Stop show ---

async function stopShow(): Promise<void> {
  stoppingSession.value = true;
  const response = await fetch(makeURL('/api/v1/show/sessions/stop'), { method: 'POST' });
  if (response.ok) {
    toast.success('Stopped show session');
  } else {
    log.error('Unable to stop show session');
    toast.error('Unable to stop show session');
  }
  stoppingSession.value = false;
}

// --- Lifecycle ---

onMounted(async () => {
  await Promise.all([
    userStore.getCurrentUser().then(() => {
      if (userStore.currentUser != null) {
        return Promise.all([
          userStore.getStageDirectionStyleOverrides(),
          userStore.getCueColourOverrides(),
        ]);
      }
      return Promise.resolve();
    }),
    showStore.getSceneList(),
    showStore.getCharacterList(),
    showStore.getCharacterGroupList(),
    showStore.getCueTypes(),
    scriptStore.loadCues(),
    scriptStore.getCuts(),
    scriptStore.getStageDirectionStyles(),
    scriptStore.getMaxPage().then(() => {
      currentMaxPage.value = scriptStore.maxPage;
    }),
  ]);

  computeContentSize();

  const loadedCompiledScript = await loadCompiledScript();

  if (!loadedCompiledScript) {
    currentMinLoadedPage.value = 1;
    for (let i = 0; i < currentMaxPage.value; i++) await loadNextPage();
  }

  initialLoad.value = true;
  await nextTick();
  computeScriptBoundaries();

  if (props.initialLineRef) {
    scrollToElement(document.getElementById(props.initialLineRef));
    const parts = props.initialLineRef.split('_');
    if (parts.length >= 4) {
      navigateTo(parseInt(parts[1], 10), parseInt(parts[3], 10));
    }
    await nextTick();
    computeScriptBoundaries();
  } else {
    navigateTo(1, 0);
  }

  fullLoad.value = true;

  window.addEventListener('keydown', handleKeyPress);
  const scriptContainer = document.getElementById('script-container');
  if (scriptContainer) {
    scriptContainer.addEventListener('wheel', handleWheelNavigation, { passive: false });
  }
  window.addEventListener('resize', debounceContentSize);

  emit('script-loaded');
});

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyPress);
  const scriptContainer = document.getElementById('script-container');
  if (scriptContainer) {
    scriptContainer.removeEventListener('wheel', handleWheelNavigation);
  }
  window.removeEventListener('resize', debounceContentSize);
});

// Watch follow data reactively
import { watch } from 'vue';
watch(() => props.sessionFollowData, handleFollowDataChange, { deep: true });
</script>

<style scoped>
.script-container {
  overflow: scroll;
  overflow-x: auto;
  width: 100vw;
  -ms-overflow-style: none;
  scrollbar-width: none;
}

.script-container::-webkit-scrollbar {
  display: none;
  width: 0 !important;
}

.script-container[data-following='true'] {
  overflow: hidden !important;
}

.script-footer {
  border-top: 0.1rem solid #3498db;
  padding-top: 0.5rem;
  padding-bottom: 0.1rem;
}

.center-spinner {
  margin-top: 20vh;
}
</style>
