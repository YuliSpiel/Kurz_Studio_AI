/**
 * API client for AutoShorts backend.
 */

const API_BASE = '/api'

// ============ Custom Errors ============
export class AuthenticationError extends Error {
  constructor(message: string = 'Authentication required') {
    super(message)
    this.name = 'AuthenticationError'
  }
}

// ============ Auth Types ============
export interface RegisterRequest {
  email: string
  username: string
  password: string
}

export interface LoginRequest {
  email: string
  password: string
}

export interface UserResponse {
  id: string
  email: string
  username: string
  credits: number
  subscription_tier: string
  created_at: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  user: UserResponse
}

// ============ Library Types ============
export interface RunListItem {
  id: string
  run_id: string
  prompt: string
  mode: string
  state: string
  progress: number
  video_url: string | null
  thumbnail_url: string | null
  created_at: string
}

interface CharacterInput {
  name: string
  gender: 'male' | 'female' | 'other'
  role: string
  personality: string
  appearance: string
  reference_image?: string
}

interface RunSpec {
  mode: 'general' | 'story' | 'ad'
  prompt: string
  num_characters: 1 | 2 | 3
  num_cuts: number
  art_style: string
  music_genre: string
  characters?: CharacterInput[]
  reference_images?: string[]
  lora_strength?: number
  voice_id?: string
  video_title?: string
  layout_config?: Record<string, any>
  // Test mode flags
  stub_image_mode?: boolean
  stub_music_mode?: boolean
  stub_tts_mode?: boolean
  // Plot review mode
  review_mode?: boolean
}

interface RunStatus {
  run_id: string
  state: string
  progress: number
  artifacts: Record<string, any>
  logs: string[]
}

export async function createRun(spec: RunSpec): Promise<RunStatus> {
  const token = localStorage.getItem('auth_token')

  const response = await fetch(`${API_BASE}/runs`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token && { 'Authorization': `Bearer ${token}` }),
    },
    body: JSON.stringify(spec),
  })

  if (!response.ok) {
    if (response.status === 401) {
      throw new AuthenticationError('로그인이 필요합니다')
    }
    throw new Error(`Failed to create run: ${response.statusText}`)
  }

  return response.json()
}

export async function getRun(runId: string): Promise<RunStatus> {
  const response = await fetch(`${API_BASE}/runs/${encodeURIComponent(runId)}`)

  if (!response.ok) {
    throw new Error(`Failed to get run: ${response.statusText}`)
  }

  return response.json()
}

export async function uploadReferenceImage(file: File): Promise<string> {
  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch(`${API_BASE}/uploads`, {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    throw new Error(`Failed to upload image: ${response.statusText}`)
  }

  const data = await response.json()
  return data.filename
}

export interface Font {
  id: string
  name: string
  path: string
}

export async function getAvailableFonts(): Promise<Font[]> {
  const response = await fetch(`${API_BASE}/fonts`)

  if (!response.ok) {
    throw new Error(`Failed to get fonts: ${response.statusText}`)
  }

  const data = await response.json()
  return data.fonts || []
}

export interface PromptEnhancementResult {
  enhanced_prompt: string
  suggested_title: string
  suggested_plot_outline: string
  suggested_num_cuts: number
  suggested_art_style: string
  suggested_music_genre: string
  suggested_num_characters: number
  suggested_narrative_tone: string
  suggested_plot_structure: string
  reasoning: string
}

export async function enhancePrompt(
  originalPrompt: string,
  mode: string = 'general'
): Promise<PromptEnhancementResult> {
  const response = await fetch('/api/v1/enhance-prompt', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      original_prompt: originalPrompt,
      mode: mode,
    }),
  })

  if (!response.ok) {
    const errorText = await response.text()
    console.error('[ENHANCE API] Error response:', response.status, errorText)
    throw new Error(`Failed to enhance prompt (${response.status}): ${response.statusText}`)
  }

  const result = await response.json()
  console.log('[ENHANCE API] Success:', result)
  return result
}

export interface Character {
  char_id: string
  name: string
  description: string
}

export interface PlotJsonData {
  run_id: string
  plot: {
    title?: string
    bgm_prompt?: string
    characters?: Character[]
    scenes: Array<{
      scene_id: string
      image_prompt: string
      text: string
      speaker: string
    }>
  }
  mode: string
}

