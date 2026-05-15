<script setup lang="ts">
import { ref, onMounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import SearchBar from './SearchBar.vue'
import StreamingAnswer from './StreamingAnswer.vue'
import SourceCard from './SourceCard.vue'
import FollowUpQuestions from './FollowUpQuestions.vue'
import PipelineStatus from './PipelineStatus.vue'
import { useSearch } from '../composables/useSearch'
import {
  deleteConversation,
  fetchConversation,
  fetchSharedConversation,
  setConversationFavorite,
} from '../services/api'
import type { CitationAudit, Conversation, PipelineStep, Source, Message } from '../types'

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
const shareId = ref<string | null>(null)
const isFavorite = ref(false)
const statusMessage = ref('')
const isSharedView = ref(false)

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
  abortSearch,
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
  if (conversationId.value) {
    try {
      const data = await fetchConversation(conversationId.value)
      shareId.value = data.share_id
      isFavorite.value = data.is_favorite
    } catch { /* keep streamed turn even if metadata refresh fails */ }
  }

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
    applyConversation(data)
  } catch { /* conversation not found */ }
}

async function loadSharedConversation(id: string) {
  try {
    const data = await fetchSharedConversation(id)
    isSharedView.value = true
    applyConversation(data)
  } catch { /* shared conversation not found */ }
}

function applyConversation(data: Conversation) {
    conversationId.value = data.id
    shareId.value = data.share_id
    isFavorite.value = data.is_favorite
    turns.value = []
    const messages: Message[] = data.messages || []
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
}

onMounted(() => {
  const id = route.params.id as string
  const shared = route.params.shareId as string
  const q = route.query.q as string
  if (shared) loadSharedConversation(shared)
  else if (id) loadConversation(id)
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

function currentShareLink(): string {
  return shareId.value
    ? `${window.location.origin}/share/${shareId.value}`
    : window.location.href
}

function turnMarkdown(turn: ConversationTurn): string {
  const sourceLines = turn.sources.map((source, index) => (
    `${index + 1}. ${source.title}\n   ${source.url}\n   ${source.snippet}`
  )).join('\n\n')
  return `# ${turn.query}\n\n${turn.answer}\n\n## Sources\n\n${sourceLines || 'No sources'}\n`
}

async function copyAnswer(turn: ConversationTurn) {
  await navigator.clipboard.writeText(turn.answer)
  statusMessage.value = '回答已复制'
}

async function copyShareLink() {
  await navigator.clipboard.writeText(currentShareLink())
  statusMessage.value = '分享链接已复制'
}

function downloadMarkdown(turn: ConversationTurn) {
  const blob = new Blob([turnMarkdown(turn)], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `${turn.query.slice(0, 24) || 'answer'}.md`
  link.click()
  URL.revokeObjectURL(url)
  statusMessage.value = 'Markdown 已导出'
}

async function toggleFavorite() {
  if (!conversationId.value || isSharedView.value) return
  const next = !isFavorite.value
  await setConversationFavorite(conversationId.value, next)
  isFavorite.value = next
  statusMessage.value = next ? '已收藏' : '已取消收藏'
}

async function removeConversation() {
  if (!conversationId.value || isSharedView.value) return
  if (!confirm('确定删除这条历史记录吗？')) return
  await deleteConversation(conversationId.value)
  router.push('/')
}

function stopSearch() {
  abortSearch()
}

function regenerate(turn: ConversationTurn) {
  if (isStreaming.value) return
  handleSearch(turn.query)
}
</script>

<template>
  <div class="max-w-4xl mx-auto px-3 sm:px-4 py-4 sm:py-6">
    <!-- Sticky search bar -->
    <div class="sticky top-14 z-40 bg-gray-950/90 backdrop-blur-md py-4 -mx-4 px-4">
      <SearchBar compact @search="handleSearch" />
    </div>

    <!-- Error -->
    <div v-if="error" class="mt-4 p-4 rounded-xl bg-red-900/20 border border-red-800 text-red-400 text-sm">
      {{ error }}
    </div>
    <div v-if="statusMessage" class="mt-4 p-3 rounded-xl bg-emerald-900/20 border border-emerald-800 text-emerald-300 text-sm">
      {{ statusMessage }}
    </div>

    <!-- Conversation turns -->
    <div class="mt-6 space-y-12">
      <div v-for="(turn, i) in turns" :key="i">
        <!-- User query -->
        <div class="mb-6 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <h2 class="text-xl font-semibold text-gray-100 break-words">{{ turn.query }}</h2>
          <div v-if="i === turns.length - 1" class="flex flex-wrap gap-2">
            <button
              v-if="isStreaming"
              @click="stopSearch"
              class="px-3 py-1.5 rounded-lg border border-red-800/70 text-xs text-red-300 hover:bg-red-500/10"
            >
              停止
            </button>
            <button
              v-else-if="turn.answer"
              @click="regenerate(turn)"
              class="px-3 py-1.5 rounded-lg border border-gray-700 text-xs text-gray-300 hover:border-indigo-500"
            >
              重新生成
            </button>
            <button
              v-if="conversationId && !isSharedView"
              @click="toggleFavorite"
              class="px-3 py-1.5 rounded-lg border border-gray-700 text-xs text-gray-300 hover:border-amber-500"
            >
              {{ isFavorite ? '取消收藏' : '收藏' }}
            </button>
            <button
              v-if="shareId"
              @click="copyShareLink"
              class="px-3 py-1.5 rounded-lg border border-gray-700 text-xs text-gray-300 hover:border-indigo-500"
            >
              分享
            </button>
            <button
              v-if="conversationId && !isSharedView"
              @click="removeConversation"
              class="px-3 py-1.5 rounded-lg border border-gray-700 text-xs text-gray-300 hover:border-red-500"
            >
              删除
            </button>
          </div>
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
            <div v-if="displayAnswer(turn, i) && !(i === turns.length - 1 && isStreaming)" class="ml-auto flex gap-2">
              <button
                @click="copyAnswer(turn)"
                class="px-2.5 py-1 rounded-lg border border-gray-700 text-xs text-gray-400 hover:text-gray-200"
              >
                复制
              </button>
              <button
                @click="downloadMarkdown(turn)"
                class="px-2.5 py-1 rounded-lg border border-gray-700 text-xs text-gray-400 hover:text-gray-200"
              >
                导出 MD
              </button>
            </div>
          </div>
          <div class="bg-gray-900/50 rounded-2xl border border-gray-800 p-4 sm:p-6">
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
