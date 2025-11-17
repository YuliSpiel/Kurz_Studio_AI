import { useState, useEffect } from 'react'
import { enhancePrompt, PromptEnhancementResult } from '../api/client'

interface HeroChatProps {
  onSubmit: (prompt: string, mode: 'general' | 'story' | 'ad') => void
  onEnhancementReady?: (enhancement: PromptEnhancementResult, originalPrompt: string) => void
  disabled?: boolean
}

const ROTATING_WORDS = ['Epic', 'Cool', 'Fire', 'Viral', 'Neat', 'Bold']
const COLORS = ['#6f9fa0', '#7189a0', '#c9a989'] // 짙게 한 버전

const PLACEHOLDERS = {
  general: ['2030 직장인 공감 썰', '세계 5대 명소 추천'],
  story: ['소꿉친구랑 결혼 골인한 이야기', '아기 고양이의 우주 모험'],
  ad: ['제품 링크를 넣어주세요']
}

function HeroChat({ onSubmit, onEnhancementReady, disabled = false }: HeroChatProps) {
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
  }, [currentPlaceholderText])

  // Initialize with random placeholder on mount
  useEffect(() => {
    const placeholders = PLACEHOLDERS[selectedMode]
    const randomIndex = Math.floor(Math.random() * placeholders.length)
    setCurrentPlaceholderText(placeholders[randomIndex])
  }, [])

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
      setIsEnhancing(true)
      try {
        const result = await enhancePrompt(prompt, 'general')
        setEnhancementResult(result)
        setShowEnhancementModal(true)
      } catch (error: any) {
        console.error('Failed to enhance prompt:', error)
        alert(`프롬프트 풍부화 실패:\n${error?.message || String(error)}\n\n백엔드 서버가 실행 중인지 확인해주세요.`)
      } finally {
        setIsEnhancing(false)
      }
    } else {
      // For story/ad modes, proceed directly
      onSubmit(prompt, selectedMode)
    }
  }

  const handleApplyEnhancement = () => {
    if (!enhancementResult) return

    // Pass enhancement result to parent
    if (onEnhancementReady) {
      onEnhancementReady(enhancementResult, prompt)
    }

    setShowEnhancementModal(false)
    setEnhancementResult(null)
  }

  const handleCancelEnhancement = () => {
    setShowEnhancementModal(false)
    setEnhancementResult(null)
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
            텍스트 한 줄이면, 플롯·이미지·음악·보이스부터 숏폼영상까지 AI가 완성합니다
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
      {showEnhancementModal && enhancementResult && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.7)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
        }}>
          <div style={{
            backgroundColor: 'white',
            padding: '30px',
            borderRadius: '12px',
            maxWidth: '600px',
            width: '90%',
            maxHeight: '80vh',
            overflow: 'auto',
            boxShadow: '0 20px 60px rgba(0, 0, 0, 0.3)',
          }}>
            <h3 style={{ marginTop: 0, marginBottom: '20px', fontSize: '24px', color: '#1F2937' }}>
              ✨ AI 풍부화 결과
            </h3>

            <div style={{ marginBottom: '20px' }}>
              <label style={{ display: 'block', fontWeight: 'bold', marginBottom: '8px', color: '#374151' }}>
                제안된 영상 제목
              </label>
              <div style={{
                padding: '12px',
                backgroundColor: '#EEF2FF',
                borderRadius: '8px',
                fontSize: '16px',
                fontWeight: '600',
                lineHeight: '1.4',
                color: '#4338CA',
              }}>
                {enhancementResult.suggested_title}
              </div>
            </div>

            <div style={{ marginBottom: '20px' }}>
              <label style={{ display: 'block', fontWeight: 'bold', marginBottom: '8px', color: '#374151' }}>
                📖 예상 플롯
              </label>
              <div style={{
                padding: '14px',
                backgroundColor: '#F0FDF4',
                borderLeft: '4px solid #10B981',
                borderRadius: '8px',
                fontSize: '14px',
                lineHeight: '1.8',
                color: '#065F46',
                whiteSpace: 'pre-wrap',
              }}>
                {enhancementResult.suggested_plot_outline}
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '20px' }}>
              <div>
                <label style={{ display: 'block', fontWeight: 'bold', marginBottom: '4px', fontSize: '13px', color: '#6B7280' }}>
                  컷 수
                </label>
                <div style={{ fontSize: '18px', fontWeight: '600', color: '#7C3AED' }}>
                  {enhancementResult.suggested_num_cuts}개
                </div>
              </div>

              <div>
                <label style={{ display: 'block', fontWeight: 'bold', marginBottom: '4px', fontSize: '13px', color: '#6B7280' }}>
                  캐릭터 수
                </label>
                <div style={{ fontSize: '18px', fontWeight: '600', color: '#10B981' }}>
                  {enhancementResult.suggested_num_characters}명
                </div>
              </div>

              <div>
                <label style={{ display: 'block', fontWeight: 'bold', marginBottom: '4px', fontSize: '13px', color: '#6B7280' }}>
                  화풍
                </label>
                <div style={{ fontSize: '16px', fontWeight: '500', color: '#1F2937' }}>
                  {enhancementResult.suggested_art_style}
                </div>
              </div>

              <div>
                <label style={{ display: 'block', fontWeight: 'bold', marginBottom: '4px', fontSize: '13px', color: '#6B7280' }}>
                  음악 장르
                </label>
                <div style={{ fontSize: '16px', fontWeight: '500', color: '#1F2937' }}>
                  {enhancementResult.suggested_music_genre}
                </div>
              </div>

              <div style={{ gridColumn: '1 / -1' }}>
                <label style={{ display: 'block', fontWeight: 'bold', marginBottom: '4px', fontSize: '13px', color: '#6B7280' }}>
                  말투
                </label>
                <div style={{ fontSize: '16px', fontWeight: '500', color: '#1F2937' }}>
                  {enhancementResult.suggested_narrative_tone}
                </div>
              </div>

              <div style={{ gridColumn: '1 / -1' }}>
                <label style={{ display: 'block', fontWeight: 'bold', marginBottom: '4px', fontSize: '13px', color: '#6B7280' }}>
                  전개 구조
                </label>
                <div style={{ fontSize: '16px', fontWeight: '500', color: '#1F2937' }}>
                  {enhancementResult.suggested_plot_structure}
                </div>
              </div>
            </div>

            <div style={{
              padding: '12px',
              backgroundColor: '#FEF3C7',
              borderLeft: '4px solid #F59E0B',
              borderRadius: '6px',
              marginBottom: '24px',
            }}>
              <div style={{ fontSize: '12px', fontWeight: 'bold', color: '#92400E', marginBottom: '4px' }}>
                💡 제안 이유
              </div>
              <div style={{ fontSize: '13px', color: '#78350F', lineHeight: '1.5' }}>
                {enhancementResult.reasoning}
              </div>
            </div>

            <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
              <button
                onClick={handleCancelEnhancement}
                style={{
                  padding: '10px 20px',
                  backgroundColor: '#E5E7EB',
                  color: '#374151',
                  border: 'none',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  fontSize: '14px',
                  fontWeight: '600',
                }}
              >
                취소
              </button>
              <button
                onClick={handleApplyEnhancement}
                style={{
                  padding: '10px 20px',
                  backgroundColor: '#7C3AED',
                  color: 'white',
                  border: 'none',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  fontSize: '14px',
                  fontWeight: '600',
                }}
              >
                적용하기
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}

export default HeroChat
