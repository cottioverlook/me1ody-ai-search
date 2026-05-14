<script setup lang="ts">
import type { CitationAudit, PipelineStep } from '../types'

defineProps<{
  steps: PipelineStep[]
  audit?: CitationAudit | null
}>()

function stepClass(status: PipelineStep['status']): string {
  if (status === 'done') return 'border-emerald-700/70 bg-emerald-500/10 text-emerald-200'
  if (status === 'running') return 'border-indigo-700/70 bg-indigo-500/10 text-indigo-200'
  return 'border-gray-800 bg-gray-900/40 text-gray-500'
}

function dotClass(status: PipelineStep['status']): string {
  if (status === 'done') return 'bg-emerald-400'
  if (status === 'running') return 'bg-indigo-400 animate-pulse'
  return 'bg-gray-700'
}

function durationText(duration?: number): string {
  if (duration === undefined) return ''
  if (duration < 1000) return `${Math.round(duration)}ms`
  return `${(duration / 1000).toFixed(1)}s`
}
</script>

<template>
  <div class="mb-6 border border-gray-800 bg-gray-900/30 p-4 rounded-xl">
    <div class="flex items-center justify-between gap-3 mb-3">
      <span class="text-sm font-medium text-gray-300">检索链路</span>
      <span
        v-if="audit"
        class="text-xs px-2 py-1 rounded border"
        :class="audit.valid ? 'border-emerald-700/70 bg-emerald-500/10 text-emerald-300' : 'border-amber-700/70 bg-amber-500/10 text-amber-300'"
      >
        {{ audit.valid ? '引用通过' : '需核对引用' }}
      </span>
    </div>

    <div class="grid grid-cols-1 sm:grid-cols-5 gap-2">
      <div
        v-for="step in steps"
        :key="step.stage"
        class="min-h-10 rounded-lg border px-3 py-2 flex items-center gap-2 text-xs"
        :class="stepClass(step.status)"
      >
        <span class="w-2 h-2 rounded-full flex-shrink-0" :class="dotClass(step.status)"></span>
        <span class="truncate">{{ step.label }}</span>
        <span v-if="step.duration_ms !== undefined" class="ml-auto text-[11px] opacity-70">
          {{ durationText(step.duration_ms) }}
        </span>
      </div>
    </div>

    <div v-if="audit" class="mt-3 text-xs text-gray-500">
      来源数 {{ audit.source_count }} ·
      {{ audit.has_citations ? '已检测到引用' : '未检测到引用' }}
      <span v-if="audit.invalid_citations.length > 0">
        · 异常引用 {{ audit.invalid_citations.map((num) => `[${num}]`).join(' ') }}
      </span>
    </div>
  </div>
</template>
