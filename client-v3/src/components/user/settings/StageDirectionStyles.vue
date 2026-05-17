<template>
  <div>
    <template v-if="systemStore.currentShow != null">
      <BTable
        id="stage-directions-table"
        :items="tableData"
        :fields="columns"
        :per-page="rowsPerPage"
        :current-page="currentPage"
        show-empty
      >
        <template #head(btn)>
          <BButton
            variant="outline-success"
            :disabled="overrideChoices.length <= 1"
            @click="selectModal?.show()"
          >
            New Override
          </BButton>
        </template>

        <template #cell(description)="data">
          {{ stageDirectionStyles.find((s) => s.id === data.item.settings.id)?.description }}
        </template>

        <template #cell(example)="data">
          <i class="example-stage-direction" :style="exampleCss(data.item.settings)">
            <template v-if="data.item.settings.text_format === 'upper'">
              {{ exampleText.toUpperCase() }}
            </template>
            <template v-else-if="data.item.settings.text_format === 'lower'">
              {{ exampleText.toLowerCase() }}
            </template>
            <template v-else>{{ exampleText }}</template>
          </i>
        </template>

        <template #cell(btn)="data">
          <BButtonGroup>
            <BButton
              variant="warning"
              :disabled="isSubmittingEdit || isDeleting"
              @click="openEditStyleForm(data)"
            >
              Edit
            </BButton>
            <BButton
              variant="danger"
              :disabled="isSubmittingEdit || isDeleting"
              @click="openDeleteConfirm(data.item.id)"
            >
              Delete
            </BButton>
          </BButtonGroup>
        </template>
      </BTable>
    </template>
    <BAlert v-else :model-value="true" variant="danger">No show loaded.</BAlert>

    <!-- Select style modal -->
    <BModal
      ref="selectModal"
      title="Add New Override"
      :ok-disabled="newStyleFormState.styleId == null || isSubmittingNew"
      @show="newStyleFormState.styleId = null"
      @ok="openNewOverrideModal"
    >
      <BForm>
        <BFormSelect v-model="newStyleFormState.styleId" :options="overrideChoices" />
      </BForm>
    </BModal>

    <!-- New override config modal -->
    <BModal
      ref="newModal"
      title="Add New Override"
      size="lg"
      :ok-disabled="isSubmittingNew"
      @hidden="resetNewFormState"
      @ok.prevent="onSubmitNewOverride"
    >
      <div>
        <h4>Example Stage Direction</h4>
        <i class="example-stage-direction" :style="newFormExampleCss">
          <template v-if="newStyleFormState.textFormat === 'upper'">
            {{ exampleText.toUpperCase() }}
          </template>
          <template v-else-if="newStyleFormState.textFormat === 'lower'">
            {{ exampleText.toLowerCase() }}
          </template>
          <template v-else>{{ exampleText }}</template>
        </i>
      </div>
      <div>
        <h4>Configuration Options</h4>
        <BFormGroup label="Default Styles">
          <BButtonGroup>
            <BButton
              v-for="(btn, idx) in newStyleFormState.styleOptions"
              :key="idx"
              v-model:pressed="btn.state"
              variant="primary"
            >
              {{ btn.caption }}
            </BButton>
          </BButtonGroup>
        </BFormGroup>

        <BFormGroup label="Default Text Format" label-for="new-text-format-input">
          <BFormSelect id="new-text-format-input" v-model="newStyleFormState.textFormat">
            <BFormSelectOption value="default">Default</BFormSelectOption>
            <BFormSelectOption value="upper">Uppercase</BFormSelectOption>
            <BFormSelectOption value="lower">Lowercase</BFormSelectOption>
          </BFormSelect>
        </BFormGroup>

        <BFormGroup label="Text Colour" label-for="new-text-colour-input">
          <BFormInput
            id="new-text-colour-input"
            v-model="newStyleFormState.textColour"
            type="color"
            :state="validationState(vNew$.textColour)"
            aria-describedby="new-colour-feedback"
          />
          <BFormInvalidFeedback id="new-colour-feedback">
            This is a required field.
          </BFormInvalidFeedback>
        </BFormGroup>

        <BFormGroup label="Background Colour" label-for="new-background-colour-enable">
          <BFormCheckbox
            id="new-background-colour-enable"
            v-model="newStyleFormState.enableBackgroundColour"
            switch
          />
        </BFormGroup>

        <BFormGroup v-if="newStyleFormState.enableBackgroundColour">
          <BFormInput
            id="new-background-colour-picker"
            v-model="newStyleFormState.backgroundColour"
            type="color"
          />
        </BFormGroup>
      </div>
    </BModal>

    <!-- Edit override config modal -->
    <BModal
      ref="editModal"
      title="Edit Override"
      size="lg"
      :ok-disabled="isSubmittingEdit"
      @hidden="resetEditFormState"
      @ok.prevent="onSubmitEditOverride"
    >
      <div>
        <h4>Example Stage Direction</h4>
        <i class="example-stage-direction" :style="editFormExampleCss">
          <template v-if="editStyleFormState.textFormat === 'upper'">
            {{ exampleText.toUpperCase() }}
          </template>
          <template v-else-if="editStyleFormState.textFormat === 'lower'">
            {{ exampleText.toLowerCase() }}
          </template>
          <template v-else>{{ exampleText }}</template>
        </i>
      </div>
      <div>
        <h4>Configuration Options</h4>
        <BFormGroup label="Default Styles">
          <BButtonGroup>
            <BButton
              v-for="(btn, idx) in editStyleFormState.styleOptions"
              :key="idx"
              v-model:pressed="btn.state"
              variant="primary"
            >
              {{ btn.caption }}
            </BButton>
          </BButtonGroup>
        </BFormGroup>

        <BFormGroup label="Default Text Format" label-for="edit-text-format-input">
          <BFormSelect id="edit-text-format-input" v-model="editStyleFormState.textFormat">
            <BFormSelectOption value="default">Default</BFormSelectOption>
            <BFormSelectOption value="upper">Uppercase</BFormSelectOption>
            <BFormSelectOption value="lower">Lowercase</BFormSelectOption>
          </BFormSelect>
        </BFormGroup>

        <BFormGroup label="Text Colour" label-for="edit-text-colour-input">
          <BFormInput
            id="edit-text-colour-input"
            v-model="editStyleFormState.textColour"
            type="color"
            :state="validationState(vEdit$.textColour)"
            aria-describedby="edit-colour-feedback"
          />
          <BFormInvalidFeedback id="edit-colour-feedback">
            This is a required field.
          </BFormInvalidFeedback>
        </BFormGroup>

        <BFormGroup label="Background Colour" label-for="edit-background-colour-enable">
          <BFormCheckbox
            id="edit-background-colour-enable"
            v-model="editStyleFormState.enableBackgroundColour"
            switch
          />
        </BFormGroup>

        <BFormGroup v-if="editStyleFormState.enableBackgroundColour">
          <BFormInput
            id="edit-background-colour-picker"
            v-model="editStyleFormState.backgroundColour"
            type="color"
          />
        </BFormGroup>
      </div>
    </BModal>

    <!-- Delete confirmation modal -->
    <BModal
      ref="deleteModal"
      title="Delete Override"
      ok-variant="danger"
      ok-title="Delete"
      @ok="confirmDelete"
    >
      <p>Are you sure you want to delete this override?</p>
    </BModal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import type { BModal } from 'bootstrap-vue-next';
