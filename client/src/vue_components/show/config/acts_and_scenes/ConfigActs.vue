<template>
  <span v-if="!loading">
    <b-table
      id="acts-table"
      :items="actTableItems"
      :fields="actFields"
      :per-page="rowsPerPage"
      :current-page="currentPage"
      show-empty
    >
      <template #head(btn)="data">
        <b-button v-if="IS_SHOW_EDITOR" v-b-modal.new-act variant="outline-success">
          New Act
        </b-button>
      </template>
      <template #cell(interval_after)="data">
        <b-icon-check-square-fill v-if="data.item.interval_after" variant="success" />
        <b-icon-x-square-fill v-else variant="danger" />
      </template>
      <template #cell(next_act)="data">
        <p v-if="data.item.next_act">
          {{ ACT_BY_ID(data.item.next_act).name }}
        </p>
        <p v-else>N/A</p>
      </template>
      <template #cell(previous_act)="data">
        <p v-if="data.item.previous_act">
          {{ ACT_BY_ID(data.item.previous_act).name }}
        </p>
        <p v-else>N/A</p>
      </template>
      <template #cell(btn)="data">
        <b-button-group v-if="IS_SHOW_EDITOR">
          <b-button
            variant="warning"
            :disabled="submittingEditAct || deletingAct"
            @click="openEditForm(data)"
          >
            Edit
          </b-button>
          <b-button
            variant="danger"
            :disabled="submittingEditAct || deletingAct"
            @click="deleteAct(data)"
          >
            Delete
          </b-button>
        </b-button-group>
      </template>
    </b-table>
    <b-pagination
      v-show="actTableItems.length > rowsPerPage"
      v-model="currentPage"
      :total-rows="actTableItems.length"
      :per-page="rowsPerPage"
      aria-controls="acts-table"
      class="justify-content-center"
    />
    <b-modal
      id="new-act"
      ref="new-act"
      title="Add New Act"
      size="md"
      :ok-disabled="$v.newFormState.$invalid || submittingNewAct"
      @show="resetNewForm"
      @hidden="resetNewForm"
      @ok="onSubmitNew"
    >
      <b-form ref="new-act-form" @submit.stop.prevent="onSubmitNew">
        <b-form-group id="new-name-input-group" label="Name" label-for="new-name-input">
          <b-form-input
            id="new-name-input"
            v-model="$v.newFormState.name.$model"
            name="new-name-input"
            :state="getValidationState('newFormState', 'name')"
            aria-describedby="new-name-feedback"
          />
          <b-form-invalid-feedback id="new-name-feedback">
            This is a required field.
          </b-form-invalid-feedback>
        </b-form-group>
        <b-form-group
          id="new-interval-input-group"
          label="Interval After"
          label-for="new-interval-input"
        >
          <b-form-checkbox
            id="new-interval-input"
            v-model="newFormState.interval_after"
            name="new-interval-input"
          />
        </b-form-group>
        <b-form-group
          id="new-previous-act-input-group"
          label="Previous Act"
          label-for="new-previous-act-input"
        >
          <b-form-select
            id="new-previous-act-input"
            v-model="newFormState.previous_act_id"
            :options="previousActOptions"
            aria-describedby="new-previous-act-feedback"
          />
        </b-form-group>
      </b-form>
    </b-modal>
    <b-modal
      id="edit-act"
      ref="edit-act"
      title="Edit Act"
      size="md"
      :ok-disabled="$v.editFormState.$invalid || submittingEditAct"
      @hidden="resetEditForm"
      @ok="onSubmitEdit"
    >
      <b-form ref="edit-act-form" @submit.stop.prevent="onSubmitEdit">
        <b-form-group id="edit-name-input-group" label="Name" label-for="edit-name-input">
          <b-form-input
            id="edit-name-input"
            v-model="$v.editFormState.name.$model"
            name="edit-name-input"
            :state="getValidationState('editFormState', 'name')"
            aria-describedby="edit-name-feedback"
          />
          <b-form-invalid-feedback id="edit-name-feedback">
            This is a required field.
          </b-form-invalid-feedback>
        </b-form-group>
        <b-form-group
          id="edit-interval-input-group"
          label="Interval After"
          label-for="edit-interval-input"
        >
          <b-form-checkbox
            id="edit-interval-input"
            v-model="editFormState.interval_after"
            name="edit-interval-input"
          />
        </b-form-group>
        <b-form-group
          id="edit-previous-act-input-group"
          label="Previous Act"
          label-for="edit-previous-act-input"
        >
          <b-form-select
            id="edit-previous-act-input"
            v-model="$v.editFormState.previous_act_id.$model"
            :options="editFormActOptions"
            :state="getValidationState('editFormState', 'previous_act_id')"
            aria-describedby="edit-previous-act-feedback"
          />
          <b-form-invalid-feedback id="edit-previous-act-feedback">
            This cannot form a circular dependency between acts.
          </b-form-invalid-feedback>
        </b-form-group>
      </b-form>
    </b-modal>
  </span>
  <div v-else class="text-center py-5">
    <b-spinner label="Loading" />
  </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import { required, integer } from 'vuelidate/lib/validators';
import { mapGetters, mapActions } from 'vuex';
import log from 'loglevel';
import formValidationMixin from '@/mixins/formValidationMixin';

