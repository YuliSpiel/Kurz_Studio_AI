import { useState, useEffect, FormEvent } from 'react'
import { createRun, uploadReferenceImage, getAvailableFonts, Font, enhancePrompt, PromptEnhancementResult } from '../api/client'

interface RunFormProps {
  onRunCreated: (runId: string) => void
  enhancementData?: {
    enhancement: PromptEnhancementResult
    originalPrompt: string
  } | null
}

export default function RunForm({ onRunCreated, enhancementData }: RunFormProps) {
  const mode = 'general' // Fixed to general mode
  const [prompt, setPrompt] = useState('')
  const [numCuts, setNumCuts] = useState(3)
  const [numCharacters, setNumCharacters] = useState<1 | 2 | 3>(1)
  const [artStyle, setArtStyle] = useState('파스텔 수채화')
  const [musicGenre, setMusicGenre] = useState('ambient')
  const [narrativeTone, setNarrativeTone] = useState('격식형')
  const [plotStructure, setPlotStructure] = useState('기승전결')
  const [referenceFiles, setReferenceFiles] = useState<File[]>([])
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isEnhancing, setIsEnhancing] = useState(false)
  const [enhancementResult, setEnhancementResult] = useState<PromptEnhancementResult | null>(null)
  const [showEnhancementPreview, setShowEnhancementPreview] = useState(false)

  // Layout customization states
  const [videoTitle, setVideoTitle] = useState('')
  const [titleBgColor, setTitleBgColor] = useState('#323296') // Dark blue
  const [titleFont, setTitleFont] = useState('AppleGothic')
  const [titleFontSize, setTitleFontSize] = useState(100)
  const [subtitleFont, setSubtitleFont] = useState('AppleGothic')
  const [subtitleFontSize, setSubtitleFontSize] = useState(80)

  // Test mode states (Option+Shift+T)
  const [showTestMode, setShowTestMode] = useState(false)
  const [stubImageMode, setStubImageMode] = useState(false)
  const [stubMusicMode, setStubMusicMode] = useState(false)
  const [stubTTSMode, setStubTTSMode] = useState(false)

  // Review mode state
  const [isSubmittingReview, setIsSubmittingReview] = useState(false)

  // Font list with fallback defaults
  const [availableFonts, setAvailableFonts] = useState<Font[]>([
    { id: 'AppleGothic', name: 'Apple Gothic (시스템)', path: 'AppleGothic' },
    { id: 'AppleMyungjo', name: 'Apple Myungjo (시스템)', path: 'AppleMyungjo' }
  ])

  // Keyboard shortcut for test mode (Option+Shift+T)
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

  // Apply enhancement data when it changes
  useEffect(() => {
    if (enhancementData) {
      const { enhancement } = enhancementData
      setPrompt(enhancement.suggested_plot_outline)
      setVideoTitle(enhancement.suggested_title)
      setNumCuts(enhancement.suggested_num_cuts)
      setNumCharacters(enhancement.suggested_num_characters as 1 | 2 | 3)
      setArtStyle(enhancement.suggested_art_style)
      setMusicGenre(enhancement.suggested_music_genre)
      setNarrativeTone(enhancement.suggested_narrative_tone)
      setPlotStructure(enhancement.suggested_plot_structure)
    }
  }, [enhancementData])

  // Load available fonts on component mount
  useEffect(() => {
    const loadFonts = async () => {
      try {
        console.log('Loading fonts from API...')
        const fonts = await getAvailableFonts()
        console.log('Loaded fonts:', fonts)

        if (fonts && fonts.length > 0) {
          setAvailableFonts(fonts)

          // Dynamically load custom fonts for preview
          fonts.forEach(font => {
            // Skip system fonts (they don't have file paths in /api/fonts/)
            if (font.id.startsWith('Apple')) return

            const fontFace = new FontFace(font.id, `url(/api/fonts/${font.id})`)
            fontFace.load().then(loadedFont => {
              document.fonts.add(loadedFont)
              console.log(`Loaded font: ${font.id}`)
            }).catch(err => {
              console.warn(`Failed to load font ${font.id}:`, err)
            })
          })
        } else {
          console.warn('No fonts returned from API, using fallback fonts')
        }
      } catch (error) {
        console.error('Failed to load fonts:', error)
        console.log('Using fallback fonts')
      }
    }
    loadFonts()
  }, [])

  const handleSubmit = async (reviewMode: boolean) => {
    if (reviewMode) {
      setIsSubmittingReview(true)
    } else {
      setIsSubmitting(true)
    }

    try {
      // Upload reference images
      const referenceImages: string[] = []
      for (const file of referenceFiles) {
        const filename = await uploadReferenceImage(file)
        referenceImages.push(filename)
      }

      // Create run with layout customization and test mode flags
      const result = await createRun({
        mode,
        prompt: `${prompt}\n\n[스타일 지시: 말투="${narrativeTone}", 전개구조="${plotStructure}"]`,
        num_characters: numCharacters,
        num_cuts: numCuts,
        art_style: artStyle,
        music_genre: musicGenre,
        reference_images: referenceImages.length > 0 ? referenceImages : undefined,
        video_title: videoTitle,
        layout_config: {
          title_bg_color: titleBgColor,
          title_font: titleFont,
          title_font_size: titleFontSize,
          subtitle_font: subtitleFont,
          subtitle_font_size: subtitleFontSize,
        },
        // Test mode flags
        stub_image_mode: stubImageMode,
        stub_music_mode: stubMusicMode,
        stub_tts_mode: stubTTSMode,
        // Review mode flag
        review_mode: reviewMode,
      })

      onRunCreated(result.run_id)
    } catch (error) {
      console.error('Failed to create run:', error)
      alert('Run 생성 실패: ' + error)
    } finally {
      setIsSubmitting(false)
      setIsSubmittingReview(false)
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setReferenceFiles(Array.from(e.target.files))
    }
  }

  const handleEnhancePrompt = async () => {
    if (!prompt || prompt.trim().length === 0) {
      alert('프롬프트를 먼저 입력해주세요')
      return
    }

    setIsEnhancing(true)
    try {
      const result = await enhancePrompt(prompt, mode)
      setEnhancementResult(result)
      setShowEnhancementPreview(true)
    } catch (error: any) {
      console.error('Failed to enhance prompt:', error)
      const errorMessage = error?.message || String(error)
      alert(`프롬프트 풍부화 실패:\n${errorMessage}\n\n백엔드 서버가 실행 중인지 확인해주세요.`)
    } finally {
      setIsEnhancing(false)
    }
  }

  const handleApplyEnhancement = () => {
    if (!enhancementResult) return

    // Use suggested_plot_outline instead of enhanced_prompt
    setPrompt(enhancementResult.suggested_plot_outline)
    setVideoTitle(enhancementResult.suggested_title)
    setNumCuts(enhancementResult.suggested_num_cuts)
    setNumCharacters(enhancementResult.suggested_num_characters as 1 | 2 | 3)
    setArtStyle(enhancementResult.suggested_art_style)
    setMusicGenre(enhancementResult.suggested_music_genre)
    setNarrativeTone(enhancementResult.suggested_narrative_tone)
    setPlotStructure(enhancementResult.suggested_plot_structure)
    setShowEnhancementPreview(false)
    setEnhancementResult(null)
  }

  const handleCancelEnhancement = () => {
    setShowEnhancementPreview(false)
    setEnhancementResult(null)
  }

  return (
    <div className="run-form-wrapper">
      <form onSubmit={handleSubmit} className="run-form">
        <h2>새 숏츠 생성</h2>

      <div className="form-group">
        <label>프롬프트</label>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="예: 우주를 여행하는 고양이 이야기"
          rows={4}
          required
        />
        <button
          type="button"
          onClick={handleEnhancePrompt}
          disabled={isEnhancing || !prompt}
          className="btn-enhance"
          style={{
            marginTop: '10px',
            padding: '8px 16px',
            backgroundColor: '#7C3AED',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            cursor: prompt ? 'pointer' : 'not-allowed',
            fontSize: '14px',
            fontWeight: '600',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            opacity: (isEnhancing || !prompt) ? 0.6 : 1,
          }}
        >
          <span style={{ fontSize: '16px' }}>✨</span>
          {isEnhancing ? 'AI 분석 중...' : 'AI 풍부화'}
        </button>
      </div>

      <div className="form-group">
        <label>컷 수 (1-10)</label>
        <input
          type="number"
          value={numCuts}
          onChange={(e) => setNumCuts(Number(e.target.value))}
          min={1}
          max={10}
          required
        />
      </div>

      <div className="form-group">
        <label>화풍</label>
        <input
          type="text"
          value={artStyle}
          onChange={(e) => setArtStyle(e.target.value)}
          placeholder="예: 파스텔 수채화, 애니메이션, 사실적"
        />
      </div>

      <div className="form-group">
        <label>음악 장르</label>
        <input
          type="text"
          value={musicGenre}
          onChange={(e) => setMusicGenre(e.target.value)}
          placeholder="예: ambient, cinematic, upbeat"
        />
      </div>

      <div className="form-group">
        <label>내레이션 말투</label>
        <select
          value={narrativeTone}
          onChange={(e) => setNarrativeTone(e.target.value)}
        >
          <option value="격식형">격식형 (-입니다체) - 뉴스, 해설, 교육</option>
          <option value="서술형">서술형 (-함.체) - 요약, 정보전달</option>
          <option value="친근한반말">친근한 반말 (-거야, -지?) - 광고, 추천</option>
          <option value="진지한나레이션">진지한 나레이션체 - 스토리, 다큐</option>
          <option value="감정강조">감정 강조형 - 리액션, 감정 몰입</option>
          <option value="코믹풍자">코믹/풍자형 - 병맛, 밈 기반</option>
        </select>
      </div>

      <div className="form-group">
        <label>전개 구조</label>
        <select
          value={plotStructure}
          onChange={(e) => setPlotStructure(e.target.value)}
        >
          <option value="기승전결">고전적 기승전결 - 스토리텔링, 교육</option>
          <option value="고구마사이다">고구마-사이다형 - 답답함→반전 해결</option>
          <option value="3막구조">3막 구조 (시작-위기-해결) - 간결한 내러티브</option>
          <option value="비교형">비교형 (Before-After) - 변화 강조</option>
          <option value="반전형">반전형 (Twist Ending) - 밈, 코믹, 리액션</option>
          <option value="정보나열">정보 나열형 (Listicle) - 트렌드 요약</option>
          <option value="감정곡선">감정 곡선형 - 공감→위로→희망</option>
          <option value="질문형">질문형 오프닝 - 호기심 유발</option>
          <option value="루프형">루프형 (Looped Ending) - 반복 시청 유도</option>
        </select>
      </div>

      <div className="form-group">
        <label>참조 이미지 (선택)</label>
        <input
          type="file"
          accept="image/*"
          multiple
          onChange={handleFileChange}
        />
        {referenceFiles.length > 0 && (
          <p className="file-count">{referenceFiles.length}개 파일 선택됨</p>
        )}
      </div>

      {/* Test Mode Panel (Option+Shift+T) */}
      {showTestMode && (
        <div style={{
          marginTop: '20px',
          padding: '15px',
          backgroundColor: '#FFF3CD',
          border: '2px solid #FFC107',
          borderRadius: '8px',
        }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            marginBottom: '10px',
            fontWeight: 'bold',
            color: '#856404'
          }}>
            <span style={{ fontSize: '18px', marginRight: '8px' }}>🧪</span>
            테스트 모드 (API 호출 생략)
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={stubImageMode}
                onChange={(e) => setStubImageMode(e.target.checked)}
                style={{ marginRight: '8px', cursor: 'pointer' }}
              />
              <span>Stub 이미지 모드 (Gemini 이미지 생성 생략)</span>
            </label>
            <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={stubMusicMode}
                onChange={(e) => setStubMusicMode(e.target.checked)}
                style={{ marginRight: '8px', cursor: 'pointer' }}
              />
              <span>Stub 음원 모드 (ElevenLabs 음악 생성 생략)</span>
            </label>
            <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={stubTTSMode}
                onChange={(e) => setStubTTSMode(e.target.checked)}
                style={{ marginRight: '8px', cursor: 'pointer' }}
              />
              <span>Stub TTS 모드 (ElevenLabs 음성 합성 생략)</span>
            </label>
          </div>
          <p style={{
            marginTop: '10px',
            fontSize: '12px',
            color: '#856404',
            fontStyle: 'italic'
          }}>
            💡 Option+Shift+T를 다시 누르면 테스트 모드가 숨겨집니다
          </p>
        </div>
      )}
      </form>

      {/* Layout Customization Section */}
      <div className="layout-customization-section">
        <h3>레이아웃 커스터마이징</h3>

        <div className="layout-customization-grid">
          {/* Left: Preview */}
          <div className="preview-container">
            <div className="layout-preview">
              <div
                className="preview-title-block"
                style={{
                  backgroundColor: titleBgColor,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  padding: '10px 10px',
                  boxSizing: 'border-box',
                  minHeight: '40px'
                }}
              >
                <span style={{
                  color: 'white',
                  fontSize: `${titleFontSize / 3.86}px`,
                  fontFamily: titleFont,
                  fontWeight: 'bold',
                  whiteSpace: 'pre-wrap',
                  textAlign: 'center',
                  lineHeight: '1.2'
                }}>
                  {videoTitle || '샘플 타이틀'}
                </span>
              </div>
              <div className="preview-content" style={{
                flex: 1,
                position: 'relative',
                overflow: 'hidden',
                backgroundColor: '#ffffff',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'flex-start'
              }}>
                {/* Subtitle area - between title and image */}
                <div style={{
                  width: '100%',
                  padding: '10px 0',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  backgroundColor: '#ffffff'
                }}>
                  <span style={{
                    fontSize: `${subtitleFontSize / 3.86}px`,
                    fontFamily: subtitleFont,
                    color: 'black',
                    fontWeight: 'bold',
                    textAlign: 'center',
                    width: '90%'
                  }}>
                    카피바라와 친구들이 온천에서 힐링하고있어요!
                  </span>
                </div>
                {/* Background Image - 1:1, positioned at 60% from top (matching render) */}
                <div style={{
                  flex: 1,
                  width: '100%',
                  position: 'relative',
                  display: 'flex'
                }}>
                  <img
                    src="/outputs/20251111_1441_카피바라가온천을/scene_4_scene.png"
                    alt="Preview"
                    style={{
                      position: 'absolute',
                      top: '60%',
                      left: '50%',
                      transform: 'translate(-50%, -60%)',
                      maxWidth: '100%',
                      maxHeight: '100%',
                      objectFit: 'contain'
                    }}
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Right: Settings */}
          <div className="settings-container">
            <div className="form-group">
              <label>영상 제목</label>
              <textarea
                value={videoTitle}
                onChange={(e) => setVideoTitle(e.target.value)}
                placeholder="영상 제목을 입력하세요 (엔터로 줄바꿈 가능)"
                rows={2}
                style={{ resize: 'vertical' }}
              />
            </div>

            <div className="form-group">
              <label>타이틀 블록 색상</label>
              <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                <input
                  type="color"
                  value={titleBgColor}
                  onChange={(e) => setTitleBgColor(e.target.value)}
                  style={{ width: '60px', height: '40px' }}
                />
                <input
                  type="text"
                  value={titleBgColor}
                  onChange={(e) => setTitleBgColor(e.target.value)}
                  placeholder="#323296"
                  style={{ flex: 1 }}
                />
              </div>
            </div>

            <div className="form-group">
              <label>타이틀 폰트</label>
              <select value={titleFont} onChange={(e) => setTitleFont(e.target.value)}>
                {availableFonts.map(font => (
                  <option key={font.id} value={font.id}>{font.name}</option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label>타이틀 폰트 크기: {titleFontSize}px</label>
              <input
                type="range"
                min="80"
                max="130"
                value={titleFontSize}
                onChange={(e) => setTitleFontSize(Number(e.target.value))}
              />
            </div>

            <div className="form-group">
              <label>자막 폰트</label>
              <select value={subtitleFont} onChange={(e) => setSubtitleFont(e.target.value)}>
                {availableFonts.map(font => (
                  <option key={font.id} value={font.id}>{font.name}</option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label>자막 폰트 크기: {subtitleFontSize}px</label>
              <input
                type="range"
                min="60"
                max="110"
                value={subtitleFontSize}
                onChange={(e) => setSubtitleFontSize(Number(e.target.value))}
              />
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '12px', marginTop: '20px' }}>
          <button
            type="button"
            disabled={isSubmitting || isSubmittingReview || !prompt}
            className="btn-submit"
            onClick={() => handleSubmit(false)}
            style={{
              flex: 1,
              backgroundColor: isSubmitting ? '#9CA3AF' : '#10B981',
              cursor: (isSubmitting || isSubmittingReview || !prompt) ? 'not-allowed' : 'pointer',
            }}
          >
            {isSubmitting ? '생성 중...' : '🚀 자동 모드 (즉시 생성)'}
          </button>
          <button
            type="button"
            disabled={isSubmitting || isSubmittingReview || !prompt}
            className="btn-submit"
            onClick={() => handleSubmit(true)}
            style={{
              flex: 1,
              backgroundColor: isSubmittingReview ? '#9CA3AF' : '#7C3AED',
              cursor: (isSubmitting || isSubmittingReview || !prompt) ? 'not-allowed' : 'pointer',
            }}
          >
            {isSubmittingReview ? '생성 중...' : '✏️ 검수 모드 (플롯 확인 후 생성)'}
          </button>
        </div>
      </div>

      {/* Enhancement Preview Modal */}
      {showEnhancementPreview && enhancementResult && (
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

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: '16px', marginBottom: '20px' }}>
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
    </div>
  )
}
