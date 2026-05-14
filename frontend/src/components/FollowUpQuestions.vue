<script setup lang="ts">
defineProps<{
  questions: string[]
}>()

const emit = defineEmits<{
  select: [question: string]
}>()
</script>

<template>
  <div v-if="questions.length > 0" class="mt-8">
    <div class="flex items-center gap-2 mb-4">
      <svg class="w-5 h-5 text-amber-400" fill="currentColor" viewBox="0 0 20 20">
        <path fill-rule="evenodd"
          d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z"
          clip-rule="evenodd" />
      </svg>
      <span class="text-sm font-medium text-gray-400">相关问题</span>
    </div>
    <div class="grid gap-2">
      <button
        v-for="(q, i) in questions"
        :key="i"
        @click="emit('select', q)"
        class="text-left px-4 py-3 rounded-xl border border-gray-800 text-sm text-gray-300 hover:border-indigo-500/50 hover:text-indigo-400 hover:bg-indigo-500/5 transition-all"
      >
        <div class="flex items-center gap-2">
          <svg class="w-4 h-4 text-gray-600 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
          </svg>
          {{ q }}
        </div>
      </button>
    </div>
  </div>
</template>
