<script setup lang="ts">
import { computed, watch, nextTick, ref } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import hljs from 'highlight.js/lib/core'
import bash from 'highlight.js/lib/languages/bash'
import css from 'highlight.js/lib/languages/css'
import java from 'highlight.js/lib/languages/java'
import javascript from 'highlight.js/lib/languages/javascript'
import json from 'highlight.js/lib/languages/json'
import python from 'highlight.js/lib/languages/python'
import sql from 'highlight.js/lib/languages/sql'
import typescript from 'highlight.js/lib/languages/typescript'
import xml from 'highlight.js/lib/languages/xml'
import type { Source } from '../types'

hljs.registerLanguage('bash', bash)
hljs.registerLanguage('css', css)
hljs.registerLanguage('java', java)
hljs.registerLanguage('javascript', javascript)
hljs.registerLanguage('json', json)
hljs.registerLanguage('python', python)
hljs.registerLanguage('sql', sql)
hljs.registerLanguage('typescript', typescript)
hljs.registerLanguage('xml', xml)

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

function escapeHtmlAttribute(value: string): string {
  return value.replace(/[&"'<>]/g, (character) => ({
    '&': '&amp;',
    '"': '&quot;',
    "'": '&#39;',
    '<': '&lt;',
    '>': '&gt;',
  })[character]!)
}

function safeCitationUrl(value: string): string {
  try {
    const url = new URL(value)
    return ['http:', 'https:'].includes(url.protocol) ? url.toString() : '#'
  } catch {
    return '#'
  }
}

const processedHtml = computed(() => {
  if (!renderedHtml.value || !props.sources.length) return renderedHtml.value
  const withCitations = renderedHtml.value.replace(
    /\[(\d+)\]/g,
    (_, num) => {
      const idx = parseInt(num) - 1
      if (idx >= 0 && idx < props.sources.length) {
        const url = escapeHtmlAttribute(safeCitationUrl(props.sources[idx].url))
        const title = escapeHtmlAttribute(props.sources[idx].title)
        return `<a href="${url}" target="_blank" rel="noopener noreferrer" class="citation-link" title="${title}">[${num}]</a>`
      }
      return `<span class="citation-link">[${num}]</span>`
    }
  )
  return DOMPurify.sanitize(withCitations)
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
