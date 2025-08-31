<template>
  <div class="about">
    <h1>About DigiScript</h1>
    <p class="description">
      A digital script resource for queueing shows, produced by the Dream Team
    </p>
    <p class="team-intro">The dream team is</p>
    <ul class="team-list">
      <li>Tim Bradgate</li>
      <li>Jack Pollock</li>
      <li>Matthew Stratford</li>
      <li>Matthew Gaynor</li>
    </ul>
  </div>
</template>

<script setup lang="ts">
// Static content - no reactive data needed yet
</script>

<style scoped>
.about {
  color: white;
  max-width: 600px;
  margin: 0 auto;
  padding: 2rem 0;
}

.about h1 {
  font-size: 2.5rem;
  margin-bottom: 1.5rem;
  color: white;
}

.description {
  font-size: 1.125rem;
  margin-bottom: 1.5rem;
  line-height: 1.6;
}

.team-intro {
  font-size: 1.125rem;
  margin-bottom: 1rem;
}

.team-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.team-list li {
  font-size: 1rem;
  margin-bottom: 0.5rem;
  color: white;
}
</style>
