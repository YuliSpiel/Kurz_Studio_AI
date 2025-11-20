import { useState, useEffect } from 'react'
import { enhancePrompt, createRun, PromptEnhancementResult, getPlotJson, confirmPlot, regeneratePlot, PlotJsonData, Character } from '../api/client'

interface HeroChatProps {
  onSubmit: (prompt: string, mode: 'general' | 'story' | 'ad') => void
  onEnhancementReady?: (enhancement: PromptEnhancementResult, originalPrompt: string) => void
  onRunCreated?: (runId: string, reviewMode: boolean) => void
  disabled?: boolean
}

interface Scene {
  scene_id: string
  image_prompt: string
  text: string
  speaker: string
}

const ROTATING_WORDS = ['Epic', 'Cool', 'Fire', 'Viral', 'Neat', 'Bold']
const COLORS = ['#6f9fa0', '#7189a0', '#c9a989'] // 짙게 한 버전

const PLACEHOLDERS = {
  general: ['2030 직장인 공감 썰', '세계 5대 명소 추천'],
  story: ['소꿉친구랑 결혼 골인한 이야기', '아기 고양이의 우주 모험'],
  ad: ['상품 페이지 링크를 입력하세요']
}

function HeroChat({ onSubmit, onEnhancementReady, onRunCreated, disabled = false }: HeroChatProps) {
  const [prompt, setPrompt] = useState('')
  const [selectedMode, setSelectedMode] = useState<'general' | 'story' | 'ad'>('general')
  const [currentWordIndex, setCurrentWordIndex] = useState(0)
  const [isAnimating, setIsAnimating] = useState(false)
  const [typedPlaceholder, setTypedPlaceholder] = useState('')
  const [currentPlaceholderText, setCurrentPlaceholderText] = useState('')

  // Enhancement states
  const [isEnhancing, setIsEnhancing] = useState(false)
  const [enhancementResult, setEnhancementResult] = useState<PromptEnhancementResult | null>(null)
  const [showEnhancementModal, setShowEnhancementModal] = useState(false)
  const [showEnhanceErrorModal, setShowEnhanceErrorModal] = useState(false)
  const [enhanceError, setEnhanceError] = useState<string>('')

  // Editable enhancement values
  const [editedTitle, setEditedTitle] = useState('')
  const [editedPlot, setEditedPlot] = useState('')
  const [editedNumCuts, setEditedNumCuts] = useState(3)
  const [editedNumCharacters, setEditedNumCharacters] = useState(1)
  const [editedArtStyle, setEditedArtStyle] = useState('')
  const [editedMusicGenre, setEditedMusicGenre] = useState('')
  const [editedNarrativeTone, setEditedNarrativeTone] = useState('')
  const [editedPlotStructure, setEditedPlotStructure] = useState('')

  // Plot review mode states
  const [modalMode, setModalMode] = useState<'enhancement' | 'plot-review'>('enhancement')
  const [currentRunId, setCurrentRunId] = useState<string | null>(null)
  const [plotData, setPlotData] = useState<PlotJsonData | null>(null)
  const [scenes, setScenes] = useState<Scene[]>([])
  const [characters, setCharacters] = useState<Character[]>([])
  const [plotReviewTab, setPlotReviewTab] = useState<'characters' | 'scenes'>('characters')
  const [isLoadingPlot, setIsLoadingPlot] = useState(false)
  const [isConfirmingPlot, setIsConfirmingPlot] = useState(false)
  const [isRegeneratingPlot, setIsRegeneratingPlot] = useState(false)
  const [hasEditedPlot, setHasEditedPlot] = useState(false)
  const [currentAnimFrame, setCurrentAnimFrame] = useState(1)

  // Test mode states
  const [showTestMode, setShowTestMode] = useState(false)
  const [stubImageMode, setStubImageMode] = useState(false)
  const [stubMusicMode, setStubMusicMode] = useState(false)
  const [stubTTSMode, setStubTTSMode] = useState(false)

  // Rotating words animation
  useEffect(() => {
    const interval = setInterval(() => {
      setIsAnimating(true)
      setTimeout(() => {
        setCurrentWordIndex((prev) => (prev + 1) % ROTATING_WORDS.length)
        setIsAnimating(false)
      }, 300)
    }, 3000)

    return () => clearInterval(interval)
  }, [])

  // Typing effect for placeholder
  useEffect(() => {
    if (!currentPlaceholderText) return

    // Ad mode: no typing effect, show immediately
    if (selectedMode === 'ad') {
      setTypedPlaceholder(currentPlaceholderText)
      return
    }

    let currentCharIndex = 0
    setTypedPlaceholder('')

    // Typing animation
    const typingInterval = setInterval(() => {
      if (currentCharIndex <= currentPlaceholderText.length) {
        setTypedPlaceholder(currentPlaceholderText.slice(0, currentCharIndex))
        currentCharIndex++
      } else {
        clearInterval(typingInterval)
        // Stay on completed text - don't switch automatically
      }
    }, 100) // Type one character every 100ms

    return () => clearInterval(typingInterval)
  }, [currentPlaceholderText, selectedMode])

  // Initialize with random placeholder on mount
  useEffect(() => {
    const placeholders = PLACEHOLDERS[selectedMode]
    const randomIndex = Math.floor(Math.random() * placeholders.length)
    setCurrentPlaceholderText(placeholders[randomIndex])
  }, [])

  // Test mode toggle with Option/Alt + Shift + T
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.altKey && e.shiftKey && e.key === 'T') {
        e.preventDefault()
        setShowTestMode(prev => !prev)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  // Animation for plot loading
  useEffect(() => {
    if (!isLoadingPlot) return

    const interval = setInterval(() => {
      setCurrentAnimFrame(prev => (prev % 9) + 1) // Loop from 1 to 9
    }, 150) // Change frame every 150ms

    return () => clearInterval(interval)
  }, [isLoadingPlot])

  const handleModeChange = (mode: 'general' | 'story' | 'ad') => {
    const placeholders = PLACEHOLDERS[mode]
    const randomIndex = Math.floor(Math.random() * placeholders.length)
    setCurrentPlaceholderText(placeholders[randomIndex])
    setSelectedMode(mode)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!prompt.trim() || disabled) return

    // For general mode, trigger AI enhancement
    if (selectedMode === 'general') {
      // Prevent duplicate calls while already enhancing
      if (isEnhancing) {
        console.log('[ENHANCE] Already enhancing, ignoring duplicate call')
        return
      }

      // Show modal immediately with loading state
      setShowEnhancementModal(true)
      setIsEnhancing(true)

      try {
        console.log('[ENHANCE] Requesting AI analysis...')
        const result = await enhancePrompt(prompt, 'general')

        // Check if this is a fallback response (contains error message in reasoning)
        if (result.reasoning && (result.reasoning.includes('AI 분석 실패') || result.reasoning.includes('시스템 오류'))) {
          console.warn('[ENHANCE] Received fallback response from backend:', result.reasoning)
          // Still show the result - backend already provided fallback values
        }

        setEnhancementResult(result)
        setIsEnhancing(false)
        return // 성공
      } catch (error: any) {
        console.error('[ENHANCE] Network or parse error:', error)

        // Network completely failed - backend didn't respond
        // This should be very rare since backend has its own fallback
        setIsEnhancing(false)
        setShowEnhancementModal(false)

        // Show error modal instead of alert
        setEnhanceError(error?.message || String(error))
        setShowEnhanceErrorModal(true)
      }
    } else {
      // For story/ad modes, proceed directly
      onSubmit(prompt, selectedMode)
    }
  }

  // Initialize editable state when enhancement result arrives
  useEffect(() => {
    if (enhancementResult) {
      setEditedTitle(enhancementResult.suggested_title)
      setEditedPlot(enhancementResult.suggested_plot_outline)
      setEditedNumCuts(enhancementResult.suggested_num_cuts)
      setEditedNumCharacters(enhancementResult.suggested_num_characters)
      setEditedArtStyle(enhancementResult.suggested_art_style)
      setEditedMusicGenre(enhancementResult.suggested_music_genre)
      setEditedNarrativeTone(enhancementResult.suggested_narrative_tone)
      setEditedPlotStructure(enhancementResult.suggested_plot_structure)
    }
  }, [enhancementResult])

  const handleAutoGenerate = async () => {
    if (!enhancementResult) return

    try {
      // Create run spec from enhancement result
      const runSpec = {
        mode: selectedMode,
        prompt: editedPlot,
        num_characters: editedNumCharacters as 1 | 2 | 3,
        num_cuts: editedNumCuts,
        art_style: editedArtStyle,
        music_genre: editedMusicGenre,
        narrative_tone: editedNarrativeTone,
        plot_structure: editedPlotStructure,
        video_title: editedTitle,
        review_mode: false, // Auto-generate mode - no review
        // Test mode flags
        stub_image_mode: stubImageMode,
        stub_music_mode: stubMusicMode,
        stub_tts_mode: stubTTSMode,
      }

      // Create run directly
      const result = await createRun(runSpec)

      // Notify parent component
      if (onRunCreated) {
        onRunCreated(result.run_id, false)
      }

      setShowEnhancementModal(false)
      setEnhancementResult(null)
    } catch (error) {
      console.error('Failed to create run:', error)
      alert('영상 생성 시작 실패. 다시 시도해주세요.')
    }
  }

  const handleReviewMode = async () => {
    if (!enhancementResult) return

    try {
      // Create run spec from enhancement result with review mode enabled
      const runSpec = {
        mode: selectedMode,
        prompt: editedPlot,
        num_characters: editedNumCharacters as 1 | 2 | 3,
        num_cuts: editedNumCuts,
        art_style: editedArtStyle,
        music_genre: editedMusicGenre,
        narrative_tone: editedNarrativeTone,
        plot_structure: editedPlotStructure,
        video_title: editedTitle,
        review_mode: true, // Review mode - will show plot review modal
        // Test mode flags
        stub_image_mode: stubImageMode,
        stub_music_mode: stubMusicMode,
        stub_tts_mode: stubTTSMode,
      }

      // Create run directly
      const result = await createRun(runSpec)
      setCurrentRunId(result.run_id)

      // Switch modal to plot review mode (KEEP MODAL OPEN)
      setModalMode('plot-review')

      // Start loading plot.json
      await loadPlotJson(result.run_id)

    } catch (error) {
      console.error('Failed to create run:', error)
      alert('영상 생성 시작 실패. 다시 시도해주세요.')
    }
  }

  const loadPlotJson = async (runId: string) => {
    setIsLoadingPlot(true)
    let retries = 0
    const maxRetries = 30 // 최대 30초 대기 (1초 간격)

    while (retries < maxRetries) {
      try {
        const data = await getPlotJson(runId)
        setPlotData(data)
        setScenes(data.plot.scenes)
        setCharacters(data.plot.characters || [])
        setIsLoadingPlot(false)
        console.log(`[${runId}] Plot JSON loaded successfully after ${retries} retries`)
        console.log(`[${runId}] Loaded ${data.plot.characters?.length || 0} characters, ${data.plot.scenes.length} scenes`)
        return // 성공하면 종료
      } catch (error) {
        retries++
        if (retries >= maxRetries) {
          console.error(`[${runId}] Failed to load plot JSON after ${maxRetries} retries:`, error)
          const errorMessage = error instanceof Error ? error.message : String(error)
          alert(`플롯 JSON 로드 실패 (${maxRetries}초 대기 후): ${errorMessage}\n\n백엔드 로그를 확인해주세요.`)
          setIsLoadingPlot(false)
          return
        }
        // 1초 대기 후 재시도
        console.log(`[${runId}] Plot JSON not ready yet, retrying (${retries}/${maxRetries})...`)
        await new Promise(resolve => setTimeout(resolve, 1000))
      }
    }
  }

  const handleCharacterEdit = (charId: string, field: keyof Character, value: string) => {
    setCharacters(prevChars =>
      prevChars.map(char =>
        char.char_id === charId ? { ...char, [field]: value } : char
      )
    )
    setHasEditedPlot(true)
  }

  const handleSceneEdit = (sceneId: string, field: keyof Scene, value: string | number) => {
    setScenes(prevScenes =>
      prevScenes.map(scene =>
        scene.scene_id === sceneId ? { ...scene, [field]: value } : scene
      )
    )
    setHasEditedPlot(true)
  }

  const handleDeleteScene = (sceneId: string) => {
    if (!confirm('이 장면을 삭제하시겠습니까?')) return
    setScenes(prevScenes => prevScenes.filter(scene => scene.scene_id !== sceneId))
    setHasEditedPlot(true)
  }

  const handleConfirmPlot = async () => {
    if (!currentRunId) return
    setIsConfirmingPlot(true)
    try {
      const editedPlotData = hasEditedPlot ? {
        title: plotData?.plot.title,
        bgm_prompt: plotData?.plot.bgm_prompt,
        characters: characters,
        scenes: scenes
      } : undefined
      await confirmPlot(currentRunId, editedPlotData)

      // Notify parent and close modal
      if (onRunCreated) {
        onRunCreated(currentRunId, true)
      }
      handleCancelEnhancement()
    } catch (error) {
      console.error('Failed to confirm plot:', error)
      alert('플롯 확정 실패: ' + error)
    } finally {
      setIsConfirmingPlot(false)
    }
  }

  const handleRegeneratePlot = async () => {
    if (!currentRunId) return
    if (!confirm('플롯을 재생성하시겠습니까? 현재 플롯은 삭제됩니다.')) {
      return
    }

    setIsRegeneratingPlot(true)
    try {
      await regeneratePlot(currentRunId)
      alert('플롯 재생성이 시작되었습니다. 잠시 후 새로운 플롯이 표시됩니다.')
      // Reload plot after regeneration
      await new Promise(resolve => setTimeout(resolve, 2000))
      await loadPlotJson(currentRunId)
    } catch (error) {
      console.error('Failed to regenerate plot:', error)
      alert('플롯 재생성 실패: ' + error)
    } finally {
      setIsRegeneratingPlot(false)
    }
  }

  const handleCancelEnhancement = () => {
    setShowEnhancementModal(false)
    setEnhancementResult(null)
    setModalMode('enhancement')
    setCurrentRunId(null)
    setPlotData(null)
    setScenes([])
    setCharacters([])
    setPlotReviewTab('characters')
    setHasEditedPlot(false)
  }

  return (
    <section className="hero-chat-section">
      <div className="hero-chat-container">
        <div className="hero-chat-header">
          <h1 className="hero-chat-title">
            <span>Create something </span>
            <span
              className={`hero-chat-lovable ${isAnimating ? 'animating' : ''}`}
              style={{ color: COLORS[currentWordIndex % COLORS.length] }}
            >
              {ROTATING_WORDS[currentWordIndex]}
            </span>
          </h1>
          <p className="hero-chat-subtitle">
            텍스트 한 줄이면, AI가 알아서 숏폼 영상을 완성합니다
          </p>
        </div>

        <div className="hero-chat-form-wrapper">
          <form onSubmit={handleSubmit} className="hero-chat-form">
            <div className="hero-chat-input-container">
              <textarea
                className="hero-chat-textarea"
                placeholder={typedPlaceholder}
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                maxLength={5000}
                disabled={disabled}
                rows={1}
                onInput={(e) => {
                  const target = e.target as HTMLTextAreaElement
                  target.style.height = 'auto'
                  target.style.height = Math.min(target.scrollHeight, 200) + 'px'
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault()
                    // Don't call handleSubmit directly - let the form submit event handle it
                    // This prevents duplicate submissions
                    const form = e.currentTarget.form
                    if (form) {
                      form.requestSubmit()
                    }
                  }
                }}
              />
            </div>

            <div className="hero-chat-actions">
              <div className="hero-chat-mode-selector">
                <button
                  type="button"
                  className={`hero-mode-chip ${selectedMode === 'general' ? 'active' : ''}`}
                  onClick={() => handleModeChange('general')}
                  disabled={disabled}
                >
                  일반
                </button>
                <button
                  type="button"
                  className={`hero-mode-chip ${selectedMode === 'story' ? 'active' : ''}`}
                  onClick={() => handleModeChange('story')}
                  disabled={disabled}
                >
                  스토리
                </button>
                <button
                  type="button"
                  className={`hero-mode-chip ${selectedMode === 'ad' ? 'active' : ''}`}
                  onClick={() => handleModeChange('ad')}
                  disabled={disabled}
                >
                  광고
                </button>
              </div>

              <button
                type="submit"
                className="hero-chat-submit"
                disabled={!prompt.trim() || disabled}
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  fill="currentColor"
                  viewBox="0 0 24 24"
                  className="hero-submit-icon"
                >
                  <path d="M11 19V7.415l-3.293 3.293a1 1 0 1 1-1.414-1.414l5-5 .074-.067a1 1 0 0 1 1.34.067l5 5a1 1 0 1 1-1.414 1.414L13 7.415V19a1 1 0 1 1-2 0"></path>
                </svg>
              </button>
            </div>
          </form>
        </div>
      </div>

      {/* AI Enhancement Modal */}
      {showEnhancementModal && (
        <div className="enhancement-modal-overlay">
          <div className="enhancement-modal-container">
            <div className="enhancement-modal-layout">
              {/* Left: Stepper */}
              <div className="enhancement-stepper">
                {modalMode === 'enhancement' ? (
                  // Enhancement mode: Show all steps with first step active/completed
                  <>
                    <h3 style={{ fontSize: '18px', fontWeight: '700', marginBottom: '24px', color: '#111827' }}>
                      제작 단계
                    </h3>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      {/* Step 0: 프롬프트 분석 (Active or Completed) */}
                      <div style={{ position: 'relative', display: 'flex', alignItems: 'flex-start', gap: '12px', paddingBottom: '24px' }}>
                        <div className="enhancement-step-icon" style={enhancementResult ? {
                          backgroundColor: '#7189a0', border: '2px solid #7189a0'
                        } : {
                          backgroundColor: '#6f9fa0', border: '2px solid #6f9fa0', boxShadow: '0 0 0 4px rgba(111, 159, 160, 0.1)'
                        }}>
                          {enhancementResult ? (
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="#FFFFFF">
                              <path d="M19.7071 6.29289C20.0976 6.68342 20.0976 7.31658 19.7071 7.70711L9.70711 17.7071C9.31658 18.0976 8.68342 18.0976 8.29289 17.7071L4.29289 13.7071C3.90237 13.3166 3.90237 12.6834 4.29289 12.2929C4.68342 11.9024 5.31658 11.9024 5.70711 12.2929L9 15.5858L18.2929 6.29289C18.6834 5.90237 19.3166 5.90237 19.7071 6.29289Z"/>
                            </svg>
                          ) : (
                            <div className="enhancement-step-spinner"></div>
                          )}
                        </div>
                        <div style={{ flex: 1, paddingTop: '4px' }}>
                          <div style={{ fontSize: '15px', fontWeight: enhancementResult ? '600' : '700', color: enhancementResult ? '#6B7280' : '#111827', marginBottom: '4px' }}>
                            프롬프트 분석
                          </div>
                          <div style={{ fontSize: '13px', color: '#9CA3AF', lineHeight: '1.4' }}>
                            {enhancementResult ? '완료됨' : 'AI가 프롬프트를 분석 중입니다'}
                          </div>
                        </div>
                        <div style={{ position: 'absolute', left: '21px', top: '44px', bottom: '0', width: '2px', backgroundColor: enhancementResult ? '#7189a0' : '#E5E7EB' }} />
                      </div>

                      {/* Step 1: 시나리오 작성 (Pending) */}
                      <div style={{ position: 'relative', display: 'flex', alignItems: 'flex-start', gap: '12px', paddingBottom: '24px' }}>
                        <div className="enhancement-step-icon" style={{ backgroundColor: '#F3F4F6', border: '2px solid #E5E7EB' }}>
                        </div>
                        <div style={{ flex: 1, paddingTop: '4px' }}>
                          <div style={{ fontSize: '15px', fontWeight: '600', color: '#6B7280', marginBottom: '4px' }}>
                            시나리오 작성
                          </div>
                          <div style={{ fontSize: '13px', color: '#9CA3AF', lineHeight: '1.4' }}>
                            플롯을 검토하고 수정합니다
                          </div>
                        </div>
                        <div style={{ position: 'absolute', left: '21px', top: '44px', bottom: '0', width: '2px', backgroundColor: '#E5E7EB' }} />
                      </div>

                      {/* Step 2: 에셋 생성 (Pending) */}
                      <div style={{ position: 'relative', display: 'flex', alignItems: 'flex-start', gap: '12px', paddingBottom: '24px' }}>
                        <div className="enhancement-step-icon" style={{ backgroundColor: '#F3F4F6', border: '2px solid #E5E7EB' }}>
                        </div>
                        <div style={{ flex: 1, paddingTop: '4px' }}>
                          <div style={{ fontSize: '15px', fontWeight: '600', color: '#6B7280', marginBottom: '4px' }}>
                            에셋 생성
                          </div>
                          <div style={{ fontSize: '13px', color: '#9CA3AF', lineHeight: '1.4' }}>
                            이미지, 음악, 음성을 생성합니다
                          </div>
                        </div>
                        <div style={{ position: 'absolute', left: '21px', top: '44px', bottom: '0', width: '2px', backgroundColor: '#E5E7EB' }} />
                      </div>

                      {/* Step 3: 영상 합성 (Pending) */}
                      <div style={{ position: 'relative', display: 'flex', alignItems: 'flex-start', gap: '12px', paddingBottom: '24px' }}>
                        <div className="enhancement-step-icon" style={{ backgroundColor: '#F3F4F6', border: '2px solid #E5E7EB' }}>
                        </div>
                        <div style={{ flex: 1, paddingTop: '4px' }}>
                          <div style={{ fontSize: '15px', fontWeight: '600', color: '#6B7280', marginBottom: '4px' }}>
                            영상 합성
                          </div>
                          <div style={{ fontSize: '13px', color: '#9CA3AF', lineHeight: '1.4' }}>
                            최종 영상을 합성합니다
                          </div>
                        </div>
                        <div style={{ position: 'absolute', left: '21px', top: '44px', bottom: '0', width: '2px', backgroundColor: '#E5E7EB' }} />
                      </div>

                      {/* Step 4: 품질 검수 (Pending) */}
                      <div style={{ position: 'relative', display: 'flex', alignItems: 'flex-start', gap: '12px', paddingBottom: '0px' }}>
                        <div className="enhancement-step-icon" style={{ backgroundColor: '#F3F4F6', border: '2px solid #E5E7EB' }}>
                        </div>
                        <div style={{ flex: 1, paddingTop: '4px' }}>
                          <div style={{ fontSize: '15px', fontWeight: '600', color: '#6B7280', marginBottom: '4px' }}>
                            품질 검수
                          </div>
                          <div style={{ fontSize: '13px', color: '#9CA3AF', lineHeight: '1.4' }}>
                            최종 품질을 검수합니다
                          </div>
                        </div>
                      </div>
                    </div>
                  </>
                ) : (
                  // Plot review mode: 4 steps
                  <>
                    <h3 style={{ fontSize: '18px', fontWeight: '700', marginBottom: '24px', color: '#111827' }}>
                      검수 단계
                    </h3>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      {/* Step 0: 프롬프트 분석 (Completed) */}
                      <div style={{ position: 'relative', display: 'flex', alignItems: 'flex-start', gap: '12px', paddingBottom: '24px' }}>
                        <div className="enhancement-step-icon" style={{ backgroundColor: '#7189a0', border: '2px solid #7189a0' }}>
                          <svg width="16" height="16" viewBox="0 0 24 24" fill="#FFFFFF">
                            <path d="M19.7071 6.29289C20.0976 6.68342 20.0976 7.31658 19.7071 7.70711L9.70711 17.7071C9.31658 18.0976 8.68342 18.0976 8.29289 17.7071L4.29289 13.7071C3.90237 13.3166 3.90237 12.6834 4.29289 12.2929C4.68342 11.9024 5.31658 11.9024 5.70711 12.2929L9 15.5858L18.2929 6.29289C18.6834 5.90237 19.3166 5.90237 19.7071 6.29289Z"/>
                          </svg>
                        </div>
                        <div style={{ flex: 1, paddingTop: '4px' }}>
                          <div style={{ fontSize: '15px', fontWeight: '600', color: '#6B7280', marginBottom: '4px' }}>
                            프롬프트 분석
                          </div>
                          <div style={{ fontSize: '13px', color: '#9CA3AF', lineHeight: '1.4' }}>
                            완료됨
                          </div>
                        </div>
                        <div style={{ position: 'absolute', left: '21px', top: '44px', bottom: '0', width: '2px', backgroundColor: '#7189a0' }} />
                      </div>

                      {/* Step 1: 시나리오 작성 (Active) */}
                      <div style={{ position: 'relative', display: 'flex', alignItems: 'flex-start', gap: '12px', paddingBottom: '24px' }}>
                        <div className="enhancement-step-icon" style={{ backgroundColor: '#6f9fa0', border: '2px solid #6f9fa0', boxShadow: '0 0 0 4px rgba(111, 159, 160, 0.1)' }}>
                          <div className="enhancement-step-spinner"></div>
                        </div>
                        <div style={{ flex: 1, paddingTop: '4px' }}>
                          <div style={{ fontSize: '15px', fontWeight: '700', color: '#111827', marginBottom: '4px' }}>
                            시나리오 작성
                          </div>
                          <div style={{ fontSize: '13px', color: '#9CA3AF', lineHeight: '1.4' }}>
                            플롯을 검토하고 수정합니다
                          </div>
                        </div>
                        <div style={{ position: 'absolute', left: '21px', top: '44px', bottom: '0', width: '2px', backgroundColor: '#E5E7EB' }} />
                      </div>

                      {/* Step 2: 에셋 생성 (Pending) */}
                      <div style={{ position: 'relative', display: 'flex', alignItems: 'flex-start', gap: '12px', paddingBottom: '24px' }}>
                        <div className="enhancement-step-icon" style={{ backgroundColor: '#F3F4F6', border: '2px solid #E5E7EB' }}>
                        </div>
                        <div style={{ flex: 1, paddingTop: '4px' }}>
                          <div style={{ fontSize: '15px', fontWeight: '600', color: '#6B7280', marginBottom: '4px' }}>
                            에셋 생성
                          </div>
                          <div style={{ fontSize: '13px', color: '#9CA3AF', lineHeight: '1.4' }}>
                            이미지, 음악, 음성을 생성합니다
                          </div>
                        </div>
                        <div style={{ position: 'absolute', left: '21px', top: '44px', bottom: '0', width: '2px', backgroundColor: '#E5E7EB' }} />
                      </div>

                      {/* Step 3: 영상 합성 (Pending) */}
                      <div style={{ position: 'relative', display: 'flex', alignItems: 'flex-start', gap: '12px', paddingBottom: '24px' }}>
                        <div className="enhancement-step-icon" style={{ backgroundColor: '#F3F4F6', border: '2px solid #E5E7EB' }}>
                        </div>
                        <div style={{ flex: 1, paddingTop: '4px' }}>
                          <div style={{ fontSize: '15px', fontWeight: '600', color: '#6B7280', marginBottom: '4px' }}>
                            영상 합성
                          </div>
                          <div style={{ fontSize: '13px', color: '#9CA3AF', lineHeight: '1.4' }}>
                            최종 영상을 합성합니다
                          </div>
                        </div>
                        <div style={{ position: 'absolute', left: '21px', top: '44px', bottom: '0', width: '2px', backgroundColor: '#E5E7EB' }} />
                      </div>

                      {/* Step 4: 품질 검수 (Pending) */}
                      <div style={{ position: 'relative', display: 'flex', alignItems: 'flex-start', gap: '12px', paddingBottom: '0px' }}>
                        <div className="enhancement-step-icon" style={{ backgroundColor: '#F3F4F6', border: '2px solid #E5E7EB' }}>
                        </div>
                        <div style={{ flex: 1, paddingTop: '4px' }}>
                          <div style={{ fontSize: '15px', fontWeight: '600', color: '#6B7280', marginBottom: '4px' }}>
                            품질 검수
                          </div>
                          <div style={{ fontSize: '13px', color: '#9CA3AF', lineHeight: '1.4' }}>
                            최종 품질을 검수합니다
                          </div>
                        </div>
                      </div>
                    </div>
                  </>
                )}
              </div>

              {/* Right: Content */}
              <div className="enhancement-content">
                {modalMode === 'plot-review' ? (
                  // Plot Review Mode
                  <>
                    {isLoadingPlot ? (
                      <div className="enhancement-loading">
                        <img
                          src={`/animations/1_plot/plotanim_${String(currentAnimFrame).padStart(2, '0')}.png`}
                          alt="Loading animation"
                          style={{
                            width: '200px',
                            height: '200px',
                            objectFit: 'contain',
                            marginBottom: '24px'
                          }}
                        />
                        <h3 className="loading-title">시나리오 작성 중...</h3>
                        <p className="loading-subtitle">
                          기획자가 플롯을 짜고 있습니다
                        </p>
                      </div>
                    ) : (
                      <>
                        <div className="enhancement-content-header">
                          <h3 className="enhancement-modal-title">📋 시나리오 작성</h3>
                        </div>

                        {/* Tab Navigation */}
                        <div style={{ display: 'flex', gap: '8px', borderBottom: '2px solid #E5E7EB', marginBottom: '20px' }}>
                          <button
                            onClick={() => setPlotReviewTab('characters')}
                            style={{
                              padding: '10px 20px', fontSize: '15px', fontWeight: '600',
                              border: 'none', borderBottom: plotReviewTab === 'characters' ? '3px solid #6f9fa0' : '3px solid transparent',
                              background: plotReviewTab === 'characters' ? '#F9FAFB' : 'transparent',
                              color: plotReviewTab === 'characters' ? '#6f9fa0' : '#6B7280',
                              cursor: 'pointer', transition: 'all 0.2s'
                            }}
                          >
                            👥 인물 ({characters.length})
                          </button>
                          <button
                            onClick={() => setPlotReviewTab('scenes')}
                            style={{
                              padding: '10px 20px', fontSize: '15px', fontWeight: '600',
                              border: 'none', borderBottom: plotReviewTab === 'scenes' ? '3px solid #6f9fa0' : '3px solid transparent',
                              background: plotReviewTab === 'scenes' ? '#F9FAFB' : 'transparent',
                              color: plotReviewTab === 'scenes' ? '#6f9fa0' : '#6B7280',
                              cursor: 'pointer', transition: 'all 0.2s'
                            }}
                          >
                            🎬 장면 ({scenes.length})
                          </button>
                        </div>

                        <div style={{ flex: 1, overflowY: 'auto', padding: '0 0 20px 0' }}>
                          {plotReviewTab === 'characters' ? (
                            // Characters Tab
                            <>
                              <div style={{ backgroundColor: '#F3F4F6', padding: '15px', borderRadius: '8px', marginBottom: '20px' }}>
                                <p><strong>모드:</strong> {plotData?.mode || 'general'}</p>
                                <p><strong>총 인물 수:</strong> {characters.length}명</p>
                                <p style={{ marginTop: '10px', fontSize: '14px', color: '#6B7280' }}>
                                  인물의 외형 묘사를 수정하면 모든 장면의 이미지에 자동으로 반영됩니다.
                                </p>
                              </div>

                              {hasEditedPlot && (
                                <p style={{
                                  marginTop: '0', marginBottom: '16px', padding: '12px', fontSize: '13px',
                                  color: '#D97706', backgroundColor: '#FEF3C7', border: '1px solid #F59E0B',
                                  borderRadius: '6px', fontWeight: '500'
                                }}>
                                  ⚠️ 플롯이 수정되었습니다. 확정 시 수정된 내용이 반영됩니다.
                                </p>
                              )}

                              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                                {characters.map((char, index) => (
                                  <div key={char.char_id} style={{
                                    backgroundColor: '#FFFFFF', border: '2px solid #E5E7EB',
                                    borderRadius: '8px', padding: '16px'
                                  }}>
                                    <div style={{
                                      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                                      marginBottom: '12px', paddingBottom: '8px', borderBottom: '1px solid #E5E7EB'
                                    }}>
                                      <span style={{ fontSize: '16px', fontWeight: 'bold', color: '#1F2937' }}>
                                        인물 {index + 1}: {char.name}
                                      </span>
                                    </div>

                                    <div style={{ marginBottom: '12px' }}>
                                      <label style={{
                                        display: 'block', fontSize: '13px', fontWeight: '600',
                                        color: '#4B5563', marginBottom: '6px'
                                      }}>🆔 캐릭터 ID</label>
                                      <input
                                        type="text"
                                        value={char.char_id}
                                        disabled
                                        style={{
                                          width: '100%', padding: '8px 10px', fontSize: '14px',
                                          border: '1px solid #D1D5DB', borderRadius: '4px',
                                          backgroundColor: '#F9FAFB', color: '#6B7280'
                                        }}
                                      />
                                    </div>

                                    <div style={{ marginBottom: '12px' }}>
                                      <label style={{
                                        display: 'block', fontSize: '13px', fontWeight: '600',
                                        color: '#4B5563', marginBottom: '6px'
                                      }}>👤 이름</label>
                                      <input
                                        type="text"
                                        value={char.name}
                                        onChange={(e) => handleCharacterEdit(char.char_id, 'name', e.target.value)}
                                        style={{
                                          width: '100%', padding: '8px 10px', fontSize: '14px',
                                          border: '1px solid #D1D5DB', borderRadius: '4px'
                                        }}
                                      />
                                    </div>

                                    <div style={{ marginBottom: '0' }}>
                                      <label style={{
                                        display: 'block', fontSize: '13px', fontWeight: '600',
                                        color: '#4B5563', marginBottom: '6px'
                                      }}>✨ 외형 묘사</label>
                                      <textarea
                                        value={char.description}
                                        onChange={(e) => handleCharacterEdit(char.char_id, 'description', e.target.value)}
                                        placeholder="예: 25세 여성, 긴 검은 머리, 밝은 눈동자, 흰색 티셔츠와 청바지 착용"
                                        style={{
                                          width: '100%', padding: '8px 10px', fontSize: '14px',
                                          border: '1px solid #D1D5DB', borderRadius: '4px', resize: 'vertical'
                                        }}
                                        rows={4}
                                      />
                                      <p style={{ marginTop: '6px', fontSize: '12px', color: '#9CA3AF' }}>
                                        💡 이 묘사는 장면의 {'{'}{char.char_id}{'}'} 변수를 대체합니다
                                      </p>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </>
                          ) : (
                            // Scenes Tab
                            <>
                              <div style={{ backgroundColor: '#F3F4F6', padding: '15px', borderRadius: '8px', marginBottom: '20px' }}>
                                <p><strong>모드:</strong> {plotData?.mode || 'general'}</p>
                                <p><strong>총 장면 수:</strong> {scenes.length}개</p>
                                <p style={{ marginTop: '10px', fontSize: '14px', color: '#6B7280' }}>
                                  각 장면을 클릭하여 수정할 수 있습니다. 수정 후 "확정" 버튼을 누르면 수정된 내용으로 영상이 생성됩니다.
                                </p>
                              </div>

                              {hasEditedPlot && (
                                <p style={{
                                  marginTop: '0', marginBottom: '16px', padding: '12px', fontSize: '13px',
                                  color: '#D97706', backgroundColor: '#FEF3C7', border: '1px solid #F59E0B',
                                  borderRadius: '6px', fontWeight: '500'
                                }}>
                                  ⚠️ 플롯이 수정되었습니다. 확정 시 수정된 내용이 반영됩니다.
                                </p>
                              )}

                              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                                {scenes.map((scene, index) => (
                              <div key={scene.scene_id} style={{
                                backgroundColor: '#FFFFFF', border: '2px solid #E5E7EB',
                                borderRadius: '8px', padding: '16px'
                              }}>
                                <div style={{
                                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                                  marginBottom: '12px', paddingBottom: '8px', borderBottom: '1px solid #E5E7EB'
                                }}>
                                  <span style={{ fontSize: '16px', fontWeight: 'bold', color: '#1F2937' }}>
                                    장면 {index + 1}
                                  </span>
                                  <button
                                    onClick={() => handleDeleteScene(scene.scene_id)}
                                    style={{
                                      background: 'none', border: 'none', fontSize: '20px',
                                      cursor: 'pointer', padding: '4px', opacity: 0.6
                                    }}
                                    title="장면 삭제"
                                  >
                                    🗑️
                                  </button>
                                </div>

                                <div style={{ marginBottom: '12px' }}>
                                  <label style={{
                                    display: 'block', fontSize: '13px', fontWeight: '600',
                                    color: '#4B5563', marginBottom: '6px'
                                  }}>🖼️ 이미지 프롬프트</label>
                                  <textarea
                                    value={scene.image_prompt}
                                    onChange={(e) => handleSceneEdit(scene.scene_id, 'image_prompt', e.target.value)}
                                    placeholder="이미지 설명을 입력하세요. 비워두면 이전 장면의 이미지가 재사용됩니다."
                                    style={{
                                      width: '100%', padding: '8px 10px', fontSize: '14px',
                                      border: '1px solid #D1D5DB', borderRadius: '4px', resize: 'vertical'
                                    }}
                                    rows={3}
                                  />
                                </div>

                                <div style={{ marginBottom: '12px' }}>
                                  <label style={{
                                    display: 'block', fontSize: '13px', fontWeight: '600',
                                    color: '#4B5563', marginBottom: '6px'
                                  }}>💬 대사/자막</label>
                                  <textarea
                                    value={scene.text}
                                    onChange={(e) => handleSceneEdit(scene.scene_id, 'text', e.target.value)}
                                    style={{
                                      width: '100%', padding: '8px 10px', fontSize: '14px',
                                      border: '1px solid #D1D5DB', borderRadius: '4px', resize: 'vertical'
                                    }}
                                    rows={2}
                                  />
                                </div>

                                <div style={{ marginBottom: '0' }}>
                                  <label style={{
                                    display: 'block', fontSize: '13px', fontWeight: '600',
                                    color: '#4B5563', marginBottom: '6px'
                                  }}>🎤 화자</label>
                                  <input
                                    type="text"
                                    value={scene.speaker}
                                    onChange={(e) => handleSceneEdit(scene.scene_id, 'speaker', e.target.value)}
                                    style={{
                                      width: '100%', padding: '8px 10px', fontSize: '14px',
                                      border: '1px solid #D1D5DB', borderRadius: '4px'
                                    }}
                                  />
                                  </div>
                                </div>
                              ))}
                              </div>
                            </>
                          )}
                        </div>

                        <div className="enhancement-actions">
                          <button onClick={handleCancelEnhancement} className="enhancement-btn-cancel">
                            취소
                          </button>
                          <button
                            onClick={handleRegeneratePlot}
                            disabled={isRegeneratingPlot || isConfirmingPlot}
                            style={{
                              padding: '12px 24px', borderRadius: '8px', fontSize: '15px', fontWeight: '600',
                              cursor: isRegeneratingPlot || isConfirmingPlot ? 'not-allowed' : 'pointer',
                              backgroundColor: '#FFFFFF', color: '#DC2626', border: '2px solid #DC2626',
                              opacity: isRegeneratingPlot || isConfirmingPlot ? 0.5 : 1
                            }}
                          >
                            {isRegeneratingPlot ? '재생성 중...' : '거부 및 재생성'}
                          </button>
                          <button
                            onClick={handleConfirmPlot}
                            disabled={isConfirmingPlot || isRegeneratingPlot}
                            style={{
                              padding: '12px 24px', borderRadius: '8px', fontSize: '15px', fontWeight: '600',
                              cursor: isConfirmingPlot || isRegeneratingPlot ? 'not-allowed' : 'pointer',
                              backgroundColor: '#6f9fa0', color: '#FFFFFF', border: 'none',
                              opacity: isConfirmingPlot || isRegeneratingPlot ? 0.5 : 1
                            }}
                          >
                            {isConfirmingPlot ? '처리 중...' : '승인 및 다음 단계'}
                          </button>
                        </div>
                      </>
                    )}
                  </>
                ) : isEnhancing ? (
                  // Loading state
                  <div className="enhancement-loading">
                    <div className="loading-spinner">⚙️</div>
                    <h3 className="loading-title">AI 풍부화 진행 중...</h3>
                    <p className="loading-subtitle">
                      프롬프트를 분석하고 최적의 영상 설정을 추천하고 있습니다
                    </p>
                  </div>
                ) : enhancementResult ? (
                  // Content state
                  <>
                    <div className="enhancement-content-header">
                      <h3 className="enhancement-modal-title">✨ AI 풍부화 결과</h3>
                    </div>

                    <div className="enhancement-section">
                      <label className="enhancement-label">💬 입력한 내용</label>
                      <div style={{
                        padding: '12px 16px',
                        backgroundColor: '#F9FAFB',
                        border: '1px solid #E5E7EB',
                        borderRadius: '8px',
                        fontSize: '14px',
                        color: '#6B7280',
                        lineHeight: '1.6',
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word'
                      }}>
                        {prompt}
                      </div>
                    </div>

                    <div className="enhancement-section">
                      <label className="enhancement-label">제안된 영상 제목</label>
                      <input
                        type="text"
                        className="enhancement-input"
                        value={editedTitle}
                        onChange={(e) => setEditedTitle(e.target.value)}
                        placeholder="영상 제목 입력"
                      />
                    </div>

                    <div className="enhancement-section">
                      <label className="enhancement-label">📖 예상 플롯</label>
                      <textarea
                        className="enhancement-textarea"
                        value={editedPlot}
                        onChange={(e) => setEditedPlot(e.target.value)}
                        placeholder="플롯 내용 입력"
                        rows={4}
                      />
                    </div>

                    <div className="enhancement-grid">
                      <div className="enhancement-grid-item">
                        <label className="enhancement-grid-label">화풍</label>
                        <input
                          type="text"
                          className="enhancement-input-small"
                          value={editedArtStyle}
                          onChange={(e) => setEditedArtStyle(e.target.value)}
                          placeholder="화풍"
                        />
                      </div>

                      <div className="enhancement-grid-item">
                        <label className="enhancement-grid-label">음악 장르</label>
                        <input
                          type="text"
                          className="enhancement-input-small"
                          value={editedMusicGenre}
                          onChange={(e) => setEditedMusicGenre(e.target.value)}
                          placeholder="음악 장르"
                        />
                      </div>

                      <div className="enhancement-grid-item-full">
                        <label className="enhancement-grid-label">말투</label>
                        <select
                          className="enhancement-select"
                          value={editedNarrativeTone}
                          onChange={(e) => setEditedNarrativeTone(e.target.value)}
                        >
                          <option value="격식형">-입니다</option>
                          <option value="서술형">-함/-임</option>
                          <option value="친근한반말">-야/ -지?</option>
                          <option value="진지한나레이션">진지한 나레이션</option>
                          <option value="감정강조">감정 풍부</option>
                          <option value="코믹풍자">병맛/밈</option>
                        </select>
                      </div>

                      <div className="enhancement-grid-item-full">
                        <label className="enhancement-grid-label">전개 구조</label>
                        <select
                          className="enhancement-select"
                          value={editedPlotStructure}
                          onChange={(e) => setEditedPlotStructure(e.target.value)}
                        >
                          <option value="기승전결">고전적 기승전결</option>
                          <option value="고구마사이다">고구마-사이다형</option>
                          <option value="3막구조">3막 : 시작-위기-해결</option>
                          <option value="비교형">Before-After</option>
                          <option value="반전형">반전형</option>
                          <option value="정보나열">정보 나열형</option>
                          <option value="감정곡선">감정 곡선 : 공감→위로→희망</option>
                          <option value="질문형">질문형 오프닝</option>
                        </select>
                      </div>
                    </div>

                    {/* Test Mode Section */}
                    {showTestMode && (
                      <div style={{
                        padding: '16px 18px',
                        backgroundColor: '#FFF3CD',
                        border: '1px solid #FFC107',
                        borderRadius: '10px',
                        marginBottom: '24px'
                      }}>
                        <div style={{ fontSize: '13px', fontWeight: '600', color: '#856404', marginBottom: '12px' }}>
                          🧪 테스트 모드 (Option/Alt + Shift + T)
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                            <input
                              type="checkbox"
                              checked={stubImageMode}
                              onChange={(e) => setStubImageMode(e.target.checked)}
                              style={{ width: '16px', height: '16px', cursor: 'pointer' }}
                            />
                            <span style={{ fontSize: '13px', color: '#856404' }}>이미지 생성 스킵 (Stub Image Mode)</span>
                          </label>
                          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                            <input
                              type="checkbox"
                              checked={stubMusicMode}
                              onChange={(e) => setStubMusicMode(e.target.checked)}
                              style={{ width: '16px', height: '16px', cursor: 'pointer' }}
                            />
                            <span style={{ fontSize: '13px', color: '#856404' }}>음악 생성 스킵 (Stub Music Mode)</span>
                          </label>
                          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                            <input
                              type="checkbox"
                              checked={stubTTSMode}
                              onChange={(e) => setStubTTSMode(e.target.checked)}
                              style={{ width: '16px', height: '16px', cursor: 'pointer' }}
                            />
                            <span style={{ fontSize: '13px', color: '#856404' }}>음성 합성 스킵 (Stub TTS Mode)</span>
                          </label>
                        </div>
                      </div>
                    )}

                    <div className="enhancement-actions">
                      <button onClick={handleCancelEnhancement} className="enhancement-btn-cancel">
                        취소
                      </button>
                      <div className="enhancement-btn-wrapper">
                        <button
                          onClick={handleReviewMode}
                          className="enhancement-btn-review"
                        >
                          검수 모드
                        </button>
                        <span className="enhancement-tooltip">플롯을 검토하고 수정할 수 있습니다</span>
                      </div>
                      <div className="enhancement-btn-wrapper">
                        <button
                          onClick={handleAutoGenerate}
                          className="enhancement-btn-apply"
                        >
                          자동 생성
                        </button>
                        <span className="enhancement-tooltip">현재 설정으로 바로 영상 제작을 시작합니다</span>
                      </div>
                    </div>
                  </>
                ) : null}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Enhancement Error Modal */}
      {showEnhanceErrorModal && (
        <div className="enhancement-modal-overlay">
          <div className="enhancement-modal-container" style={{ maxWidth: '500px' }}>
            <div style={{ padding: '32px' }}>
              <div style={{ textAlign: 'center', marginBottom: '24px' }}>
                <div style={{
                  width: '64px',
                  height: '64px',
                  borderRadius: '50%',
                  backgroundColor: '#FEE2E2',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  margin: '0 auto 16px'
                }}>
                  <span style={{ fontSize: '32px' }}>⚠️</span>
                </div>
                <h3 style={{ fontSize: '20px', fontWeight: '700', color: '#111827', marginBottom: '8px' }}>
                  AI 풍부화 실패
                </h3>
                <p style={{ fontSize: '14px', color: '#6B7280', lineHeight: '1.5' }}>
                  프롬프트 분석 중 오류가 발생했습니다
                </p>
              </div>

              <div style={{
                backgroundColor: '#FEF2F2',
                border: '1px solid #FCA5A5',
                borderRadius: '8px',
                padding: '12px 16px',
                marginBottom: '24px'
              }}>
                <p style={{
                  fontSize: '13px',
                  color: '#991B1B',
                  fontFamily: 'monospace',
                  wordBreak: 'break-word'
                }}>
                  {enhanceError}
                </p>
              </div>

              <div style={{
                display: 'flex',
                flexDirection: 'column',
                gap: '12px'
              }}>
                <button
                  onClick={() => {
                    setShowEnhanceErrorModal(false)
                    handleSubmit({ preventDefault: () => {} } as React.FormEvent)
                  }}
                  style={{
                    width: '100%',
                    padding: '12px 24px',
                    backgroundColor: '#6f9fa0',
                    color: '#FFFFFF',
                    border: 'none',
                    borderRadius: '8px',
                    fontSize: '15px',
                    fontWeight: '600',
                    cursor: 'pointer',
                    transition: 'all 0.2s'
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#5a8385'}
                  onMouseLeave={(e) => e.currentTarget.style.backgroundColor = '#6f9fa0'}
                >
                  🔄 다시 시도
                </button>

                <button
                  onClick={() => {
                    setShowEnhanceErrorModal(false)
                    // Show enhancement modal with default values for manual input
                    setEnhancementResult({
                      enhanced_prompt: prompt,
                      suggested_title: prompt,
                      suggested_plot_outline: prompt,
                      suggested_num_cuts: 5,
                      suggested_num_characters: 1,
                      suggested_art_style: '일러스트',
                      suggested_music_genre: 'upbeat',
                      suggested_narrative_tone: '격식형',
                      suggested_plot_structure: '기승전결',
                      reasoning: '수동 입력 모드'
                    })
                    setShowEnhancementModal(true)
                  }}
                  style={{
                    width: '100%',
                    padding: '12px 24px',
                    backgroundColor: '#FFFFFF',
                    color: '#6f9fa0',
                    border: '2px solid #6f9fa0',
                    borderRadius: '8px',
                    fontSize: '15px',
                    fontWeight: '600',
                    cursor: 'pointer',
                    transition: 'all 0.2s'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.backgroundColor = '#F9FAFB'
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = '#FFFFFF'
                  }}
                >
                  ✏️ 직접 입력
                </button>

                <button
                  onClick={() => setShowEnhanceErrorModal(false)}
                  style={{
                    width: '100%',
                    padding: '12px 24px',
                    backgroundColor: 'transparent',
                    color: '#6B7280',
                    border: 'none',
                    borderRadius: '8px',
                    fontSize: '14px',
                    fontWeight: '500',
                    cursor: 'pointer',
                    transition: 'all 0.2s'
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#F3F4F6'}
                  onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                >
                  취소
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}

export default HeroChat