export default defineComponent({
  name: 'ConfigActs',
  mixins: [formValidationMixin],
  data() {
    return {
      loading: true,
      rowsPerPage: 15,
      currentPage: 1,
      actFields: [
        'name',
        { key: 'interval_after', label: 'Interval After' },
        { key: 'previous_act', label: 'Previous Act' },
        { key: 'next_act', label: 'Next Act' },
        { key: 'btn', label: '' },
      ],
      newFormState: {
        name: '',
        interval_after: false,
        previous_act_id: null as number | null,
      },
      editFormState: {
        id: null as number | null,
        showID: null as number | null,
        name: '',
        interval_after: false,
        previous_act_id: null as number | null,
      },
      submittingNewAct: false,
      submittingEditAct: false,
      deletingAct: false,
    };
  },
  validations: {
    newFormState: {
      name: { required },
    },
    editFormState: {
      name: { required },
      previous_act_id: {
        integer,
        noLoops(value) {
          const actIndexes = [this.editFormState.id];
          let currentAct = this.ACT_BY_ID(value);
          while (currentAct != null && currentAct.previous_act != null) {
            if (actIndexes.includes(currentAct.previous_act)) {
              return false;
            }
            currentAct = this.ACT_BY_ID(currentAct.previous_act);
          }
          return true;
        },
      },
    },
  },
  computed: {
    actTableItems(): unknown[] {
      const ret: any[] = [];
      if ((this as any).CURRENT_SHOW.first_act_id != null && (this as any).ACT_LIST.length > 0) {
        let act = (this as any).ACT_BY_ID((this as any).CURRENT_SHOW.first_act_id);
        while (act != null) {
          ret.push((this as any).ACT_BY_ID(act.id));
          act = (this as any).ACT_BY_ID(act.next_act);
        }
      }
      const actIds = ret.map((x) => x.id);
      (this as any).ACT_LIST.forEach((act: any) => {
        if (!actIds.includes(act.id)) {
          ret.push(act);
        }
      });
      return ret;
    },
    previousActOptions(): unknown[] {
      return [
        { value: null, text: 'None', disabled: false },
        ...(this as any).ACT_LIST.filter((act: any) => act.next_act == null).map((act: any) => ({
          value: act.id,
          text: act.name,
        })),
      ];
    },
    editFormActOptions(): unknown[] {
      const ret: any[] = [];
      ret.push(
        ...(this.previousActOptions as any[]).filter((act) => act.value !== this.editFormState.id)
      );
      if (this.editFormState.previous_act_id != null) {
        const act = (this as any).ACT_LIST.find(
          (a: any) => a.id === this.editFormState.previous_act_id
        );
        ret.push({
          value: this.editFormState.previous_act_id,
          text: act.name,
          disabled: false,
        });
      }
      return ret;
    },
    ...mapGetters(['ACT_LIST', 'CURRENT_SHOW', 'ACT_BY_ID', 'IS_SHOW_EDITOR']),
  },
  async mounted(): Promise<void> {
    await (this as any).GET_ACT_LIST();
    this.loading = false;
  },
  methods: {
    resetNewForm(): void {
      (this as any).resetForm('newFormState', {
        name: '',
        interval_after: false,
        previous_act_id: null,
      });
      this.submittingNewAct = false;
    },
    async onSubmitNew(event: Event): Promise<void> {
      (this as any).$v.newFormState.$touch();
      if ((this as any).$v.newFormState.$anyError || this.submittingNewAct) {
        event.preventDefault();
        return;
      }
      this.submittingNewAct = true;
      try {
        await (this as any).ADD_ACT(this.newFormState);
        (this as any).$bvModal.hide('new-act');
        this.resetNewForm();
      } catch (error) {
        log.error('Error submitting new act:', error);
        event.preventDefault();
      } finally {
        this.submittingNewAct = false;
      }
    },
    openEditForm(act: any): void {
      if (act != null) {
        this.editFormState.id = act.item.id;
        this.editFormState.showID = act.item.show_id;
        this.editFormState.name = act.item.name;
        this.editFormState.interval_after = act.item.interval_after;
        if (act.item.previous_act != null) {
          this.editFormState.previous_act_id = act.item.previous_act;
        }
        (this as any).$bvModal.show('edit-act');
      }
    },
    resetEditForm(): void {
      (this as any).resetForm('editFormState', {
        id: null,
        showID: null,
        name: '',
        interval_after: false,
        previous_act_id: null,
      });
      this.submittingEditAct = false;
      this.deletingAct = false;
    },
    async onSubmitEdit(event: Event): Promise<void> {
      (this as any).$v.editFormState.$touch();
      if ((this as any).$v.editFormState.$anyError || this.submittingEditAct) {
        event.preventDefault();
        return;
      }
      this.submittingEditAct = true;
      try {
        await (this as any).UPDATE_ACT(this.editFormState);
        (this as any).$bvModal.hide('edit-act');
        this.resetEditForm();
      } catch (error) {
        log.error('Error submitting edit act:', error);
        event.preventDefault();
      } finally {
        this.submittingEditAct = false;
      }
    },
    async deleteAct(act: any): Promise<void> {
      if (this.deletingAct) {
        return;
      }
      const msg = `Are you sure you want to delete ${act.item.name}?`;
      const action = await (this as any).$bvModal.msgBoxConfirm(msg, {});
      if (action === true) {
        this.deletingAct = true;
        try {
          await (this as any).DELETE_ACT(act.item.id);
        } catch (error) {
          log.error('Error deleting act:', error);
        } finally {
          this.deletingAct = false;
        }
      }
    },
    ...mapActions(['GET_ACT_LIST', 'ADD_ACT', 'DELETE_ACT', 'UPDATE_ACT']),
  },
});
</script>

<style scoped></style>
