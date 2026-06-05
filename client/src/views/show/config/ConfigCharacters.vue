<template>
  <b-container class="mx-0" fluid>
    <b-row>
      <b-col>
        <b-tabs content-class="mt-3">
          <b-tab title="Characters" active>
            <b-table
              id="character-table"
              :items="CHARACTER_LIST"
              :fields="characterFields"
              :per-page="rowsPerPage"
              :current-page="currentPage"
              show-empty
            >
              <template #head(btn)="data">
                <b-button v-if="IS_SHOW_EDITOR" v-b-modal.new-character variant="outline-success">
                  New Character
                </b-button>
              </template>
              <template #cell(cast_member)="data">
                <template v-if="data.item.cast_member">
                  {{ data.item.cast_member.first_name }} {{ data.item.cast_member.last_name }}
                </template>
                <template v-else-if="IS_SHOW_EDITOR">
                  <b-link @click="openEditForm(data)"> Set Cast Member </b-link>
                </template>
              </template>
              <template #cell(btn)="data">
                <b-button-group v-if="IS_SHOW_EDITOR">
                  <b-button
                    variant="warning"
                    :disabled="submittingEditCharacter || deletingCharacter || mergingCharacter"
                    @click="openEditForm(data)"
                  >
                    Edit
                  </b-button>
                  <b-button
                    variant="info"
                    :disabled="submittingEditCharacter || deletingCharacter || mergingCharacter"
                    @click="openMergeForm(data)"
                  >
                    Merge
                  </b-button>
                  <b-button
                    variant="danger"
                    :disabled="submittingEditCharacter || deletingCharacter || mergingCharacter"
                    @click="deleteCharacter(data)"
                  >
                    Delete
                  </b-button>
                </b-button-group>
              </template>
            </b-table>
            <b-pagination
              v-show="CHARACTER_LIST.length > rowsPerPage"
              v-model="currentPage"
              :total-rows="CHARACTER_LIST.length"
              :per-page="rowsPerPage"
              aria-controls="character-table"
              class="justify-content-center"
            />
          </b-tab>
          <b-tab title="Character Groups">
            <character-groups />
          </b-tab>
          <b-tab title="Line Counts">
            <character-line-stats />
          </b-tab>
        </b-tabs>
      </b-col>
    </b-row>
    <b-modal
      id="merge-character"
      ref="merge-character"
      :title="`Merge ${mergeSourceCharacter ? mergeSourceCharacter.name : 'Character'}`"
      size="md"
      :ok-disabled="!mergeDestinationCharacter || mergingCharacter"
      @hidden="resetMergeForm"
      @ok="onSubmitMerge"
    >
      <p>
        Select a destination character. All script lines and group memberships from
        <strong>{{ mergeSourceCharacter ? mergeSourceCharacter.name : '' }}</strong>
        will be transferred to the selected character, and it will be deleted.
      </p>
      <b-form-group label="Merge into" label-for="merge-destination-input" label-cols="4">
        <multi-select
          id="merge-destination-input"
          v-model="mergeDestinationCharacter"
          :multiple="false"
          :options="mergeDestinationOptions"
          track-by="id"
          label="name"
          placeholder="Select destination character"
        />
      </b-form-group>
    </b-modal>
    <b-modal
      id="new-character"
      ref="new-character"
      title="Add New Character"
      size="md"
      :ok-disabled="$v.newFormState.$invalid || submittingNewCharacter"
      @show="resetNewForm"
      @hidden="resetNewForm"
      @ok="onSubmitNew"
    >
      <b-form ref="new-character-form" @submit.stop.prevent="onSubmitNew">
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
          id="new-description-input-group"
          label="Description"
          label-for="new-description-input"
        >
          <b-form-input
            id="new-description-input"
            v-model="$v.newFormState.description.$model"
            name="new-description-input"
            :state="getValidationState('newFormState', 'description')"
          />
        </b-form-group>
        <b-form-group
          id="new-played-by-input-group"
          label="Played By"
          label-for="new-played-by-input"
        >
          <b-form-select
            id="new-played-by-input"
            v-model="$v.newFormState.played_by.$model"
            :options="castOptions"
            :state="getValidationState('newFormState', 'played_by')"
          />
        </b-form-group>
      </b-form>
    </b-modal>
    <b-modal
      id="edit-character"
      ref="edit-character"
      title="Edit Cast Member"
      size="md"
      :ok-disabled="$v.editFormState.$invalid || submittingEditCharacter"
      @hidden="resetEditForm"
      @ok="onSubmitEdit"
    >
      <b-form ref="edit-character-form" @submit.stop.prevent="onSubmitEdit">
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
          id="edit-description-input-group"
          label="Description"
          label-for="edit-description-input"
        >
          <b-form-input
            id="edit-description-input"
            v-model="$v.editFormState.description.$model"
            name="edit-description-input"
            :state="getValidationState('editFormState', 'description')"
          />
        </b-form-group>
        <b-form-group
          id="edit-played-by-input-group"
          label="Played By"
          label-for="edit-played-by-input"
        >
          <b-form-select
            id="edit-played-by-input"
            v-model="$v.editFormState.played_by.$model"
            :options="castOptions"
            :state="getValidationState('editFormState', 'played_by')"
          />
        </b-form-group>
      </b-form>
    </b-modal>
  </b-container>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import { required } from 'vuelidate/lib/validators';
import { mapGetters, mapActions } from 'vuex';
import CharacterLineStats from '@/vue_components/show/config/characters/CharacterLineStats.vue';
import log from 'loglevel';
import CharacterGroups from '@/vue_components/show/config/characters/CharacterGroups.vue';
import formValidationMixin from '@/mixins/formValidationMixin';

