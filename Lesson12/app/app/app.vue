<template>
  <div class="wrap">
    <nav>
      <NuxtLink to="/">Home</NuxtLink>
      <NuxtLink to="/about">About</NuxtLink>
    </nav>
    <NuxtPage />
    <footer>Built {{ buildTime }} · served from S3 via CloudFront</footer>
  </div>
</template>

<script setup lang="ts">
const buildTime = useState('buildTime', () => new Date().toISOString())
</script>

<style>
body { margin: 0; font-family: system-ui, sans-serif; background: #f6f7f9; color: #1f2328; }
.wrap { max-width: 720px; margin: 0 auto; padding: 32px 16px; }
nav { display: flex; gap: 16px; margin-bottom: 24px; }
nav a { color: #00a36c; font-weight: 600; text-decoration: none; }
nav a.router-link-exact-active { text-decoration: underline; }
footer { margin-top: 48px; font-size: 13px; color: #6b7280; }
</style>
