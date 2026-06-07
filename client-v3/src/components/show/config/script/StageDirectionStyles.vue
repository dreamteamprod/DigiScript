<template>
  <BContainer class="mx-0" fluid>
    <BRow>
      <BCol>
        <BTable
          :items="scriptStore.stageDirectionStyles"
          :fields="columns"
          :per-page="perPage"
          :current-page="currentPage"
          show-empty
        >
          <template #head(btn)>
            <div class="d-flex gap-2">
              <BButton
                v-if="systemStore.isScriptEditor"
                variant="outline-success"
                @click="newModal?.show()"
              >
                New Style
              </BButton>
              <BButton
                v-if="systemStore.isScriptEditor"
                variant="outline-info"
                @click="openImportModal"
              >
                Import Style
              </BButton>
            </div>
          </template>
          <template #cell(example)="data">
            <i class="example-stage-direction" :style="exampleCss(data.item)">
              {{ formatExampleText(data.item) }}
            </i>
          </template>
          <template #cell(btn)="data">
            <BButtonGroup v-if="systemStore.isScriptEditor">
              <BButton
                variant="warning"
                size="sm"
                :disabled="isSubmittingEdit || isDeleting"
                @click="openEditForm(data.item)"
              >
                Edit
              </BButton>
              <BButton
                variant="danger"
                size="sm"
                :disabled="isSubmittingEdit || isDeleting"
                @click="deleteStyle(data.item)"
              >
                Delete
              </BButton>
            </BButtonGroup>
          </template>
        </BTable>
        <PaginationControls
          v-model:per-page="perPage"
          v-model:current-page="currentPage"
          :total-rows="scriptStore.stageDirectionStyles.length"
        />
      </BCol>
    </BRow>

    <!-- New Style Modal -->
    <BModal
      ref="newModal"
      title="Add New Style"
      size="lg"
      :ok-disabled="isSubmittingNew"
      @show="resetNewForm"
      @hidden="resetNewForm"
      @ok.prevent="onSubmitNew"
    >
      <StyleForm v-model="newForm" />
    </BModal>

    <!-- Edit Style Modal -->
    <BModal
      ref="editModal"
      title="Edit Style"
      size="lg"
      :ok-disabled="isSubmittingEdit"
      @hidden="resetEditForm"
      @ok.prevent="onSubmitEdit"
    >
      <StyleForm v-model="editForm" />
    </BModal>

    <!-- Import Modal -->
    <BModal
      ref="importModal"
      title="Import Stage Direction Style"
      size="xl"
      ok-only
      ok-title="Close"
      @hidden="resetImportState"
    >
      <div v-if="isLoadingImport" class="text-center py-3">
        <BSpinner />
      </div>
      <div v-else-if="importStyleGroups.length === 0" class="text-muted text-center py-3">
        No styles available to import from other shows.
      </div>
      <div v-else>
        <BCard v-for="show in importStyleGroups" :key="show.id" no-body class="mb-2">
          <BCardHeader class="section-card-header" role="button" @click="toggleImportShow(show.id)">
            <div class="d-flex justify-content-between align-items-center">
              <span>{{ show.name }}</span>
              <IMdiChevronUp v-if="styleGroupExpanded[show.id]" /><IMdiChevronDown v-else />
            </div>
          </BCardHeader>
          <BCollapse :model-value="styleGroupExpanded[show.id]">
            <BCardBody class="p-0">
              <BTable :items="show.styles" :fields="importColumns" small show-empty class="mb-0">
                <template #cell(example)="row">
                  <i class="example-stage-direction" :style="exampleCss(row.item)">
                    {{ formatExampleText(row.item) }}
                  </i>
                </template>
                <template #cell(btn)="row">
                  <BButton
                    variant="outline-success"
                    size="sm"
                    :disabled="!!isImporting[row.item.id]"
                    @click="importStyle(row.item)"
                  >
                    <BSpinner v-if="isImporting[row.item.id]" small />
                    <span v-else>Import</span>
                  </BButton>
                </template>
              </BTable>
            </BCardBody>
          </BCollapse>
        </BCard>
      </div>
    </BModal>
  </BContainer>
