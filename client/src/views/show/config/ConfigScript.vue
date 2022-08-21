<template>
  <b-container class="mx-0" fluid>
    <b-row>
      <b-col cols="4">
        <h5>Revisions</h5>
        <b-table id="revisions-table" :items="SCRIPT_REVISIONS"
                 :fields="revisionColumns" show-empty>
          <template #head(btn)="data">
            <b-button variant="outline-success" v-b-modal.new-revision>
              New Revision
            </b-button>
          </template>
        </b-table>
      </b-col>
    </b-row>
  </b-container>
</template>

<script>
import { mapActions, mapGetters } from 'vuex';

export default {
  name: 'ConfigScript',
  data() {
    return {
      revisionColumns: [
        'revision',
        'created_at',
        'edited_at',
        'description',
        { key: 'btn', label: '' },
      ],
    };
  },
  async mounted() {
    await this.GET_SCRIPT_REVISIONS();
  },
  methods: {
    ...mapActions(['GET_SCRIPT_REVISIONS']),
  },
  computed: {
    ...mapGetters(['SCRIPT_REVISIONS']),
  },
};
</script>
