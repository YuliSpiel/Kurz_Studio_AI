import { useState, useEffect, FormEvent } from 'react'
import { createRun, uploadReferenceImage, getAvailableFonts, Font, enhancePrompt, PromptEnhancementResult } from '../api/client'

interface RunFormProps {
  onRunCreated: (runId: string) => void
}

export default function RunForm({ onRunCreated }: RunFormProps) {
  const mode = 'general' // Fixed to general mode
  const [prompt, setPrompt] = useState('')
  const [numCuts, setNumCuts] = useState(3)
  const [artStyle, setArtStyle] = useState('파스텔 수채화')
  const [musicGenre, setMusicGenre] = useState('ambient')
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

  // Font list with fallback defaults
  const [availableFonts, setAvailableFonts] = useState<Font[]>([
    { id: 'AppleGothic', name: 'Apple Gothic (시스템)', path: 'AppleGothic' },
    { id: 'AppleMyungjo', name: 'Apple Myungjo (시스템)', path: 'AppleMyungjo' }
  ])

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

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setIsSubmitting(true)

    try {
      // Upload reference images
      const referenceImages: string[] = []
      for (const file of referenceFiles) {
        const filename = await uploadReferenceImage(file)
        referenceImages.push(filename)
      }

      // Create run with layout customization
      const result = await createRun({
        mode,
        prompt,
        num_characters: 1, // Fixed to 1 character for general mode
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
      })

      onRunCreated(result.run_id)
    } catch (error) {
      console.error('Failed to create run:', error)
      alert('Run 생성 실패: ' + error)
    } finally {
      setIsSubmitting(false)
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

    setPrompt(enhancementResult.enhanced_prompt)
    setVideoTitle(enhancementResult.suggested_title)
    setNumCuts(enhancementResult.suggested_num_cuts)
    setArtStyle(enhancementResult.suggested_art_style)
    setMusicGenre(enhancementResult.suggested_music_genre)
    // Note: num_characters is ignored, always fixed to 1 for general mode
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
                    "고구마가 세상에서 제일 맛있어!"
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
                    src="/outputs/20251107_1617_고구마를좋아하는/scene_1_scene.png"
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

        <button type="submit" disabled={isSubmitting || !prompt} className="btn-submit" onClick={handleSubmit}>
          {isSubmitting ? '생성 중...' : '숏츠 생성 시작'}
        </button>
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
                풍부화된 프롬프트
              </label>
              <div style={{
                padding: '12px',
                backgroundColor: '#F3F4F6',
                borderRadius: '8px',
                fontSize: '14px',
                lineHeight: '1.6',
                color: '#1F2937',
              }}>
                {enhancementResult.enhanced_prompt}
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '16px', marginBottom: '20px' }}>
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