</template>

<script setup lang="ts">
import { ref, onMounted, defineComponent, h } from 'vue';
import type { BModal } from 'bootstrap-vue-next';
import { useVuelidate } from '@vuelidate/core';
import { required } from '@vuelidate/validators';
import log from 'loglevel';
import { useScriptStore } from '@/stores/script';
import { useSystemStore } from '@/stores/system';
import { useConfirm } from '@/composables/useConfirm';
import { usePagination } from '@/composables/usePagination';
import { useFormValidation } from '@/composables/useFormValidation';
import type { StageDirectionStyle } from '@/types/api/script';
import { toast } from '@/js/toast';

const scriptStore = useScriptStore();
const systemStore = useSystemStore();
const { confirm } = useConfirm();
const { validationState } = useFormValidation();

const { perPage, currentPage } = usePagination();
const isSubmittingNew = ref(false);
const isSubmittingEdit = ref(false);
const isDeleting = ref(false);
const importStyleGroups = ref<any[]>([]);
const styleGroupExpanded = ref<Record<number, boolean>>({});
const isLoadingImport = ref(false);
const isImporting = ref<Record<number, boolean>>({});

const newModal = ref<InstanceType<typeof BModal>>();
const editModal = ref<InstanceType<typeof BModal>>();
const importModal = ref<InstanceType<typeof BModal>>();

interface StyleForm {
  id?: number | null;
  description: string;
  bold: boolean;
  italic: boolean;
  underline: boolean;
  textFormat: string;
  textColour: string;
  enableBackgroundColour: boolean;
  backgroundColour: string;
}

function defaultStyleForm(): StyleForm {
  return {
    description: '',
    bold: false,
    italic: false,
    underline: false,
    textFormat: 'default',
    textColour: '#FFFFFF',
    enableBackgroundColour: false,
    backgroundColour: '#000000',
  };
}

const newForm = ref<StyleForm>(defaultStyleForm());
const editForm = ref<StyleForm>({ ...defaultStyleForm(), id: null });

const vNew$ = useVuelidate({ description: { required } }, newForm);
const vEdit$ = useVuelidate({ description: { required } }, editForm);

const columns = [
  { key: 'description', label: 'Description' },
  { key: 'example', label: 'Example Stage Direction' },
  { key: 'btn', label: '' },
];

const importColumns = [
  { key: 'description', label: 'Description' },
  { key: 'example', label: 'Example Stage Direction' },
  { key: 'btn', label: '' },
];

const exampleText = 'Your stage direction will look like this when formatted in the script!';

function formatExampleText(item: any): string {
  if (item.text_format === 'upper') return exampleText.toUpperCase();
  if (item.text_format === 'lower') return exampleText.toLowerCase();
  return exampleText;
}

function exampleCss(item: any): Record<string, string> {
  const style: Record<string, string> = {
    'font-weight': item.bold ? 'bold' : 'normal',
    'font-style': item.italic ? 'italic' : 'normal',
    'text-decoration-line': item.underline ? 'underline' : 'none',
    color: item.text_colour ?? '',
  };
  if (item.enable_background_colour) style['background-color'] = item.background_colour ?? '';
  return style;
}

function formExampleCss(form: StyleForm): Record<string, string> {
  const style: Record<string, string> = {
    'font-weight': form.bold ? 'bold' : 'normal',
    'font-style': form.italic ? 'italic' : 'normal',
    'text-decoration-line': form.underline ? 'underline' : 'none',
    color: form.textColour,
  };
  if (form.enableBackgroundColour) style['background-color'] = form.backgroundColour;
  return style;
}

function styleToPayload(form: StyleForm): Record<string, unknown> {
  return {
    ...(form.id == null ? {} : { id: form.id }),
    description: form.description,
    bold: form.bold,
    italic: form.italic,
    underline: form.underline,
    textFormat: form.textFormat,
    textColour: form.textColour,
    enableBackgroundColour: form.enableBackgroundColour,
    backgroundColour: form.backgroundColour,
  };
}

