<script setup lang="ts">
import type { Source } from '../types'
import SourceCard from './SourceCard.vue'

defineProps<{
  sources: Source[]
}>()
</script>

<template>
  <div v-if="sources.length > 0" class="space-y-2">
    <div class="text-sm font-medium text-gray-400 mb-3">来源</div>
    <SourceCard
      v-for="(source, i) in sources"
      :key="i"
      :source="source"
      :index="i + 1"
    />
  </div>
</template>