import { useVuelidate } from '@vuelidate/core';
import { required } from '@vuelidate/validators';
import log from 'loglevel';
import { makeURL } from '@/js/utils';
import { useUserStore } from '@/stores/user';
import { useSystemStore } from '@/stores/system';
import { useFormValidation } from '@/composables/useFormValidation';
import type { StageDirectionStyle } from '@/types/api/script';

interface StyleOption {
  caption: string;
  state: boolean;
}

const defaultStyleOptions = (): StyleOption[] => [
  { caption: 'Bold', state: false },
  { caption: 'Italic', state: false },
  { caption: 'Underline', state: false },
];

const userStore = useUserStore();
const systemStore = useSystemStore();
const { validationState } = useFormValidation();

const exampleText = 'Your stage direction will look like this when formatted in the script!';
const columns = [
  'description',
  { key: 'example', label: 'Example Stage Direction' },
  { key: 'btn', label: '' },
];
const rowsPerPage = 15;
const currentPage = ref(1);

const stageDirectionStyles = ref<StageDirectionStyle[]>([]);
const isSubmittingNew = ref(false);
const isSubmittingEdit = ref(false);
const isDeleting = ref(false);
const pendingDeleteId = ref<number | null>(null);

const selectModal = ref<InstanceType<typeof BModal>>();
const newModal = ref<InstanceType<typeof BModal>>();
const editModal = ref<InstanceType<typeof BModal>>();
const deleteModal = ref<InstanceType<typeof BModal>>();

