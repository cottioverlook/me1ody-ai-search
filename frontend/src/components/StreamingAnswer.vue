<script setup lang="ts">
import { computed, watch, nextTick, ref } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import hljs from 'highlight.js'
import type { Source } from '../types'

const props = defineProps<{
  content: string
  sources: Source[]
  isStreaming: boolean
}>()

const containerRef = ref<HTMLElement | null>(null)

const renderedHtml = computed(() => {
  if (!props.content) return ''
  const raw = marked.parse(props.content, { gfm: true, breaks: true }) as string
  return DOMPurify.sanitize(raw)
})

const processedHtml = computed(() => {
  if (!renderedHtml.value || !props.sources.length) return renderedHtml.value
  return renderedHtml.value.replace(
    /\[(\d+)\]/g,
    (_, num) => {
      const idx = parseInt(num) - 1
      if (idx >= 0 && idx < props.sources.length) {
        return `<a href="${props.sources[idx].url}" target="_blank" rel="noopener noreferrer" class="citation-link" title="${props.sources[idx].title}">[${num}]</a>`
      }
      return `<span class="citation-link">[${num}]</span>`
    }
  )
})

watch(processedHtml, () => {
  nextTick(() => {
    if (containerRef.value) {
      containerRef.value.querySelectorAll('pre code').forEach((block) => {
        hljs.highlightElement(block as HTMLElement)
      })
    }
  })
})
</script>

<template>
  <div ref="containerRef" class="prose-answer" :class="{ 'streaming-cursor': isStreaming }">
    <div v-html="processedHtml"></div>
  </div>
</template>
