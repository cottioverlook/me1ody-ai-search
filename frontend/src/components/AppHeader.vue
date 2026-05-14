<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import type { Conversation } from '../types'
import { fetchConversations, getTestToken, setTestToken } from '../services/api'

const router = useRouter()
const showHistory = ref(false)
const showTokenPanel = ref(false)
const conversations = ref<Conversation[]>([])
const tokenInput = ref(getTestToken())

async function toggleHistory() {
  if (!showHistory.value) {
    try {
      conversations.value = await fetchConversations()
    } catch {
      conversations.value = []
    }
  }
  showHistory.value = !showHistory.value
}

function openConversation(id: string) {
  showHistory.value = false
  router.push(`/search/${id}`)
}

function goHome() {
  router.push('/')
}

function saveToken() {
  setTestToken(tokenInput.value)
  tokenInput.value = getTestToken()
  showTokenPanel.value = false
}

function clearToken() {
  tokenInput.value = ''
  setTestToken('')
}
</script>

<template>
  <header class="sticky top-0 z-50 border-b border-gray-800/50 bg-gray-950/80 backdrop-blur-xl">
    <div class="max-w-5xl mx-auto px-4 h-14 flex items-center justify-between">
      <button @click="goHome" class="flex items-center gap-2.5 hover:opacity-80 transition-opacity">
        <svg class="w-7 h-7" viewBox="0 0 32 32" fill="currentColor">
          <circle cx="16" cy="16" r="14" fill="#6366f1" />
          <text x="16" y="22" text-anchor="middle" fill="white" font-size="18" font-weight="bold">M</text>
        </svg>
        <span class="text-lg font-semibold tracking-tight bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
          Me1ody
        </span>
      </button>

      <div class="flex items-center gap-2">
        <div class="relative">
          <button
            @click="showTokenPanel = !showTokenPanel"
            class="p-2 rounded-lg hover:bg-gray-800 transition-colors text-gray-400 hover:text-gray-200"
            title="测试密码"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H3v-4.586l5.257-5.257A6 6 0 1121 9z" />
            </svg>
          </button>

          <div
            v-if="showTokenPanel"
            class="absolute right-0 top-full mt-2 w-80 bg-gray-900 border border-gray-700/50 rounded-2xl shadow-2xl p-4"
          >
            <div class="text-sm font-medium text-gray-200 mb-2">测试密码</div>
            <input
              v-model="tokenInput"
              type="password"
              class="w-full rounded-lg border border-gray-700 bg-gray-950 px-3 py-2 text-sm text-gray-100 outline-none focus:border-indigo-500"
              placeholder="输入你分发给同学的测试密码"
              @keydown.enter="saveToken"
            />
            <div class="mt-3 flex justify-end gap-2">
              <button
                @click="clearToken"
                class="px-3 py-1.5 rounded-lg border border-gray-700 text-xs text-gray-400 hover:text-gray-200"
              >
                清除
              </button>
              <button
                @click="saveToken"
                class="px-3 py-1.5 rounded-lg bg-indigo-600 text-xs text-white hover:bg-indigo-500"
              >
                保存
              </button>
            </div>
          </div>
        </div>

        <div class="relative">
          <button
            @click="toggleHistory"
            class="p-2 rounded-lg hover:bg-gray-800 transition-colors text-gray-400 hover:text-gray-200"
            title="对话历史"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </button>

          <div
            v-if="showHistory"
            class="absolute right-0 top-full mt-2 w-80 max-h-96 overflow-y-auto bg-gray-900 border border-gray-700/50 rounded-2xl shadow-2xl backdrop-blur-xl"
          >
            <div class="p-4 text-sm font-medium text-gray-300 border-b border-gray-800">对话历史</div>
            <div v-if="conversations.length === 0" class="p-6 text-sm text-gray-500 text-center">
              暂无历史记录
            </div>
            <button
              v-for="conv in conversations"
              :key="conv.id"
              @click="openConversation(conv.id)"
              class="w-full text-left px-4 py-3.5 hover:bg-gray-800/50 transition-colors border-b border-gray-800/30 last:border-0"
            >
              <div class="text-sm text-gray-200 truncate">{{ conv.title }}</div>
              <div class="text-xs text-gray-500 mt-1">{{ new Date(conv.created_at).toLocaleString('zh-CN') }}</div>
            </button>
          </div>
        </div>
      </div>
    </div>
  </header>
</template>
