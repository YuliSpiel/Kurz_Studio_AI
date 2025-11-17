import { useState, useEffect } from 'react'

interface HeroChatProps {
  onSubmit: (prompt: string, mode: 'general' | 'story' | 'ad') => void
  disabled?: boolean
}

const ROTATING_WORDS = ['Epic', 'Cool', 'Fire', 'Viral', 'Neat', 'Bold']
const COLORS = ['#6f9fa0', '#7189a0', '#c9a989'] // 짙게 한 버전

const PLACEHOLDERS = {
  general: ['2030 직장인 공감 썰', '세계 5대 명소 추천'],
  story: ['소꿉친구랑 결혼 골인한 이야기', '아기 고양이의 우주 모험'],
  ad: ['제품 링크를 넣어주세요']
}

function HeroChat({ onSubmit, disabled = false }: HeroChatProps) {
  const [prompt, setPrompt] = useState('')
  const [selectedMode, setSelectedMode] = useState<'general' | 'story' | 'ad'>('general')
  const [currentWordIndex, setCurrentWordIndex] = useState(0)
  const [isAnimating, setIsAnimating] = useState(false)
  const [typedPlaceholder, setTypedPlaceholder] = useState('')
  const [currentPlaceholderText, setCurrentPlaceholderText] = useState('')

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

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (prompt.trim() && !disabled) {
      onSubmit(prompt, selectedMode)
    }
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
    </section>
  )
}

export default HeroChat
