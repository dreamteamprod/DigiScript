<template>
  <b-container id="show-config" class="mx-0" fluid>
    <b-row>
      <b-col cols="12" class="text-right">
        <b-button
          v-if="IS_SHOW_EDITOR"
          variant="warning"
          :disabled="submittingEditShow"
          @click="openEditForm()"
        >
          Edit Show
        </b-button>
      </b-col>
    </b-row>
    <b-row>
      <b-col>
        <b-table-simple>
          <b-tr v-for="key in orderedKeys" :key="key">
            <b-th>{{ key }}</b-th>
            <b-td>{{ tableData[key] != null ? tableData[key] : 'N/A' }}</b-td>
          </b-tr>
        </b-table-simple>
      </b-col>
    </b-row>
    <b-modal
      id="edit-show"
      ref="edit-show"
      title="Edit Show"
      size="md"
      :ok-disabled="$v.editFormState.$invalid || submittingEditShow"
      @hidden="resetEditForm"
      @ok="onSubmitEdit"
    >
      <b-form ref="edit-show-form" @submit.stop.prevent="onSubmitEdit">
        <b-form-group id="name-input-group" label="Name" label-for="name-input">
          <b-form-input
            id="name-input"
            v-model="$v.editFormState.name.$model"
            name="name-input"
            :state="validateEditState('name')"
            aria-describedby="name-feedback"
          />

          <b-form-invalid-feedback id="name-feedback">
            This is a required field and must be less than 100 characters.
          </b-form-invalid-feedback>
        </b-form-group>

        <b-form-group id="start-input-group" label="Start Date" label-for="start-input">
          <b-form-input
            id="start-input"
            v-model="$v.editFormState.start_date.$model"
            name="start-input"
            type="date"
            :state="validateEditState('start_date')"
            aria-describedby="start-feedback"
          />
          <b-form-invalid-feedback id="start-feedback">
            This is a required field and must be before or the same as the end date.
          </b-form-invalid-feedback>
        </b-form-group>

        <b-form-group id="end-input-group" label="End Date" label-for="end-input">
          <b-form-input
            id="end-input"
            v-model="$v.editFormState.end_date.$model"
            name="end-input"
            type="date"
            :state="validateEditState('end_date')"
            aria-describedby="end-feedback"
          />
          <b-form-invalid-feedback id="end-feedback">
            This is a required field and must be after or the same as the start date.
          </b-form-invalid-feedback>
        </b-form-group>

        <b-form-group id="act-input-group" label="Act" label-for="act-input">
          <b-form-select
            id="act-input"
            v-model="$v.editFormState.first_act_id.$model"
            :options="actOptions"
            :state="validateEditState('first_act_id')"
          />
        </b-form-group>
      </b-form>
    </b-modal>
  </b-container>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import { required, maxLength } from 'vuelidate/lib/validators';
import { mapGetters, mapActions } from 'vuex';
import { titleCase } from '@/js/utils';
import log from 'loglevel';

export default defineComponent({
  name: 'ConfigShow',
  data() {
    return {
      editFormState: {
        name: null as string | null,
        start_date: null as string | null,
        end_date: null as string | null,
        first_act_id: null as number | null,
      },
      submittingEditShow: false,
    };
  },
  computed: {
    tableData(): Record<string, unknown> {
      const data: Record<string, unknown> = {};
      Object.keys((this as any).CURRENT_SHOW).forEach((key) => {
        data[titleCase(key, '_')] = (this as any).CURRENT_SHOW[key];
      });
      return data;
    },
    orderedKeys(): string[] {
      return Object.keys(this.tableData).sort();
    },
    actOptions(): unknown[] {
      return [
        { value: null, text: 'N/A', disabled: false },
        ...(this as any).ACT_LIST.map((act: any) => ({ value: act.id, text: act.name })),
      ];
    },
    ...mapGetters(['CURRENT_SHOW', 'ACT_LIST', 'IS_SHOW_EDITOR']),
  },
  async mounted(): Promise<void> {
    await (this as any).GET_SHOW_DETAILS();
    await (this as any).GET_ACT_LIST();
  },
  validations: {
    editFormState: {
      name: {
        required,
        maxLength: maxLength(100),
      },
      start_date: {
        required,
        beforeEnd: (value, vm) =>
          value == null && vm.end_date != null ? false : new Date(value) <= new Date(vm.end_date),
      },
      end_date: {
        required,
        afterStart: (value, vm) =>
          value == null && vm.start_date != null
            ? false
            : new Date(value) >= new Date(vm.start_date),
      },
      first_act_id: {},
    },
  },
  methods: {
    titleCase,
    ...mapActions(['GET_SHOW_DETAILS', 'GET_ACT_LIST', 'UPDATE_SHOW']),
    resetEditForm(): void {
      this.editFormState = {
        name: null,
        start_date: null,
        end_date: null,
        first_act_id: null,
      };
      this.submittingEditShow = false;
      this.$nextTick(() => {
        (this as any).$v.$reset();
      });
    },
    openEditForm(): void {
      Object.keys(this.editFormState).forEach((key) => {
        (this as any).editFormState[key] = (this as any).CURRENT_SHOW[key];
      });
      (this as any).$bvModal.show('edit-show');
    },
    validateEditState(name: string): boolean | null {
      const { $dirty, $error } = (this as any).$v.editFormState[name];
      return $dirty ? !$error : null;
    },
    async onSubmitEdit(event: Event): Promise<void> {
      (this as any).$v.editFormState.$touch();
      if ((this as any).$v.editFormState.$anyError || this.submittingEditShow) {
        event.preventDefault();
        return;
      }
      this.submittingEditShow = true;
      try {
        await (this as any).UPDATE_SHOW(this.editFormState);
        (this as any).$bvModal.hide('edit-show');
        this.resetEditForm();
      } catch (error) {
        log.error('Error submitting edit show:', error);
        event.preventDefault();
      } finally {
        this.submittingEditShow = false;
      }
    },
  },
});
</script>

<style scoped>
.row {
  margin-top: 0.5em;
  margin-bottom: 0.5em;
}
</style>
