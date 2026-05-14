<script setup lang="ts">
import type { Source } from '../types'

defineProps<{
  source: Source
  index: number
}>()

function getDomain(url: string): string {
  try {
    return new URL(url).hostname.replace('www.', '')
  } catch {
    return url
  }
}

function qualityText(label?: Source['quality_label']): string {
  if (label === 'high') return '高可信'
  if (label === 'low') return '待核验'
  return '中可信'
}

function qualityClass(label?: Source['quality_label']): string {
  if (label === 'high') return 'border-emerald-700/70 bg-emerald-500/10 text-emerald-300'
  if (label === 'low') return 'border-amber-700/70 bg-amber-500/10 text-amber-300'
  return 'border-gray-700 bg-gray-800/70 text-gray-300'
}
</script>

<template>
  <a
    :href="source.url"
    target="_blank"
    rel="noopener noreferrer"
    class="block p-4 rounded-xl border border-gray-800 bg-gray-900/30 hover:border-gray-600 hover:bg-gray-800/50 transition-all group"
  >
    <div class="flex items-start gap-3">
      <div class="flex-shrink-0 mt-0.5">
        <div class="w-7 h-7 rounded-lg bg-gray-800 flex items-center justify-center text-xs font-medium text-gray-400 group-hover:text-indigo-400 group-hover:bg-indigo-500/10 transition-colors">
          {{ source.citation_index || index }}
        </div>
      </div>
      <div class="min-w-0 flex-1">
        <div class="text-sm font-medium text-gray-200 group-hover:text-indigo-400 transition-colors line-clamp-1">
          {{ source.title }}
        </div>
        <div class="text-xs text-gray-500 mt-1 flex items-center gap-2 flex-wrap">
          <span class="inline-flex items-center gap-1">
            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
            </svg>
            {{ getDomain(source.url) }}
          </span>
          <span
            v-if="source.quality_score !== undefined"
            class="inline-flex h-5 items-center rounded border px-1.5 text-[11px]"
            :class="qualityClass(source.quality_label)"
          >
            {{ qualityText(source.quality_label) }} {{ Math.round(source.quality_score * 100) }}
          </span>
          <span
            v-if="source.source_type_label"
            class="inline-flex h-5 items-center rounded border border-indigo-800/70 bg-indigo-500/10 px-1.5 text-[11px] text-indigo-300"
          >
            {{ source.source_type_label }}
          </span>
        </div>
        <div class="text-sm text-gray-400 mt-2 line-clamp-2 leading-relaxed">{{ source.snippet }}</div>
      </div>
    </div>
  </a>
</template>
