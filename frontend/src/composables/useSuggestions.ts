import { ref } from 'vue'
import { fetchSuggestions } from '../services/api'

export function useSuggestions() {
  const suggestions = ref<string[]>([])
  const loading = ref(false)
  let timer: ReturnType<typeof setTimeout> | null = null

  function debouncedFetch(query: string) {
    if (timer) clearTimeout(timer)
    if (!query || query.length < 2) {
      suggestions.value = []
      return
    }
    timer = setTimeout(async () => {
      loading.value = true
      try {
        suggestions.value = await fetchSuggestions(query)
      } finally {
        loading.value = false
      }
    }, 300)
  }

  function clear() {
    suggestions.value = []
    if (timer) clearTimeout(timer)
  }

  return { suggestions, loading, debouncedFetch, clear }
}
