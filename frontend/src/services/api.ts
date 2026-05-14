import type { Conversation } from '../types'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')
export const TEST_TOKEN_STORAGE_KEY = 'me1ody_test_token'

export function apiUrl(path: string): string {
  return `${API_BASE_URL}${path}`
}

export function getTestToken(): string {
  return localStorage.getItem(TEST_TOKEN_STORAGE_KEY) || ''
}

export function setTestToken(token: string): void {
  const trimmed = token.trim()
  if (trimmed) localStorage.setItem(TEST_TOKEN_STORAGE_KEY, trimmed)
  else localStorage.removeItem(TEST_TOKEN_STORAGE_KEY)
}

export function apiHeaders(extra: HeadersInit = {}): HeadersInit {
  const token = getTestToken()
  return {
    ...extra,
    ...(token ? { 'X-Test-Token': token } : {}),
  }
}

export async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  return fetch(apiUrl(path), {
    ...init,
    headers: apiHeaders(init.headers || {}),
  })
}

export async function fetchConversations(): Promise<Conversation[]> {
  const res = await apiFetch('/api/history')
  if (!res.ok) throw new Error('Failed to fetch history')
  return res.json()
}

export async function fetchConversation(id: string) {
  const res = await apiFetch(`/api/history/${id}`)
  if (!res.ok) throw new Error('Failed to fetch conversation')
  return res.json()
}

export async function fetchSuggestions(q: string): Promise<string[]> {
  if (!q || q.length < 2) return []
  const res = await apiFetch(`/api/suggest?q=${encodeURIComponent(q)}`)
  if (!res.ok) return []
  const data = await res.json()
  return data.suggestions || []
}