export async function getPlotJson(runId: string): Promise<PlotJsonData> {
  const response = await fetch(`${API_BASE}/v1/runs/${encodeURIComponent(runId)}/plot-json`)

  if (!response.ok) {
    throw new Error(`Failed to get plot JSON: ${response.statusText}`)
  }

  return response.json()
}

export async function confirmPlot(runId: string, editedPlot?: any): Promise<void> {
  const token = localStorage.getItem('auth_token')
  if (!token) {
    throw new AuthenticationError('로그인이 필요합니다')
  }

  const body = editedPlot ? { edited_plot: editedPlot } : {}

  const response = await fetch(`${API_BASE}/v1/runs/${encodeURIComponent(runId)}/plot-confirm`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify(body),
  })

  if (response.status === 401) {
    throw new AuthenticationError('로그인이 필요합니다')
  }

  if (!response.ok) {
    throw new Error(`Failed to confirm plot: ${response.statusText}`)
  }
}

export async function regeneratePlot(runId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/v1/runs/${encodeURIComponent(runId)}/plot-regenerate`, {
    method: 'POST',
  })

  if (!response.ok) {
    throw new Error(`Failed to regenerate plot: ${response.statusText}`)
  }
}

export async function confirmLayout(runId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/v1/runs/${encodeURIComponent(runId)}/layout-confirm`, {
    method: 'POST',
  })

  if (!response.ok) {
    throw new Error(`Failed to confirm layout: ${response.statusText}`)
  }
}

export async function regenerateLayout(runId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/v1/runs/${encodeURIComponent(runId)}/layout-regenerate`, {
    method: 'POST',
  })

  if (!response.ok) {
    throw new Error(`Failed to regenerate layout: ${response.statusText}`)
  }
}

export interface LayoutConfig {
  use_title_block: boolean
  title_bg_color: string
  title_font_size: number
  subtitle_font_size: number
  title_font: string
  subtitle_font: string
}

export interface LayoutConfigData {
  run_id: string
  layout_config: LayoutConfig
  title: string
}

export async function getLayoutConfig(runId: string): Promise<LayoutConfigData> {
  const response = await fetch(`${API_BASE}/v1/runs/${encodeURIComponent(runId)}/layout-config`)

  if (!response.ok) {
    throw new Error(`Failed to get layout config: ${response.statusText}`)
  }

  return response.json()
}

export async function confirmLayoutWithConfig(
  runId: string,
  layoutConfig?: LayoutConfig,
  title?: string
): Promise<void> {
  const body: any = {}
  if (layoutConfig) body.layout_config = layoutConfig
  if (title !== undefined) body.title = title

  const response = await fetch(`${API_BASE}/v1/runs/${encodeURIComponent(runId)}/layout-confirm`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  })

  if (!response.ok) {
    throw new Error(`Failed to confirm layout: ${response.statusText}`)
  }
}

// ============ Auth API Functions ============

export async function register(data: RegisterRequest): Promise<UserResponse> {
  const response = await fetch(`${API_BASE}/auth/register`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Registration failed')
  }

  return response.json()
}

export async function login(data: LoginRequest): Promise<TokenResponse> {
  const response = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Login failed')
  }

  return response.json()
}

// ============ Library API Functions ============

export async function getMyRuns(): Promise<RunListItem[]> {
  const token = localStorage.getItem('auth_token')

  if (!token) {
    throw new Error('Not authenticated')
  }

  const response = await fetch(`${API_BASE}/runs`, {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || 'Failed to fetch runs')
  }

  return response.json()
}

export async function deleteRun(runId: string): Promise<void> {
  const token = localStorage.getItem('auth_token')

  if (!token) {
    throw new Error('Not authenticated')
  }

  const response = await fetch(`${API_BASE}/runs/${encodeURIComponent(runId)}`, {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || 'Failed to delete run')
  }
}

export async function cancelRun(runId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/v1/runs/${encodeURIComponent(runId)}/cancel`, {
    method: 'POST',
  })

  if (!response.ok) {
    throw new Error(`Failed to cancel run: ${response.statusText}`)
  }
}
