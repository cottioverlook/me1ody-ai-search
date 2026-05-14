<script setup lang="ts">
import { ref, onMounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import SearchBar from './SearchBar.vue'
import StreamingAnswer from './StreamingAnswer.vue'
import SourceCard from './SourceCard.vue'
import FollowUpQuestions from './FollowUpQuestions.vue'
import PipelineStatus from './PipelineStatus.vue'
import { useSearch } from '../composables/useSearch'
import { fetchConversation } from '../services/api'
import type { CitationAudit, PipelineStep, Source, Message } from '../types'

const route = useRoute()
const router = useRouter()

interface ConversationTurn {
  query: string
  answer: string
  sources: Source[]
  followUps: string[]
  citationAudit?: CitationAudit | null
  pipelineSteps?: PipelineStep[]
}

const turns = ref<ConversationTurn[]>([])
const conversationId = ref<string | null>(null)

const {
  answer,
  sources,
  followUps,
  citationAudit,
  pipelineSteps,
  isStreaming,
  isWaiting,
  conversationId: streamConvId,
  error,
  search,
} = useSearch()

function scrollToBottom() {
  nextTick(() => {
    window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' })
  })
}

async function handleSearch(query: string) {
  if (!conversationId.value) {
    turns.value = []
  }

  turns.value.push({ query, answer: '', sources: [], followUps: [], citationAudit: null, pipelineSteps: [] })
  scrollToBottom()

  await search(query, conversationId.value)
  conversationId.value = streamConvId.value

  const last = turns.value[turns.value.length - 1]
  last.answer = answer.value
  last.sources = [...sources.value]
  last.followUps = [...followUps.value]
  last.citationAudit = citationAudit.value
  last.pipelineSteps = [...pipelineSteps.value]
  scrollToBottom()

  if (streamConvId.value && !route.params.id) {
    router.replace(`/search/${streamConvId.value}`)
  }
}

function handleFollowUp(question: string) {
  handleSearch(question)
}

async function loadConversation(id: string) {
  try {
    const data = await fetchConversation(id)
    conversationId.value = id
    const messages: Message[] = data.messages
    for (let i = 0; i < messages.length; i++) {
      if (messages[i].role === 'user') {
        const assistant = messages[i + 1]?.role === 'assistant' ? messages[i + 1] : null
        turns.value.push({
          query: messages[i].content,
          answer: assistant?.content || '',
          sources: (assistant?.sources as Source[]) || [],
          followUps: [],
          citationAudit: null,
          pipelineSteps: [],
        })
        if (assistant) i++
      }
    }
  } catch { /* conversation not found */ }
}

onMounted(() => {
  const id = route.params.id as string
  const q = route.query.q as string
  if (id) loadConversation(id)
  else if (q) handleSearch(q)
})

watch(() => route.query.q, (newQ) => {
  if (newQ && typeof newQ === 'string') {
    conversationId.value = null
    turns.value = []
    handleSearch(newQ)
  }
})

function displayAnswer(turn: ConversationTurn, index: number): string {
  return index === turns.value.length - 1 && isStreaming.value ? answer.value : turn.answer
}

function displaySources(turn: ConversationTurn, index: number): Source[] {
  return index === turns.value.length - 1 && isStreaming.value ? sources.value : turn.sources
}

function displayFollowUps(turn: ConversationTurn, index: number): string[] {
  return index === turns.value.length - 1 && isStreaming.value ? followUps.value : turn.followUps
}

function displayAudit(turn: ConversationTurn, index: number): CitationAudit | null | undefined {
  return index === turns.value.length - 1 && isStreaming.value ? citationAudit.value : turn.citationAudit
}

function displaySteps(turn: ConversationTurn, index: number): PipelineStep[] {
  return index === turns.value.length - 1 && isStreaming.value ? pipelineSteps.value : (turn.pipelineSteps || [])
}
</script>

<template>
  <div class="max-w-4xl mx-auto px-4 py-6">
    <!-- Sticky search bar -->
    <div class="sticky top-14 z-40 bg-gray-950/90 backdrop-blur-md py-4 -mx-4 px-4">
      <SearchBar compact @search="handleSearch" />
    </div>

    <!-- Error -->
    <div v-if="error" class="mt-4 p-4 rounded-xl bg-red-900/20 border border-red-800 text-red-400 text-sm">
      {{ error }}
    </div>

    <!-- Conversation turns -->
    <div class="mt-6 space-y-12">
      <div v-for="(turn, i) in turns" :key="i">
        <!-- User query -->
        <div class="mb-6">
          <h2 class="text-xl font-semibold text-gray-100">{{ turn.query }}</h2>
        </div>

        <!-- Loading state -->
        <div v-if="i === turns.length - 1 && isWaiting" class="flex items-center gap-3 text-gray-400 text-sm mb-6">
          <div class="flex gap-1">
            <span class="w-2 h-2 rounded-full bg-indigo-500 animate-bounce" style="animation-delay:0ms"></span>
            <span class="w-2 h-2 rounded-full bg-indigo-500 animate-bounce" style="animation-delay:150ms"></span>
            <span class="w-2 h-2 rounded-full bg-indigo-500 animate-bounce" style="animation-delay:300ms"></span>
          </div>
          正在搜索并分析...
        </div>

        <PipelineStatus
          v-if="i === turns.length - 1 && (isStreaming || displaySteps(turn, i).length > 0)"
          :steps="displaySteps(turn, i)"
          :audit="displayAudit(turn, i)"
        />

        <!-- AI Answer section -->
        <div v-if="displayAnswer(turn, i) || (i === turns.length - 1 && isStreaming)" class="mb-8">
          <div class="flex items-center gap-2 mb-4">
            <svg class="w-5 h-5 text-indigo-400" fill="currentColor" viewBox="0 0 20 20">
              <path d="M11 3a1 1 0 10-2 0v1a1 1 0 102 0V3zM15.657 5.757a1 1 0 00-1.414-1.414l-.707.707a1 1 0 001.414 1.414l.707-.707zM18 10a1 1 0 01-1 1h-1a1 1 0 110-2h1a1 1 0 011 1zM5.05 6.464A1 1 0 106.464 5.05l-.707-.707a1 1 0 00-1.414 1.414l.707.707zM4 11a1 1 0 100-2H3a1 1 0 000 2h1zM10 18a1 1 0 001-1v-1a1 1 0 10-2 0v1a1 1 0 001 1z"/>
            </svg>
            <span class="text-sm font-medium text-indigo-400">AI 综合回答</span>
          </div>
          <div class="bg-gray-900/50 rounded-2xl border border-gray-800 p-6">
            <StreamingAnswer
              :content="displayAnswer(turn, i)"
              :sources="displaySources(turn, i)"
              :is-streaming="i === turns.length - 1 && isStreaming"
            />
          </div>
        </div>

        <!-- Sources section -->
        <div v-if="displaySources(turn, i).length > 0" class="mb-8">
          <div class="flex items-center gap-2 mb-4">
            <svg class="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
            </svg>
            <span class="text-sm font-medium text-gray-400">搜索结果</span>
            <span class="text-xs text-gray-600">({{ displaySources(turn, i).length }})</span>
          </div>
          <div class="space-y-3">
            <SourceCard
              v-for="(source, j) in displaySources(turn, i)"
              :key="j"
              :source="source"
              :index="j + 1"
            />
          </div>
        </div>

        <!-- Follow-ups -->
        <FollowUpQuestions
          v-if="displayFollowUps(turn, i).length > 0"
          :questions="displayFollowUps(turn, i)"
          @select="handleFollowUp"
        />
      </div>
    </div>
  </div>
</template>