function resetNewForm(): void {
  newForm.value = defaultStyleForm();
  isSubmittingNew.value = false;
  vNew$.value.$reset();
}

function resetEditForm(): void {
  editForm.value = { ...defaultStyleForm(), id: null };
  isSubmittingEdit.value = false;
  vEdit$.value.$reset();
}

async function onSubmitNew(): Promise<void> {
  const valid = await vNew$.value.$validate();
  if (!valid || isSubmittingNew.value) return;
  isSubmittingNew.value = true;
  try {
    await scriptStore.addStageDirectionStyle(
      styleToPayload(newForm.value) as Partial<StageDirectionStyle>
    );
    newModal.value?.hide();
  } catch (e) {
    log.error('Error adding stage direction style:', e);
  } finally {
    isSubmittingNew.value = false;
  }
}

async function onSubmitEdit(): Promise<void> {
  const valid = await vEdit$.value.$validate();
  if (!valid || isSubmittingEdit.value) return;
  isSubmittingEdit.value = true;
  try {
    await scriptStore.updateStageDirectionStyle(
      styleToPayload(editForm.value) as Partial<StageDirectionStyle>
    );
    editModal.value?.hide();
  } catch (e) {
    log.error('Error updating stage direction style:', e);
  } finally {
    isSubmittingEdit.value = false;
  }
}

function openEditForm(item: StageDirectionStyle): void {
  editForm.value = {
    id: item.id,
    description: item.description ?? '',
    bold: item.bold ?? false,
    italic: item.italic ?? false,
    underline: item.underline ?? false,
    textFormat: item.text_format ?? 'default',
    textColour: item.text_colour ?? '#FFFFFF',
    enableBackgroundColour: item.enable_background_colour ?? false,
    backgroundColour: item.background_colour ?? '#000000',
  };
  editModal.value?.show();
}

async function deleteStyle(item: StageDirectionStyle): Promise<void> {
  if (isDeleting.value) return;
  const ok = await confirm(`Are you sure you want to delete "${item.description}"?`, {
    okVariant: 'danger',
    okTitle: 'Delete',
  });
  if (!ok) return;
  isDeleting.value = true;
  try {
    await scriptStore.deleteStageDirectionStyle(item.id);
  } catch (e) {
    log.error('Error deleting stage direction style:', e);
  } finally {
    isDeleting.value = false;
  }
}

async function openImportModal(): Promise<void> {
  importModal.value?.show();
  isLoadingImport.value = true;
  try {
    const data = (await scriptStore.getImportableStyles()) as any;
    importStyleGroups.value = data.style_groups ?? [];
    const expanded: Record<number, boolean> = {};
    importStyleGroups.value.forEach((group: any) => {
      expanded[group.id] = true;
    });
    styleGroupExpanded.value = expanded;
  } catch (e) {
    log.error('Error fetching importable styles:', e);
    toast.error('Failed to load styles for import');
  } finally {
    isLoadingImport.value = false;
  }
}

function resetImportState(): void {
  importStyleGroups.value = [];
  styleGroupExpanded.value = {};
  isLoadingImport.value = false;
  isImporting.value = {};
}

function toggleImportShow(showId: number): void {
  styleGroupExpanded.value[showId] = !styleGroupExpanded.value[showId];
}

async function importStyle(item: any): Promise<void> {
  isImporting.value[item.id] = true;
  try {
    await scriptStore.addStageDirectionStyle({
      description: item.description,
      bold: item.bold,
      italic: item.italic,
      underline: item.underline,
      text_format: item.text_format,
      text_colour: item.text_colour,
      enable_background_colour: item.enable_background_colour,
      background_colour: item.background_colour,
    });
    toast.success(`Imported "${item.description}"`);
  } catch (e) {
    log.error('Error importing style:', e);
    toast.error(`Failed to import "${item.description}"`);
  } finally {
    isImporting.value[item.id] = false;
  }
}

