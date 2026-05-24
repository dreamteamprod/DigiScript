<template>
  <BContainer fluid class="mx-0">
    <BRow>
      <BCol>
        <template v-if="loaded">
          <BForm @submit.prevent="handleSubmit" @reset.prevent="resetForm">
            <BCard
              v-for="(settings, category) in settingsByCategory"
              :key="`settings-${category}`"
              no-body
              class="mt-2"
            >
              <BCardHeader class="cursor-pointer" @click="toggleCategory(String(category))">
                <div class="d-flex justify-content-between align-items-center">
                  <span>
                    {{ category }}
                    <BBadge variant="success" class="ms-1">
                      {{ Object.keys(settings).length - (dirtyByCategory[String(category)] ?? 0) }}
                    </BBadge>
                    <BBadge
                      v-if="(dirtyByCategory[String(category)] ?? 0) > 0"
                      variant="warning"
                      class="ms-1"
                    >
                      {{ dirtyByCategory[String(category)] }}
                    </BBadge>
                  </span>
                  <IMdiChevronUp v-if="expandedState[String(category)]" /><IMdiChevronDown v-else />
                </div>
              </BCardHeader>
              <BCollapse
                :model-value="expandedState[String(category)]"
                @update:model-value="(val) => (expandedState[String(category)] = val)"
              >
                <BCardBody>
                  <BFormGroup
                    v-for="(setting, key) in settings"
                    :id="`${key}-input-group`"
                    :key="key"
                    :label-for="`${key}-input`"
                    label-cols="4"
                  >
                    <template #label>
                      <span>
                        {{ setting.display_name !== '' ? setting.display_name : key }}
                        <span
                          v-if="setting.help_text !== ''"
                          :id="`${key}-help-icon`"
                          class="text-muted ms-1"
                          style="cursor: help"
                          :title="setting.help_text"
                          >?</span
                        >
                      </span>
                    </template>
                    <BFormSelect
                      v-if="setting.choice_options != null"
                      :id="`${key}-input`"
                      v-model="editSettings[String(key)]"
                      :name="`${key}-input`"
                      :options="getChoiceOptions(setting)"
                      :state="fieldState(String(key))"
                      :disabled="!setting.can_edit"
                    />
                    <BFormInput
                      v-else-if="setting.type !== 'bool'"
                      :id="`${key}-input`"
                      v-model="editSettings[String(key)]"
                      :name="`${key}-input`"
                      :type="inputType(setting.type)"
                      :state="fieldState(String(key))"
                      :readonly="!setting.can_edit"
                    />
                    <BFormCheckbox
                      v-else
                      :id="`${key}-input`"
                      v-model="editSettings[String(key)]"
                      :name="`${key}-input`"
                      :disabled="!setting.can_edit"
                      switch
                    />
                  </BFormGroup>
                </BCardBody>
              </BCollapse>
            </BCard>
            <BButtonGroup size="md" style="float: right; padding-top: 1rem; padding-bottom: 0.5rem">
              <BButton type="reset" variant="danger" :disabled="!hasChanges">Reset</BButton>
              <BButton type="submit" variant="primary" :disabled="!hasChanges">Submit</BButton>
            </BButtonGroup>
          </BForm>
        </template>
        <div v-else class="text-center">
          <BSpinner style="width: 10rem; height: 10rem" variant="info" />
        </div>
      </BCol>
    </BRow>
  </BContainer>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue';
import { useVuelidate } from '@vuelidate/core';
import { required, integer } from '@vuelidate/validators';
import { storeToRefs } from 'pinia';
import log from 'loglevel';
import { makeURL } from '@/js/utils';
import { useSystemStore } from '@/stores/system';
import { toast } from '@/js/toast';

const systemStore = useSystemStore();
const { rawSettings, settingsCategories } = storeToRefs(systemStore);

const loaded = ref(false);
const editSettings = ref<Record<string, unknown>>({});
const expandedState = ref<Record<string, boolean>>({ General: true });

const visibleSettings = computed(() => {
  const result: Record<string, any> = {};
  for (const [key, setting] of Object.entries(rawSettings.value)) {
    if (!(setting as any).hide_from_ui) result[key] = setting;
  }
  return result;
});

const settingsByCategory = computed(() => {
  const result: Record<string, Record<string, any>> = {};
  for (const [category, keys] of Object.entries(settingsCategories.value)) {
    result[category] = {};
    for (const key of keys as string[]) {
      if (key in visibleSettings.value) result[category][key] = visibleSettings.value[key];
    }
  }
  return result;
});

const hasChanges = computed(() =>
  Object.keys(editSettings.value).some(
    (key) => editSettings.value[key] !== (rawSettings.value[key] as any)?.value
  )
);

const rules = computed(() => {
  const r: Record<string, any> = {};
  for (const key of Object.keys(editSettings.value)) {
    r[key] = (rawSettings.value[key] as any)?.type === 'int' ? { required, integer } : {};
  }
  return { editSettings: r };
});

const v$ = useVuelidate(rules, { editSettings });

const dirtyByCategory = computed(() => {
  const dirty: Record<string, number> = {};
  for (const [category, keys] of Object.entries(settingsCategories.value)) {
    dirty[category] = 0;
    for (const key of keys as string[]) {
      if (key in visibleSettings.value && v$.value.editSettings?.[key]?.$dirty) {
        dirty[category]++;
      }
    }
  }
  return dirty;
});

function fieldState(key: string): boolean | null {
  const field = v$.value.editSettings?.[key];
  if (!field) return null;
  return field.$dirty ? !field.$error : null;
}

function inputType(fieldType: string): string {
  return fieldType === 'int' ? 'number' : 'text';
}

function getChoiceOptions(setting: any): Array<{ value: unknown; text: string }> {
  const options: Array<{ value: unknown; text: string }> = [];
  if (setting._nullable) options.push({ value: null, text: 'N/A' });
  setting.choice_options.forEach((opt: unknown) => options.push({ value: opt, text: String(opt) }));
  return options;
}

function toggleCategory(category: string): void {
  expandedState.value[category] = !expandedState.value[category];
}

function resetEditSettings(): void {
  for (const [key, setting] of Object.entries(visibleSettings.value)) {
    editSettings.value[key] = (setting as any).value;
  }
}

function resetForm(): void {
  loaded.value = false;
  resetEditSettings();
  v$.value.$reset();
  loaded.value = true;
}

watch(rawSettings, () => {
  loaded.value = false;
  resetEditSettings();
  v$.value.$reset();
  loaded.value = true;
});

onMounted(async () => {
  await systemStore.getSettingsCategories();
  resetEditSettings();
  loaded.value = true;
});

async function handleSubmit(): Promise<void> {
  const valid = await v$.value.$validate();
  if (!valid) return;

  const response = await fetch(makeURL('/api/v1/settings'), {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(editSettings.value),
  });
  if (response.ok) {
    toast.success('Saved settings');
    v$.value.$reset();
  } else {
    log.error('Unable to save settings');
    toast.error('Unable to save settings');
  }
}
</script>

<style scoped>
.cursor-pointer {
  cursor: pointer;
}
</style>
