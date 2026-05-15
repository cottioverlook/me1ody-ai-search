import type { Conversation } from '../types'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')
export const TEST_TOKEN_STORAGE_KEY = 'me1ody_test_token'
export const USER_ID_STORAGE_KEY = 'me1ody_user_id'
let memoryUserId = ''
let memoryTestToken = ''

function storageGet(key: string): string {
  try {
    return window.localStorage.getItem(key) || ''
  } catch {
    return ''
  }
}

function storageSet(key: string, value: string): void {
  try {
    if (value) window.localStorage.setItem(key, value)
    else window.localStorage.removeItem(key)
  } catch {
    if (key === USER_ID_STORAGE_KEY) memoryUserId = value
    if (key === TEST_TOKEN_STORAGE_KEY) memoryTestToken = value
  }
}

function createUserId(): string {
  const webCrypto = globalThis.crypto
  if (webCrypto && typeof webCrypto.randomUUID === 'function') return webCrypto.randomUUID()
  return `user-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

export function getUserId(): string {
  let userId = storageGet(USER_ID_STORAGE_KEY) || memoryUserId
  if (!userId) {
    userId = createUserId()
    storageSet(USER_ID_STORAGE_KEY, userId)
  }
  return userId
}

export function apiUrl(path: string): string {
  return `${API_BASE_URL}${path}`
}

export function getTestToken(): string {
  return storageGet(TEST_TOKEN_STORAGE_KEY) || memoryTestToken
}

export function setTestToken(token: string): void {
  const trimmed = token.trim()
  storageSet(TEST_TOKEN_STORAGE_KEY, trimmed)
}

export function apiHeaders(extra: HeadersInit = {}): HeadersInit {
  const token = getTestToken()
  return {
    ...extra,
    'X-User-Id': getUserId(),
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

export async function fetchSharedConversation(shareId: string) {
  const res = await apiFetch(`/api/share/${shareId}`)
  if (!res.ok) throw new Error('Failed to fetch shared conversation')
  return res.json()
}

export async function deleteConversation(id: string): Promise<void> {
  const res = await apiFetch(`/api/history/${id}`, { method: 'DELETE' })
  if (!res.ok) throw new Error('Failed to delete conversation')
}

export async function setConversationFavorite(id: string, isFavorite: boolean): Promise<Conversation> {
  const res = await apiFetch(`/api/history/${id}/favorite`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ is_favorite: isFavorite }),
  })
  if (!res.ok) throw new Error('Failed to update favorite')
  return res.json()
}

export async function fetchSuggestions(q: string): Promise<string[]> {
  if (!q || q.length < 2) return []
  const res = await apiFetch(`/api/suggest?q=${encodeURIComponent(q)}`)
  if (!res.ok) return []
  const data = await res.json()
  return data.suggestions || []
}