const newStyleFormState = ref({
  styleId: null as number | null,
  styleOptions: defaultStyleOptions(),
  textFormat: 'default',
  textColour: '#FFFFFF',
  enableBackgroundColour: false,
  backgroundColour: '#000000',
});

const editStyleFormState = ref({
  id: null as number | null,
  styleId: null as number | null,
  styleOptions: defaultStyleOptions(),
  textFormat: 'default',
  textColour: '#FFFFFF',
  enableBackgroundColour: false,
  backgroundColour: '#000000',
});

const vNewRules = { textColour: { required }, textFormat: { required } };
const vEditRules = { textColour: { required }, textFormat: { required } };
const vNew$ = useVuelidate(vNewRules, newStyleFormState);
const vEdit$ = useVuelidate(vEditRules, editStyleFormState);

const tableData = computed(() =>
  userStore.stageDirectionStyleOverrides.filter((item) =>
    stageDirectionStyles.value.map((s) => s.id).includes(item.settings?.id ?? -1)
  )
);

const overrideChoices = computed(() => [
  { value: null, text: 'Please select an option', disabled: true },
  ...stageDirectionStyles.value
    .filter(
      (s) => !userStore.stageDirectionStyleOverrides.map((o) => o.settings?.id).includes(s.id)
    )
    .map((s) => ({ value: s.id, text: s.description })),
]);

function exampleCss(settings: Record<string, unknown>): Record<string, string> {
  const style: Record<string, string> = {
    'font-weight': settings.bold ? 'bold' : 'normal',
    'font-style': settings.italic ? 'italic' : 'normal',
    'text-decoration-line': settings.underline ? 'underline' : 'none',
    color: settings.text_colour as string,
  };
  if (settings.enable_background_colour) {
    style['background-color'] = settings.background_colour as string;
  }
  return style;
}

const newFormExampleCss = computed((): Record<string, string> => {
  const f = newStyleFormState.value;
  const style: Record<string, string> = {
    'font-weight': f.styleOptions.find((o) => o.caption === 'Bold')!.state ? 'bold' : 'normal',
    'font-style': f.styleOptions.find((o) => o.caption === 'Italic')!.state ? 'italic' : 'normal',
    'text-decoration-line': f.styleOptions.find((o) => o.caption === 'Underline')!.state
      ? 'underline'
      : 'none',
    color: f.textColour,
  };
  if (f.enableBackgroundColour) style['background-color'] = f.backgroundColour;
  return style;
});

const editFormExampleCss = computed((): Record<string, string> => {
  const f = editStyleFormState.value;
  const style: Record<string, string> = {
    'font-weight': f.styleOptions.find((o) => o.caption === 'Bold')!.state ? 'bold' : 'normal',
    'font-style': f.styleOptions.find((o) => o.caption === 'Italic')!.state ? 'italic' : 'normal',
    'text-decoration-line': f.styleOptions.find((o) => o.caption === 'Underline')!.state
      ? 'underline'
      : 'none',
    color: f.textColour,
  };
  if (f.enableBackgroundColour) style['background-color'] = f.backgroundColour;
  return style;
});

onMounted(async () => {
  if (systemStore.currentShow) {
    try {
      const response = await fetch(makeURL('/api/v1/show/script/stage_direction_styles'));
      if (response.ok) {
        stageDirectionStyles.value =
          ((await response.json()).stage_direction_styles as StageDirectionStyle[]) ?? [];
      }
    } catch (e) {
      log.error('Failed to load stage direction styles:', e);
    }
    await userStore.getStageDirectionStyleOverrides();
  }
});

function openNewOverrideModal(): void {
  const style = stageDirectionStyles.value.find((s) => s.id === newStyleFormState.value.styleId);
  if (!style) {
    log.error('Could not find style to override!');
    return;
  }
  newStyleFormState.value.styleOptions = [
    { caption: 'Bold', state: (style as Record<string, unknown>).bold as boolean },
    { caption: 'Italic', state: (style as Record<string, unknown>).italic as boolean },
    { caption: 'Underline', state: (style as Record<string, unknown>).underline as boolean },
  ];
  newStyleFormState.value.textFormat = (style as Record<string, unknown>).text_format as string;
  newStyleFormState.value.textColour = (style as Record<string, unknown>).text_colour as string;
  newStyleFormState.value.enableBackgroundColour = (style as Record<string, unknown>)
    .enable_background_colour as boolean;
  newStyleFormState.value.backgroundColour = (style as Record<string, unknown>)
    .background_colour as string;
  selectModal.value?.hide();
  newModal.value?.show();
}

