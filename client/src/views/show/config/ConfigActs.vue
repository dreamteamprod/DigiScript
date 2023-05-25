<template>
  <b-container
    class="mx-0"
    fluid
  >
    <b-row>
      <b-col>
        <h5>Act List</h5>
        <b-table
          id="acts-table"
          :items="actTableItems"
          :fields="actFields"
          :per-page="rowsPerPage"
          :current-page="currentPage"
          show-empty
        >
          <template #head(btn)="data">
            <b-button
              v-b-modal.new-act
              variant="outline-success"
            >
              New Act
            </b-button>
          </template>
          <template #cell(interval_after)="data">
            <b-icon-check-square-fill
              v-if="data.item.interval_after"
              variant="success"
            />
            <b-icon-x-square-fill
              v-else
              variant="danger"
            />
          </template>
          <template #cell(next_act)="data">
            <p v-if="data.item.next_act">
              {{ ACT_BY_ID(data.item.next_act).name }}
            </p>
            <p v-else>
              N/A
            </p>
          </template>
          <template #cell(previous_act)="data">
            <p v-if="data.item.previous_act">
              {{ ACT_BY_ID(data.item.previous_act).name }}
            </p>
            <p v-else>
              N/A
            </p>
          </template>
          <template #cell(btn)="data">
            <b-button-group>
              <b-button
                variant="warning"
                @click="openEditForm(data)"
              >
                Edit
              </b-button>
              <b-button
                variant="danger"
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
      </b-col>
    </b-row>
    <b-modal
      id="new-act"
      ref="new-act"
      title="Add New Act"
      size="md"
      @show="resetNewForm"
      @hidden="resetNewForm"
      @ok="onSubmitNew"
    >
      <b-form
        ref="new-act-form"
        @submit.stop.prevent="onSubmitNew"
      >
        <b-form-group
          id="name-input-group"
          label="Name"
          label-for="name-input"
        >
          <b-form-input
            id="name-input"
            v-model="$v.newFormState.name.$model"
            name="name-input"
            :state="validateNewState('name')"
            aria-describedby="name-feedback"
          />
          <b-form-invalid-feedback
            id="name-feedback"
          >
            This is a required field.
          </b-form-invalid-feedback>
        </b-form-group>
        <b-form-group
          id="interval-input-group"
          label="Interval After"
          label-for="interval-input"
        >
          <b-form-checkbox
            id="interval-input"
            v-model="newFormState.interval_after"
            name="interval-input"
          />
        </b-form-group>
        <b-form-group
          id="previous-act-input-group"
          label="Previous Act"
          label-for="previous-act-input"
        >
          <b-form-select
            id="previous-act-input"
            v-model="newFormState.previous_act_id"
            :options="previousActOptions"
            aria-describedby="previous-act-feedback"
          />
        </b-form-group>
      </b-form>
    </b-modal>
    <b-modal
      id="edit-act"
      ref="edit-act"
      title="Edit Act"
      size="md"
      @hidden="resetEditForm"
      @ok="onSubmitEdit"
    >
      <b-form
        ref="edit-act-form"
        @submit.stop.prevent="onSubmitEdit"
      >
        <b-form-group
          id="name-input-group"
          label="Name"
          label-for="name-input"
        >
          <b-form-input
            id="name-input"
            v-model="$v.editFormState.name.$model"
            name="name-input"
            :state="validateEditState('name')"
            aria-describedby="name-feedback"
          />
          <b-form-invalid-feedback
            id="name-feedback"
          >
            This is a required field.
          </b-form-invalid-feedback>
        </b-form-group>
        <b-form-group
          id="interval-input-group"
          label="Interval After"
          label-for="interval-input"
        >
          <b-form-checkbox
            id="interval-input"
            v-model="editFormState.interval_after"
            name="interval-input"
          />
        </b-form-group>
        <b-form-group
          id="previous-act-input-group"
          label="Previous Act"
          label-for="previous-act-input"
        >
          <b-form-select
            id="previous-act-input"
            v-model="$v.editFormState.previous_act_id.$model"
            :options="editFormActOptions"
            :state="validateEditState('previous_act_id')"
            aria-describedby="previous-act-feedback"
          />
          <b-form-invalid-feedback
            id="previous-act-feedback"
          >
            This cannot form a circular dependency between acts.
          </b-form-invalid-feedback>
        </b-form-group>
      </b-form>
    </b-modal>
  </b-container>
