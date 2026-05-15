import { ref } from 'vue'
import type { CitationAudit, PipelineStage, PipelineStep, Source } from '../types'
import { apiHeaders, apiUrl } from '../services/api'

const DEFAULT_STEPS: PipelineStep[] = [
  { stage: 'search', label: 'Tavily 搜索召回', status: 'pending' },
  { stage: 'process', label: '结果清洗与质量评分', status: 'pending' },
  { stage: 'rag', label: '向量检索与重排序', status: 'pending' },
  { stage: 'answer', label: 'DeepSeek 综合生成', status: 'pending' },
  { stage: 'audit', label: '引用审计', status: 'pending' },
]

function createDefaultSteps(): PipelineStep[] {
  return DEFAULT_STEPS.map((step) => ({ ...step }))
}

export function useSearch() {
  const answer = ref('')
  const sources = ref<Source[]>([])
  const followUps = ref<string[]>([])
  const citationAudit = ref<CitationAudit | null>(null)
  const pipelineSteps = ref<PipelineStep[]>(createDefaultSteps())
  const isStreaming = ref(false)
  const isWaiting = ref(false)
  const conversationId = ref<string | null>(null)
  const error = ref('')
  let controller: AbortController | null = null

  function updateStage(
    stage: PipelineStage,
    status: PipelineStep['status'],
    label?: string,
    durationMs?: number,
  ) {
    pipelineSteps.value = pipelineSteps.value.map((step) => {
      if (step.stage === stage) {
        return { ...step, status, label: label || step.label, duration_ms: durationMs ?? step.duration_ms }
      }
      return step
    })
  }

  async function search(query: string, convId?: string | null) {
    answer.value = ''
    sources.value = []
    followUps.value = []
    citationAudit.value = null
    pipelineSteps.value = createDefaultSteps()
    isStreaming.value = true
    isWaiting.value = true
    error.value = ''
    controller?.abort()
    controller = new AbortController()

    try {
      const response = await fetch(apiUrl('/api/search'), {
        method: 'POST',
        headers: apiHeaders({ 'Content-Type': 'application/json' }),
        signal: controller.signal,
        body: JSON.stringify({
          query,
          conversation_id: convId || undefined,
        }),
      })

      if (!response.ok) {
        let detail = ''
        try {
          const errorBody = await response.clone().json()
          detail = errorBody.detail ? `：${errorBody.detail}` : ''
        } catch {
          // ignore non-JSON error responses
        }
        if (response.status === 401) {
          throw new Error('测试密码不正确或未填写，请点击右上角钥匙图标设置。')
        }
        if (response.status === 429) {
          throw new Error('请求过于频繁，请稍后再试。')
        }
        throw new Error(`Search failed: ${response.status}${detail}`)
      }

      const reader = response.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        isWaiting.value = false
        buffer += decoder.decode(value, { stream: true })

        const lines = buffer.split('\n')
        buffer = lines.pop() ?? ''

        let currentEvent = ''
        for (const line of lines) {
          if (line.startsWith('event: ')) {
            currentEvent = line.slice(7).trim()
          } else if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              if (currentEvent === 'sources') {
                sources.value = data.sources
              } else if (currentEvent === 'token') {
                answer.value += data.text
              } else if (currentEvent === 'stage') {
                updateStage(data.stage, data.status, data.label, data.duration_ms)
              } else if (currentEvent === 'citation_audit') {
                citationAudit.value = data
              } else if (currentEvent === 'followup') {
                followUps.value = data.questions
              } else if (currentEvent === 'done') {
                conversationId.value = data.conversation_id
                isStreaming.value = false
              }
            } catch {
              // skip malformed JSON
            }
          }
        }
      }
    } catch (e) {
      if (e instanceof DOMException && e.name === 'AbortError') {
        error.value = '搜索已停止'
      } else {
        error.value = e instanceof Error ? e.message : 'Unknown error'
      }
    } finally {
      isStreaming.value = false
      isWaiting.value = false
      controller = null
    }
  }

  function abortSearch() {
    controller?.abort()
  }

  return {
    answer,
    sources,
    followUps,
    citationAudit,
    pipelineSteps,
    isStreaming,
    isWaiting,
    conversationId,
    error,
    search,
    abortSearch,
  }
}
