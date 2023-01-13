<template>
  <b-container class="mx-0" fluid>
    <b-row>
      <b-col>
        <p>
          Elapsed Time: {{ msToTimer(elapsedTime) }}
        </p>
      </b-col>
    </b-row>
    <b-row>
      <b-col>
        <div class="script-container" id="script-container">
          <p class="script-item" v-for="index in 100" :key="index">
            Line {{ index }}
          </p>
        </div>
      </b-col>
    </b-row>
  </b-container>
</template>

<script>
import { mapGetters, mapActions } from 'vuex';
import $ from 'jquery';
import { debounce } from 'lodash';

import { msToTimer } from '@/js/utils';

export default {
  name: 'ShowLiveView',
  data() {
    return {
      elapsedTime: 0,
      elapsedTimer: null,
      scrollTimer: null,
    };
  },
  async mounted() {
    await this.GET_SHOW_SESSION_DATA();
    if (this.CURRENT_SHOW_SESSION == null) {
      this.$toast.warning('No live session started!');
      this.$router.replace('/');
    } else {
      this.updateElapsedTime();
      this.computeContentSize();
      this.computeTopScriptElement();

      this.elapsedTimer = setInterval(this.updateElapsedTime, 1000);
      this.scrollTimer = setInterval(this.computeTopScriptElement, 50);
      window.addEventListener('resize', debounce(this.computeContentSize, 100));
    }
  },
  destroyed() {
    clearInterval(this.elapsedTimer);
    clearInterval(this.scrollTimer);
  },
  methods: {
    msToTimer,
    updateElapsedTime() {
      const now = new Date().getTime();
      const startTime = Date.parse(this.CURRENT_SHOW_SESSION.start_date_time);
      this.elapsedTime = now - startTime;
    },
    computeTopScriptElement() {
      const scriptContainer = $('#script-container');
      const cutoff = scriptContainer.offset().top;

      $('.script-item').each(function () {
        if ($(this).offset().top + $(this).height() > cutoff) {
          $('.script-item').removeClass('first-script-element');
          $(this).addClass('first-script-element');
          return false;
        }
        return true;
      });
    },
    computeContentSize() {
      const scriptContainer = $('#script-container');
      const startPos = scriptContainer.offset().top;
      const boxHeight = document.documentElement.clientHeight - startPos;
      scriptContainer.height(boxHeight - 10);
    },
    ...mapActions(['GET_SHOW_SESSION_DATA']),
  },
  computed: {
    ...mapGetters(['CURRENT_SHOW_SESSION']),
  },
};
</script>

<style scoped>
  .script-container {
    overflow: scroll;
    width: 100vw;
  }
</style>
