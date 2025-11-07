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
  mode: 'story' | 'ad'
  prompt: string
  num_characters: 1 | 2 | 3
  num_cuts: number
  art_style: string
  music_genre: string
  characters?: CharacterInput[]
  reference_images?: string[]
  lora_strength?: number
  voice_id?: string
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
