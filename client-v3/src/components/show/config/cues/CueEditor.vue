<template>
  <BContainer class="mx-0 px-0" fluid>
    <BRow class="script-row mb-2">
      <BCol cols="2">
        <BButtonGroup>
          <BButton variant="success" @click="goToPageModal?.show()">Go to Page</BButton>
          <BButton variant="success" @click="jumpToCueModal?.show()">Go to Cue</BButton>
        </BButtonGroup>
      </BCol>
      <BCol cols="2" style="text-align: right">
        <BButton variant="success" :disabled="currentEditPage === 1" @click="decrPage">
          Prev Page
        </BButton>
      </BCol>
      <BCol cols="4" class="text-center">
        <p class="mb-0">Current Page: {{ currentEditPage }}</p>
      </BCol>
      <BCol cols="2" style="text-align: left">
        <BButton variant="success" :disabled="currentEditPage >= currentMaxPage" @click="incrPage">
          Next Page
        </BButton>
      </BCol>
      <BCol cols="2" />
    </BRow>
    <BRow class="script-row">
      <BCol cols="3">Cues</BCol>
      <BCol>Script</BCol>
    </BRow>
    <hr />
    <BRow class="script-row">
      <BCol cols="12">
        <template
          v-for="(line, index) in scriptStore.getScriptPage(currentEditPage)"
          :key="`page_${currentEditPage}_line_${index}`"
        >
          <ScriptLineCueEditor
            :line="line"
            :line-index="index"
            :previous-line="scriptStore.getScriptPage(currentEditPage)[index - 1] ?? null"
            :acts="showStore.actList"
            :scenes="showStore.sceneList"
            :characters="showStore.characterList"
            :character-groups="showStore.characterGroupList"
            :cues="scriptStore.cuesForLine(line.id)"
            :cue-types="showStore.cueTypes"
            :cuts="scriptStore.cuts"
          />
        </template>
      </BCol>
    </BRow>

    <BModal
      ref="goToPageModal"
      title="Go to Page"
      size="sm"
      :hide-header-close="changingPage"
      :hide-footer="changingPage"
      :no-close-on-backdrop="changingPage"
      :no-close-on-esc="changingPage"
      :ok-disabled="pageV$.pageInputFormState.$invalid"
      @ok.prevent="goToPage"
    >
      <BForm @submit.stop.prevent="goToPage">
        <BFormGroup label="Page" label-for="page-input" label-cols="auto">
          <BFormInput
            id="page-input"
            v-model="v$.pageInputFormState.pageNo.$model"
            name="page-input"
            type="number"
            :state="validatePageState('pageNo')"
            aria-describedby="page-feedback"
          />
          <BFormInvalidFeedback id="page-feedback">
            This is a required field, and must be greater than 0.
          </BFormInvalidFeedback>
        </BFormGroup>
      </BForm>
    </BModal>

    <JumpToCueModal ref="jumpToCueModal" @navigate="handleJumpToCue" />
  </BContainer>
</template>

<script setup lang="ts">
import { ref, watch, onBeforeMount } from 'vue';
import { useVuelidate } from '@vuelidate/core';
import { required, minValue } from '@vuelidate/validators';
import type { BModal } from 'bootstrap-vue-next';
import { notNull, notNullAndGreaterThanZero } from '@/js/customValidators';
import { useScriptStore } from '@/stores/script';
import { useShowStore } from '@/stores/show';
import { useUserStore } from '@/stores/user';
import ScriptLineCueEditor from '@/components/show/config/cues/ScriptLineCueEditor.vue';
import JumpToCueModal from '@/components/show/config/cues/JumpToCueModal.vue';

const scriptStore = useScriptStore();
const showStore = useShowStore();
const userStore = useUserStore();

const currentEditPage = ref(1);
const currentMaxPage = ref(1);
const changingPage = ref(false);

const goToPageModal = ref<InstanceType<typeof BModal> | null>(null);
const jumpToCueModal = ref<InstanceType<typeof JumpToCueModal> | null>(null);

const pageInputFormState = ref({ pageNo: 1 });

const rules = {
  pageInputFormState: {
    pageNo: { required, notNull, notNullAndGreaterThanZero, minValue: minValue(1) },
  },
};
const v$ = useVuelidate(rules, { pageInputFormState });
// Alias for template ok-disabled binding
const pageV$ = v$;

watch(currentEditPage, (val) => {
  localStorage.setItem('cueEditPage', String(val));
});

onBeforeMount(async () => {
  await Promise.all([
    userStore.getCurrentUser().then(() => {
      if (userStore.currentUser != null) {
        return Promise.all([
          userStore.getStageDirectionStyleOverrides(),
          userStore.getCueColourOverrides(),
        ]);
      }
    }),
    showStore.getActList(),
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

  const storedPage = localStorage.getItem('cueEditPage');
  if (storedPage != null) {
    currentEditPage.value = Number.parseInt(storedPage, 10);
  }
  await goToPageInner(currentEditPage.value);
});

function validatePageState(name: 'pageNo'): boolean | null {
  const field = v$.value.pageInputFormState[name];
  return field.$dirty ? !field.$error : null;
}

async function goToPageInner(pageNo: number): Promise<void> {
  if (pageNo > 1) {
    await scriptStore.loadScriptPage(pageNo - 1);
  }
  await scriptStore.loadScriptPage(pageNo);
  currentEditPage.value = pageNo;
  await scriptStore.loadScriptPage(pageNo + 1);
}

async function goToPage(): Promise<void> {
  const valid = await v$.value.$validate();
  if (!valid) return;
  changingPage.value = true;
  await goToPageInner(pageInputFormState.value.pageNo);
  changingPage.value = false;
  goToPageModal.value?.hide();
}

async function decrPage(): Promise<void> {
  if (currentEditPage.value > 1) {
    const targetPage = currentEditPage.value - 1;
    await scriptStore.loadScriptPage(targetPage);
    currentEditPage.value--;
    await scriptStore.loadScriptPage(currentEditPage.value - 1);
  }
}

async function incrPage(): Promise<void> {
  currentEditPage.value++;
  await scriptStore.loadScriptPage(currentEditPage.value + 1);
}

async function handleJumpToCue(pageNumber: number): Promise<void> {
  await goToPageInner(pageNumber);
  jumpToCueModal.value?.hide();
}
</script>
