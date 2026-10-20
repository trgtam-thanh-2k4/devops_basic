<template>
  <section>
    <h1>Hello from Nuxt 👋</h1>
    <p>This site is a static Nuxt build stored in a private S3 bucket and served through CloudFront.</p>
    <p>Counter (checks that client-side JS works): <button @click="count++">{{ count }}</button></p>
  </section>
</template>

<script setup lang="ts">
const count = ref(0)
</script>