export default defineComponent({
  name: 'ConfigCharacters',
  components: { CharacterGroups, CharacterLineStats },
  mixins: [formValidationMixin],
  data() {
    return {
      rowsPerPage: 15,
      currentPage: 1,
      characterFields: [
        'name',
        'description',
        { key: 'cast_member', label: 'Played By' },
        { key: 'btn', label: '' },
      ],
      newFormState: {
        name: '',
        description: '',
        played_by: null as number | null,
      },
      editFormState: {
        id: null as number | null,
        showID: null as number | null,
        name: '',
        description: '',
        played_by: null as number | null,
      },
      submittingNewCharacter: false,
      submittingEditCharacter: false,
      deletingCharacter: false,
      mergingCharacter: false,
      mergeSourceCharacter: null as any,
      mergeDestinationCharacter: null as any,
    };
  },
  validations: {
    newFormState: {
      name: { required },
      description: {},
      played_by: {},
    },
    editFormState: {
      name: { required },
      description: {},
      played_by: {},
    },
  },
  computed: {
    ...mapGetters(['CHARACTER_LIST', 'CAST_LIST', 'IS_SHOW_EDITOR']),
    castOptions(): unknown[] {
      return [
        { value: null, text: 'Please select an option', disabled: true },
        ...(this as any).CAST_LIST.map((castMember: any) => ({
          value: castMember.id,
          text: `${castMember.first_name} ${castMember.last_name}`,
        })),
      ];
    },
    mergeDestinationOptions(): any[] {
      return (this as any).CHARACTER_LIST.filter(
        (c: any) => !(this as any).mergeSourceCharacter || c.id !== (this as any).mergeSourceCharacter.id,
      );
    },
  },
  async mounted(): Promise<void> {
    await Promise.all([(this as any).GET_CHARACTER_LIST(), (this as any).GET_CAST_LIST()]);
  },
  methods: {
    resetNewForm(): void {
      (this as any).resetForm('newFormState', { name: '', description: '', played_by: null });
      this.submittingNewCharacter = false;
    },
    async onSubmitNew(event: Event): Promise<void> {
      (this as any).$v.newFormState.$touch();
      if ((this as any).$v.newFormState.$anyError || this.submittingNewCharacter) {
        event.preventDefault();
        return;
      }
      this.submittingNewCharacter = true;
      try {
        await (this as any).ADD_CHARACTER(this.newFormState);
        (this as any).$bvModal.hide('new-character');
        this.resetNewForm();
      } catch (error) {
        log.error('Error submitting new character:', error);
        event.preventDefault();
      } finally {
        this.submittingNewCharacter = false;
      }
    },
    openEditForm(character: any): void {
      if (character != null) {
        this.editFormState.id = character.item.id;
        this.editFormState.showID = character.item.show_id;
        this.editFormState.name = character.item.name;
        this.editFormState.description = character.item.description;
        this.editFormState.played_by = character.item.played_by;
        (this as any).$bvModal.show('edit-character');
      }
    },
    resetEditForm(): void {
      (this as any).resetForm('editFormState', {
        id: null,
        showID: null,
        name: '',
        description: '',
        played_by: null,
      });
      this.submittingEditCharacter = false;
      this.deletingCharacter = false;
    },
    async onSubmitEdit(event: Event): Promise<void> {
      (this as any).$v.editFormState.$touch();
      if ((this as any).$v.editFormState.$anyError || this.submittingEditCharacter) {
        event.preventDefault();
        return;
      }
      this.submittingEditCharacter = true;
      try {
        await (this as any).UPDATE_CHARACTER(this.editFormState);
        (this as any).$bvModal.hide('edit-character');
        this.resetEditForm();
      } catch (error) {
        log.error('Error submitting edit character:', error);
        event.preventDefault();
      } finally {
        this.submittingEditCharacter = false;
      }
    },
    async deleteCharacter(character: any): Promise<void> {
      if (this.deletingCharacter) {
        return;
      }
      const msg = `Are you sure you want to delete ${character.item.name}?`;
      const action = await (this as any).$bvModal.msgBoxConfirm(msg, {});
      if (action === true) {
        this.deletingCharacter = true;
        try {
          await (this as any).DELETE_CHARACTER(character.item.id);
        } catch (error) {
          log.error('Error deleting character:', error);
        } finally {
          this.deletingCharacter = false;
        }
      }
    },
    openMergeForm(character: any): void {
      this.mergeSourceCharacter = character.item;
      this.mergeDestinationCharacter = null;
      (this as any).$bvModal.show('merge-character');
    },
    resetMergeForm(): void {
      this.mergeSourceCharacter = null;
      this.mergeDestinationCharacter = null;
      this.mergingCharacter = false;
    },
    async onSubmitMerge(event: Event): Promise<void> {
      if (!this.mergeDestinationCharacter || this.mergingCharacter) {
        event.preventDefault();
        return;
      }
      this.mergingCharacter = true;
      try {
        await (this as any).MERGE_CHARACTER({
          source_id: this.mergeSourceCharacter.id,
          destination_id: this.mergeDestinationCharacter.id,
        });
        (this as any).$bvModal.hide('merge-character');
        this.resetMergeForm();
      } catch (error) {
        log.error('Error merging character:', error);
        event.preventDefault();
      } finally {
        this.mergingCharacter = false;
      }
    },
    ...mapActions([
      'GET_CHARACTER_LIST',
      'GET_CAST_LIST',
      'ADD_CHARACTER',
      'UPDATE_CHARACTER',
      'DELETE_CHARACTER',
      'MERGE_CHARACTER',
    ]),
  },
});
</script>

<style scoped></style>