// Inline style form sub-component using native Bootstrap HTML to avoid component import complexity
const StyleForm = defineComponent({
  props: { modelValue: { type: Object, required: true } },
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    function update(field: string, value: unknown) {
      emit('update:modelValue', { ...props.modelValue, [field]: value });
    }
    return () => {
      const form = props.modelValue as StyleForm;
      const previewStyle = formExampleCss(form);
      const previewText = formatExampleText({
        text_format: form.textFormat,
        bold: form.bold,
        italic: form.italic,
        underline: form.underline,
        text_colour: form.textColour,
        enable_background_colour: form.enableBackgroundColour,
        background_colour: form.backgroundColour,
      });
      return h('div', [
        h('div', { class: 'mb-3' }, [
          h('h4', 'Example Stage Direction'),
          h('i', { class: 'example-stage-direction', style: previewStyle }, previewText),
        ]),
        h('div', { class: 'mb-3' }, [
          h('label', { class: 'form-label' }, 'Description'),
          h('input', {
            class: 'form-control',
            type: 'text',
            value: form.description,
            onInput: (e: Event) => update('description', (e.target as HTMLInputElement).value),
          }),
        ]),
        h('div', { class: 'mb-3' }, [
          h('label', { class: 'form-label d-block' }, 'Default Styles'),
          h('div', { class: 'btn-group' }, [
            h(
              'button',
              {
                class: ['btn', form.bold ? 'btn-primary' : 'btn-outline-primary'],
                type: 'button',
                onClick: () => update('bold', !form.bold),
              },
              'Bold'
            ),
            h(
              'button',
              {
                class: ['btn', form.italic ? 'btn-primary' : 'btn-outline-primary'],
                type: 'button',
                onClick: () => update('italic', !form.italic),
              },
              'Italic'
            ),
            h(
              'button',
              {
                class: ['btn', form.underline ? 'btn-primary' : 'btn-outline-primary'],
                type: 'button',
                onClick: () => update('underline', !form.underline),
              },
              'Underline'
            ),
          ]),
        ]),
        h('div', { class: 'mb-3' }, [
          h('label', { class: 'form-label' }, 'Default Text Format'),
          h(
            'select',
            {
              class: 'form-select',
              value: form.textFormat,
              onChange: (e: Event) => update('textFormat', (e.target as HTMLSelectElement).value),
            },
            [
              h('option', { value: 'default' }, 'Default'),
              h('option', { value: 'upper' }, 'Uppercase'),
              h('option', { value: 'lower' }, 'Lowercase'),
            ]
          ),
        ]),
        h('div', { class: 'mb-3' }, [
          h('label', { class: 'form-label' }, 'Text Colour'),
          h('input', {
            class: 'form-control form-control-color',
            type: 'color',
            value: form.textColour,
            onInput: (e: Event) => update('textColour', (e.target as HTMLInputElement).value),
          }),
        ]),
        h('div', { class: 'mb-3 form-check form-switch' }, [
          h('input', {
            class: 'form-check-input',
            type: 'checkbox',
            id: 'style-bg-enable',
            checked: form.enableBackgroundColour,
            onChange: (e: Event) =>
              update('enableBackgroundColour', (e.target as HTMLInputElement).checked),
          }),
          h(
            'label',
            { class: 'form-check-label', for: 'style-bg-enable' },
            'Enable Background Colour'
          ),
        ]),
        form.enableBackgroundColour
          ? h('div', { class: 'mb-3' }, [
              h('label', { class: 'form-label' }, 'Background Colour'),
              h('input', {
                class: 'form-control form-control-color',
                type: 'color',
                value: form.backgroundColour,
                onInput: (e: Event) =>
                  update('backgroundColour', (e.target as HTMLInputElement).value),
              }),
            ])
          : null,
      ]);
    };
  },
});

onMounted(async () => {
  await scriptStore.getStageDirectionStyles();
});
</script>

<style scoped>
.example-stage-direction {
  padding: 0.25rem 0.5rem;
  display: inline-block;
}
</style>
