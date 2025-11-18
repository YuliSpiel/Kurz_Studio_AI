/**
 * API client for AutoShorts backend.
 */

const API_BASE = '/api'

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
  const response = await fetch(`${API_BASE}/runs`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(spec),
  })

  if (!response.ok) {
    throw new Error(`Failed to create run: ${response.statusText}`)
  }

  return response.json()
}

export async function getRun(runId: string): Promise<RunStatus> {
  const response = await fetch(`${API_BASE}/runs/${runId}`)

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
  const response = await fetch(`${API_BASE}/v1/enhance-prompt`, {
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
    throw new Error(`Failed to enhance prompt: ${response.statusText}`)
  }

  return response.json()
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
  const response = await fetch(`${API_BASE}/v1/runs/${runId}/plot-json`)

  if (!response.ok) {
    throw new Error(`Failed to get plot JSON: ${response.statusText}`)
  }

  return response.json()
}

export async function confirmPlot(runId: string, editedPlot?: any): Promise<void> {
  const body = editedPlot ? { edited_plot: editedPlot } : {}

  const response = await fetch(`${API_BASE}/v1/runs/${runId}/plot-confirm`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  })

  if (!response.ok) {
    throw new Error(`Failed to confirm plot: ${response.statusText}`)
  }
}

export async function regeneratePlot(runId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/v1/runs/${runId}/plot-regenerate`, {
    method: 'POST',
  })

  if (!response.ok) {
    throw new Error(`Failed to regenerate plot: ${response.statusText}`)
  }
}