</template>

<script>
import { required, integer } from 'vuelidate/lib/validators';
import { mapGetters, mapActions } from 'vuex';

export default {
  name: 'ConfigActs',
  data() {
    return {
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
        previous_act_id: null,
      },
      editFormState: {
        id: null,
        showID: null,
        name: '',
        interval_after: false,
        previous_act_id: null,
      },
    };
  },
  validations: {
    newFormState: {
      name: {
        required,
      },
    },
    editFormState: {
      name: {
        required,
      },
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
  async mounted() {
    await this.GET_ACT_LIST();
  },
  methods: {
    resetNewForm() {
      this.newFormState = {
        name: '',
        interval_after: false,
        previous_act_id: null,
      };

      this.$nextTick(() => {
        this.$v.$reset();
      });
    },
    validateNewState(name) {
      const { $dirty, $error } = this.$v.newFormState[name];
      return $dirty ? !$error : null;
    },
    async onSubmitNew(event) {
      this.$v.newFormState.$touch();
      if (this.$v.newFormState.$anyError) {
        event.preventDefault();
      } else {
        await this.ADD_ACT(this.newFormState);
        this.resetNewForm();
      }
    },
    openEditForm(act) {
      if (act != null) {
        this.editFormState.id = act.item.id;
        this.editFormState.showID = act.item.show_id;
        this.editFormState.name = act.item.name;
        this.editFormState.interval_after = act.item.interval_after;
        if (act.item.previous_act != null) {
          this.editFormState.previous_act_id = act.item.previous_act;
        }
        this.$bvModal.show('edit-act');
      }
    },
    resetEditForm() {
      this.editFormState = {
        id: null,
        showID: null,
        name: '',
        interval_after: false,
        previous_act_id: null,
      };

      this.$nextTick(() => {
        this.$v.$reset();
      });
    },
    async onSubmitEdit(event) {
      this.$v.editFormState.$touch();
      if (this.$v.editFormState.$anyError) {
        event.preventDefault();
      } else {
        await this.UPDATE_ACT(this.editFormState);
        this.resetEditForm();
      }
    },
    validateEditState(name) {
      const { $dirty, $error } = this.$v.editFormState[name];
      return $dirty ? !$error : null;
    },
    async deleteAct(act) {
      const msg = `Are you sure you want to delete ${act.item.name}?`;
      const action = await this.$bvModal.msgBoxConfirm(msg, {});
      if (action === true) {
        await this.DELETE_ACT(act.item.id);
      }
    },
    ...mapActions(['GET_ACT_LIST', 'ADD_ACT', 'DELETE_ACT', 'UPDATE_ACT']),
  },
  computed: {
    actTableItems() {
      const ret = [];
      if (this.CURRENT_SHOW.first_act_id != null && this.ACT_LIST.length > 0) {
        let act = this.ACT_BY_ID(this.CURRENT_SHOW.first_act_id);
        while (act != null) {
          // eslint-disable-next-line no-loop-func
          ret.push(this.ACT_BY_ID(act.id));
          act = this.ACT_BY_ID(act.next_act);
        }
      }
      const actIds = ret.map((x) => (x.id));
      this.ACT_LIST.forEach((act) => {
        if (!actIds.includes(act.id)) {
          ret.push(act);
        }
      });
      return ret;
    },
    previousActOptions() {
      return [
        { value: null, text: 'None', disabled: false },
        ...this.ACT_LIST.filter((act) => (act.next_act == null), this).map((act) => ({
          value: act.id,
          text: act.name,
        })),
      ];
    },
    editFormActOptions() {
      const ret = [];
      ret.push(...this.previousActOptions.filter((act) => (act.value !== this.editFormState.id)));
      if (this.editFormState.previous_act_id != null) {
        const act = this.ACT_LIST.find((a) => (a.id === this.editFormState.previous_act_id));
        ret.push({
          value: this.editFormState.previous_act_id,
          text: act.name,
          disabled: false,
        });
      }
      return ret;
    },
    ...mapGetters(['ACT_LIST', 'CURRENT_SHOW', 'ACT_BY_ID']),
  },
};
</script>

<style scoped>

</style>
