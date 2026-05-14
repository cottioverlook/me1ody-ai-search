import { ref } from 'vue'
import type { Message } from '../types'

export function useConversation() {
  const messages = ref<Message[]>([])
  const conversationId = ref<string | null>(null)

  function addUserMessage(content: string) {
    messages.value.push({ role: 'user', content })
  }

  function addAssistantMessage(content: string, sources?: any[], followUps?: string[]) {
    messages.value.push({ role: 'assistant', content, sources, followUps })
  }

  function updateLastAssistant(content: string) {
    const last = messages.value[messages.value.length - 1]
    if (last && last.role === 'assistant') {
      last.content = content
    }
  }

  function setConversationId(id: string | null) {
    conversationId.value = id
  }

  function reset() {
    messages.value = []
    conversationId.value = null
  }

  return {
    messages,
    conversationId,
    addUserMessage,
    addAssistantMessage,
    updateLastAssistant,
    setConversationId,
    reset,
  }
}