function resetNewFormState(): void {
  newStyleFormState.value = {
    styleId: null,
    styleOptions: defaultStyleOptions(),
    textFormat: 'default',
    textColour: '#FFFFFF',
    enableBackgroundColour: false,
    backgroundColour: '#000000',
  };
  isSubmittingNew.value = false;
  vNew$.value.$reset();
}

function resetEditFormState(): void {
  editStyleFormState.value = {
    id: null,
    styleId: null,
    styleOptions: defaultStyleOptions(),
    textFormat: 'default',
    textColour: '#FFFFFF',
    enableBackgroundColour: false,
    backgroundColour: '#000000',
  };
  isSubmittingEdit.value = false;
  vEdit$.value.$reset();
}

async function onSubmitNewOverride(): Promise<void> {
  const valid = await vNew$.value.$validate();
  if (!valid || isSubmittingNew.value) return;

  isSubmittingNew.value = true;
  try {
    await userStore.addStageDirectionStyleOverride({
      styleId: newStyleFormState.value.styleId,
      bold: newStyleFormState.value.styleOptions.find((o) => o.caption === 'Bold')!.state,
      italic: newStyleFormState.value.styleOptions.find((o) => o.caption === 'Italic')!.state,
      underline: newStyleFormState.value.styleOptions.find((o) => o.caption === 'Underline')!.state,
      textFormat: newStyleFormState.value.textFormat,
      textColour: newStyleFormState.value.textColour,
      enableBackgroundColour: newStyleFormState.value.enableBackgroundColour,
      backgroundColour: newStyleFormState.value.backgroundColour,
    });
    newModal.value?.hide();
    resetNewFormState();
  } catch (e) {
    log.error('Error adding stage direction style override:', e);
  } finally {
    isSubmittingNew.value = false;
  }
}

async function onSubmitEditOverride(): Promise<void> {
  const valid = await vEdit$.value.$validate();
  if (!valid || isSubmittingEdit.value) return;

  isSubmittingEdit.value = true;
  try {
    await userStore.updateStageDirectionStyleOverride({
      id: editStyleFormState.value.id,
      bold: editStyleFormState.value.styleOptions.find((o) => o.caption === 'Bold')!.state,
      italic: editStyleFormState.value.styleOptions.find((o) => o.caption === 'Italic')!.state,
      underline: editStyleFormState.value.styleOptions.find((o) => o.caption === 'Underline')!
        .state,
      text_format: editStyleFormState.value.textFormat,
      text_colour: editStyleFormState.value.textColour,
      enable_background_colour: editStyleFormState.value.enableBackgroundColour,
      background_colour: editStyleFormState.value.backgroundColour,
    });
    editModal.value?.hide();
    resetEditFormState();
  } catch (e) {
    log.error('Error updating stage direction style override:', e);
  } finally {
    isSubmittingEdit.value = false;
  }
}

function openEditStyleForm(data: {
  item: { id: number; settings: Record<string, unknown> };
}): void {
  const { settings, id } = data.item;
  editStyleFormState.value = {
    id,
    styleId: settings.id as number,
    styleOptions: [
      { caption: 'Bold', state: settings.bold as boolean },
      { caption: 'Italic', state: settings.italic as boolean },
      { caption: 'Underline', state: settings.underline as boolean },
    ],
    textFormat: settings.text_format as string,
    textColour: settings.text_colour as string,
    enableBackgroundColour: settings.enable_background_colour as boolean,
    backgroundColour: settings.background_colour as string,
  };
  editModal.value?.show();
}

function openDeleteConfirm(id: number): void {
  pendingDeleteId.value = id;
  deleteModal.value?.show();
}

async function confirmDelete(): Promise<void> {
  if (pendingDeleteId.value == null || isDeleting.value) return;
  isDeleting.value = true;
  try {
    await userStore.deleteStageDirectionStyleOverride(pendingDeleteId.value);
  } catch (e) {
    log.error('Error deleting stage direction style override:', e);
  } finally {
    isDeleting.value = false;
    pendingDeleteId.value = null;
  }
}
</script>

<style scoped>
.example-stage-direction {
  font-size: 14px;
}
</style>
