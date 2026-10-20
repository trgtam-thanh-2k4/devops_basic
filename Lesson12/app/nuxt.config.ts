export default defineNuxtConfig({
  compatibilityDate: '2026-10-01',
  // Static site: `npm run generate` pre-renders every page into .output/public
  ssr: true,
  app: {
    head: {
      title: 'Nuxt on S3 + CloudFront',
      meta: [{ name: 'description', content: 'F8 DevOps Lesson 12' }],
    },
  },
})
