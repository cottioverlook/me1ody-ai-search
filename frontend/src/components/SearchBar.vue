<script setup lang="ts">
import { ref, watch } from 'vue'
import { useSuggestions } from '../composables/useSuggestions'

defineProps<{
  compact?: boolean
}>()

const emit = defineEmits<{
  search: [query: string]
}>()

const query = ref('')
const showSuggestions = ref(false)
const { suggestions, debouncedFetch, clear } = useSuggestions()

watch(query, (val) => {
  debouncedFetch(val)
  showSuggestions.value = true
})

function handleSearch() {
  if (!query.value.trim()) return
  clear()
  showSuggestions.value = false
  emit('search', query.value.trim())
}

function selectSuggestion(s: string) {
  query.value = s
  showSuggestions.value = false
  emit('search', s)
}

function handleBlur() {
  setTimeout(() => {
    showSuggestions.value = false
  }, 200)
}
</script>

<template>
  <div class="relative w-full" :class="compact ? 'max-w-2xl' : 'max-w-3xl mx-auto'">
    <div
      class="flex items-center gap-3 rounded-2xl border border-gray-700 bg-gray-900/80 px-5 py-3 transition-all focus-within:border-indigo-500 focus-within:ring-1 focus-within:ring-indigo-500/30"
      :class="compact ? 'py-2' : 'py-4'"
    >
      <svg class="w-5 h-5 text-gray-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
          d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
      </svg>

      <input
        v-model="query"
        @keydown.enter="handleSearch"
        @focus="showSuggestions = suggestions.length > 0"
        @blur="handleBlur"
        type="text"
        :placeholder="compact ? '继续搜索...' : '搜索任何问题...'"
        class="flex-1 bg-transparent outline-none text-gray-100 placeholder-gray-500"
        :class="compact ? 'text-sm' : 'text-lg'"
        autofocus
      />

      <button
        @click="handleSearch"
        class="flex-shrink-0 p-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 transition-colors text-white disabled:opacity-50"
        :disabled="!query.trim()"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3" />
        </svg>
      </button>
    </div>

    <!-- Suggestions dropdown -->
    <div
      v-if="showSuggestions && suggestions.length > 0"
      class="absolute top-full left-0 right-0 mt-1 bg-gray-900 border border-gray-700 rounded-xl shadow-2xl overflow-hidden z-50"
    >
      <button
        v-for="(s, i) in suggestions"
        :key="i"
        @mousedown.prevent="selectSuggestion(s)"
        class="w-full text-left px-5 py-3 text-sm text-gray-300 hover:bg-gray-800 transition-colors truncate"
      >
        {{ s }}
      </button>
    </div>
  </div>
</template>
