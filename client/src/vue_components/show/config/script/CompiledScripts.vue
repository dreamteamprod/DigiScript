<template>
  <p v-if="!loading">
    <b-table id="compiled-script-table" :items="tableData" :fields="tableColumns" show-empty>
      <template #cell(revision_id)="data">
        <span v-if="data.item.revision_id === CURRENT_REVISION"
          >{{ data.item.revision }} <b-icon-check-square-fill variant="success"
        /></span>
        <span v-else>{{ data.item.revision }}</span>
      </template>
      <template #cell(btn)="data">
        <b-button-group v-if="data.item.revision_id !== pendingRevisionId && IS_SCRIPT_EDITOR">
          <b-button
            v-if="data.item.data_path != null"
            variant="danger"
            :disabled="deletingCompiledScript || generatingCompiledScript"
            @click="deleteCompiledScript(data)"
          >
            Delete
          </b-button>
          <b-button
            v-else
            variant="success"
            :disabled="deletingCompiledScript || generatingCompiledScript"
            @click="generateCompiledScript(data)"
          >
            Generate
          </b-button>
        </b-button-group>
        <b-spinner v-else-if="data.item.revision_id === pendingRevisionId" />
      </template>
    </b-table>
  </p>
  <b-container v-else class="mx-0 px-0 script-editor-container" fluid>
    <b-row>
      <b-col>
        <div class="text-center py-5">
          <b-spinner label="Loading" />
        </div>
      </b-col>
    </b-row>
  </b-container>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import { mapActions, mapGetters } from 'vuex';
import { makeURL } from '@/js/utils';
import log from 'loglevel';

export default defineComponent({
  name: 'CompiledScripts',
  data() {
    return {
      loading: true,
      tableColumns: [
        { key: 'revision_id', label: 'Script Revision' },
        'created_at',
        'updated_at',
        'data_path',
        { key: 'btn', label: '' },
      ],
      deletingCompiledScript: false,
      generatingCompiledScript: false,
      pendingRevisionId: null as number | null,
    };
  },
  computed: {
    tableData(): any[] {
      const data: any[] = [];
      (this as any).SCRIPT_REVISIONS.forEach((revision: any) => {
        const compiledScript = (this as any).COMPILED_SCRIPTS.find(
          (cs: any) => cs.revision_id === revision.id
        );
        data.push({
          revision_id: revision.id,
          created_at: compiledScript?.created_at,
          updated_at: compiledScript?.updated_at,
          data_path: compiledScript?.data_path,
          revision: revision.revision,
        });
      });
      return data;
    },
    ...mapGetters(['COMPILED_SCRIPTS', 'SCRIPT_REVISIONS', 'IS_SCRIPT_EDITOR', 'CURRENT_REVISION']),
  },
  async mounted(): Promise<void> {
    await (this as any).GET_COMPILED_SCRIPTS();
    this.loading = false;
  },
  methods: {
    async deleteCompiledScript(data: any): Promise<void> {
      const msg = `Are you sure you want to delete the compiled script for revision ${data.item.revision_id}?`;
      const action = await (this as any).$bvModal.msgBoxConfirm(msg, {});
      if (action === false) {
        return;
      }
      this.deletingCompiledScript = true;
      this.pendingRevisionId = data.item.revision_id;
      const searchParams = new URLSearchParams({
        revision_id: data.item.revision_id,
      });
      try {
        const response = await fetch(
          `${makeURL('/api/v1/show/script/compiled_scripts')}?${searchParams}`,
          {
            method: 'DELETE',
            headers: {
              'Content-Type': 'application/json',
            },
          }
        );
        if (response.ok) {
          (this as any).$toast.success('Deleted compiled script!');
        } else {
          log.error('Unable to delete compiled scripts');
          (this as any).$toast.error('Unable to delete compiled script!');
        }
      } catch (e) {
        log.error(e);
        (this as any).$toast.error('Unable to delete compiled script!');
      } finally {
        this.deletingCompiledScript = false;
        this.pendingRevisionId = null;
      }
    },
    async generateCompiledScript(data: any): Promise<void> {
      this.generatingCompiledScript = true;
      this.pendingRevisionId = data.item.revision_id;
      try {
        const response = await fetch(`${makeURL('/api/v1/show/script/compiled_scripts')}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ revision_id: data.item.revision_id }),
        });
        if (response.ok) {
          (this as any).$toast.success('Generated new compiled script!');
        } else {
          log.error('Unable to load compiled scripts');
          (this as any).$toast.error('Unable to compile script revision!');
        }
      } catch (e) {
        log.error(e);
        (this as any).$toast.error('Unable to compile script revision!');
      } finally {
        this.generatingCompiledScript = false;
        this.pendingRevisionId = null;
      }
    },
    ...mapActions(['GET_COMPILED_SCRIPTS']),
  },
});
</script>

<style scoped></style>
