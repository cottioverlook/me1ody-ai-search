<script setup lang="ts">
import { useRouter } from 'vue-router'
import SearchBar from './SearchBar.vue'

const router = useRouter()

function handleSearch(query: string) {
  router.push({ path: '/search', query: { q: query } })
}
</script>

<template>
  <div class="flex flex-col items-center justify-center min-h-[80vh] px-4">
    <div class="text-center mb-12">
      <div class="flex items-center justify-center gap-3 mb-4">
        <svg class="w-12 h-12 text-indigo-500" viewBox="0 0 32 32" fill="currentColor">
          <circle cx="16" cy="16" r="14" fill="#6366f1" />
          <text x="16" y="22" text-anchor="middle" fill="white" font-size="18" font-weight="bold">M</text>
        </svg>
      </div>
      <h1 class="text-5xl font-bold mb-3 bg-gradient-to-r from-indigo-400 via-purple-400 to-pink-400 bg-clip-text text-transparent">
        Me1ody
      </h1>
      <p class="text-lg text-gray-400">AI 驱动的智能搜索引擎 &middot; 像 Perplexity 一样搜索</p>
    </div>

    <SearchBar @search="handleSearch" />

    <div class="mt-10 flex flex-wrap gap-3 justify-center max-w-2xl">
      <button
        v-for="hint in [
          '什么是量子计算',
          '2026 年 AI 发展趋势',
          '如何学习 Rust 编程',
          'LangChain vs LlamaIndex 对比',
          'React Server Components 工作原理',
        ]"
        :key="hint"
        @click="handleSearch(hint)"
        class="px-4 py-2.5 rounded-full border border-gray-700/50 text-sm text-gray-400 hover:border-indigo-500/50 hover:text-indigo-400 hover:bg-indigo-500/5 transition-all"
      >
        {{ hint }}
      </button>
    </div>

    <div class="mt-16 text-center text-xs text-gray-600">
      <p>由 DeepSeek V4 + Tavily Search + LangChain 驱动</p>
    </div>
  </div>
</template>
