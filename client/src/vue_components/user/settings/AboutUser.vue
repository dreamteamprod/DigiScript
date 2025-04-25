<template>
  <b-table-simple>
    <b-tr
      v-for="key in orderedKeys"
      :key="key"
    >
      <b-th>{{ key }}</b-th>
      <b-td>{{ tableData[key] != null ? tableData[key] : 'N/A' }}</b-td>
    </b-tr>
  </b-table-simple>
</template>

<script>
import { mapActions, mapGetters } from 'vuex'
import { titleCase } from '@/js/utils'

export default {
  name: 'AboutUser',
  computed: {
    tableData () {
      const data = {}
      Object.keys(this.CURRENT_USER).forEach(function (key) {
        data[this.titleCase(key, '_')] = this.CURRENT_USER[key]
      }, this)
      return data
    },
    orderedKeys () {
      return Object.keys(this.tableData).sort()
    },
    ...mapGetters(['CURRENT_USER']),
  },
  async beforeMount () {
    await this.GET_CURRENT_USER()
  },
  methods: {
    titleCase,
    ...mapActions(['GET_CURRENT_USER']),
  },
}
</script>
