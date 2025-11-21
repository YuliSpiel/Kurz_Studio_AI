import { useState, useEffect } from 'react'
import {
  getLayoutConfig,
  getAvailableFonts,
  confirmLayoutWithConfig,
  regenerateLayout,
  type LayoutConfig,
  type Font,
} from '../api/client'

interface LayoutReviewModalProps {
  runId: string
  onClose: () => void
}

export default function LayoutReviewModal({ runId, onClose }: LayoutReviewModalProps) {
  const [isLoading, setIsLoading] = useState(true)
  const [isConfirming, setIsConfirming] = useState(false)
  const [isRegenerating, setIsRegenerating] = useState(false)
  const [config, setConfig] = useState<LayoutConfig | null>(null)
  const [fonts, setFonts] = useState<Font[]>([])
  const [title, setTitle] = useState('')

  // Load initial config and fonts
  useEffect(() => {
    loadLayoutConfig()
  }, [runId])

  // Load fonts dynamically when fonts list changes
  useEffect(() => {
    if (fonts.length === 0) return

    // Create @font-face rules for all custom fonts
    const fontFaceRules = fonts
      .filter(font => !font.id.startsWith('Apple')) // Skip system fonts
      .map(font => `
        @font-face {
          font-family: '${font.id}';
          src: url('/api/fonts/${font.id}') format('truetype');
          font-weight: normal;
          font-style: normal;
        }
      `)
      .join('\n')

    // Inject font-face rules into a style tag
    const styleId = 'dynamic-fonts'
    let styleElement = document.getElementById(styleId) as HTMLStyleElement

    if (!styleElement) {
      styleElement = document.createElement('style')
      styleElement.id = styleId
      document.head.appendChild(styleElement)
    }

    styleElement.textContent = fontFaceRules
    console.log(`[LAYOUT PREVIEW] Loaded ${fonts.length} fonts`)
  }, [fonts])

  const loadLayoutConfig = async () => {
    setIsLoading(true)
    try {
      const [layoutData, fontsData] = await Promise.all([
        getLayoutConfig(runId),
        getAvailableFonts(),
      ])

      setConfig(layoutData.layout_config)
      setTitle(layoutData.title)
      setFonts(fontsData)
    } catch (err: any) {
      console.error('Failed to load layout config:', err)
      alert('레이아웃 설정을 불러오는데 실패했습니다: ' + err.message)
    } finally {
      setIsLoading(false)
    }
  }

  const handleApprove = async () => {
    if (!config) return

    setIsConfirming(true)
    try {
      await confirmLayoutWithConfig(runId, config, title)
      onClose()
    } catch (err: any) {
      console.error('Failed to confirm layout:', err)
      alert('레이아웃 확정 실패: ' + err.message)
    } finally {
      setIsConfirming(false)
    }
  }

  const handleRegenerate = async () => {
    if (!confirm('에셋을 재생성하시겠습니까? 현재 에셋은 삭제됩니다.')) {
      return
    }

    setIsRegenerating(true)
    try {
      await regenerateLayout(runId)
      alert('에셋 재생성이 시작되었습니다. 잠시 후 새로운 레이아웃이 표시됩니다.')
      onClose()
    } catch (err: any) {
      console.error('Failed to regenerate assets:', err)
      alert('에셋 재생성 실패: ' + err.message)
    } finally {
      setIsRegenerating(false)
    }
  }

  const updateConfig = (key: keyof LayoutConfig, value: any) => {
    if (!config) return
    setConfig({ ...config, [key]: value })
  }

  if (isLoading) {
    return (
      <div style={overlayStyle}>
        <div style={modalStyle}>
          <h2>레이아웃 설정 로딩 중...</h2>
          <p>잠시만 기다려주세요.</p>
        </div>
      </div>
    )
  }

  if (!config) return null

  return (
    <div className="enhancement-modal-overlay">
      <div className="enhancement-modal-container">
        <div className="enhancement-modal-layout">
          {/* Left Stepper */}
          <div className="enhancement-stepper">
            <h3 style={{ fontSize: '18px', fontWeight: '700', marginBottom: '24px', color: '#111827' }}>
              제작 단계
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

              {/* Step 1: 시나리오 작성 (Completed) */}
              <div style={{ position: 'relative', display: 'flex', alignItems: 'flex-start', gap: '12px', paddingBottom: '24px' }}>
                <div className="enhancement-step-icon" style={{ backgroundColor: '#7189a0', border: '2px solid #7189a0' }}>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="#FFFFFF">
                    <path d="M19.7071 6.29289C20.0976 6.68342 20.0976 7.31658 19.7071 7.70711L9.70711 17.7071C9.31658 18.0976 8.68342 18.0976 8.29289 17.7071L4.29289 13.7071C3.90237 13.3166 3.90237 12.6834 4.29289 12.2929C4.68342 11.9024 5.31658 11.9024 5.70711 12.2929L9 15.5858L18.2929 6.29289C18.6834 5.90237 19.3166 5.90237 19.7071 6.29289Z"/>
                  </svg>
                </div>
                <div style={{ flex: 1, paddingTop: '4px' }}>
                  <div style={{ fontSize: '15px', fontWeight: '600', color: '#6B7280', marginBottom: '4px' }}>
                    시나리오 작성
                  </div>
                  <div style={{ fontSize: '13px', color: '#9CA3AF', lineHeight: '1.4' }}>
                    완료됨
                  </div>
                </div>
                <div style={{ position: 'absolute', left: '21px', top: '44px', bottom: '0', width: '2px', backgroundColor: '#7189a0' }} />
              </div>

              {/* Step 2: 에셋 생성 (Completed) */}
              <div style={{ position: 'relative', display: 'flex', alignItems: 'flex-start', gap: '12px', paddingBottom: '24px' }}>
                <div className="enhancement-step-icon" style={{ backgroundColor: '#7189a0', border: '2px solid #7189a0' }}>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="#FFFFFF">
                    <path d="M19.7071 6.29289C20.0976 6.68342 20.0976 7.31658 19.7071 7.70711L9.70711 17.7071C9.31658 18.0976 8.68342 18.0976 8.29289 17.7071L4.29289 13.7071C3.90237 13.3166 3.90237 12.6834 4.29289 12.2929C4.68342 11.9024 5.31658 11.9024 5.70711 12.2929L9 15.5858L18.2929 6.29289C18.6834 5.90237 19.3166 5.90237 19.7071 6.29289Z"/>
                  </svg>
                </div>
                <div style={{ flex: 1, paddingTop: '4px' }}>
                  <div style={{ fontSize: '15px', fontWeight: '600', color: '#6B7280', marginBottom: '4px' }}>
                    에셋 생성
                  </div>
                  <div style={{ fontSize: '13px', color: '#9CA3AF', lineHeight: '1.4' }}>
                    완료됨
                  </div>
                </div>
                <div style={{ position: 'absolute', left: '21px', top: '44px', bottom: '0', width: '2px', backgroundColor: '#7189a0' }} />
              </div>

              {/* Step 3: 레이아웃 설정 (Active) */}
              <div style={{ position: 'relative', display: 'flex', alignItems: 'flex-start', gap: '12px', paddingBottom: '24px' }}>
                <div className="enhancement-step-icon" style={{ backgroundColor: '#6f9fa0', border: '2px solid #6f9fa0', boxShadow: '0 0 0 4px rgba(111, 159, 160, 0.1)' }}>
                  <div className="enhancement-step-spinner"></div>
                </div>
                <div style={{ flex: 1, paddingTop: '4px' }}>
                  <div style={{ fontSize: '15px', fontWeight: '700', color: '#111827', marginBottom: '4px' }}>
                    레이아웃 설정
                  </div>
                  <div style={{ fontSize: '13px', color: '#9CA3AF', lineHeight: '1.4' }}>
                    제목 블록과 폰트를 설정합니다
                  </div>
                </div>
                <div style={{ position: 'absolute', left: '21px', top: '44px', bottom: '0', width: '2px', backgroundColor: '#E5E7EB' }} />
              </div>

              {/* Step 4: 영상 합성 (Pending) */}
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

              {/* Step 5: 품질 검수 (Pending) */}
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
          </div>

          {/* Right Content */}
          <div className="enhancement-content">
            <div className="enhancement-content-header">
              <h3 className="enhancement-modal-title">🎨 레이아웃 설정</h3>
              <p style={{ fontSize: '14px', color: '#6B7280', marginTop: '4px' }}>Run ID: {runId}</p>
            </div>

            <div style={{ flex: 1, overflowY: 'auto', padding: '0 32px 32px 32px' }}>
              <div style={infoBoxStyle}>
                <div style={{ marginBottom: '12px' }}>
                  <label style={{ display: 'block', fontSize: '14px', fontWeight: '600', color: '#374151', marginBottom: '6px' }}>
                    📝 영상 제목
                  </label>
                  <textarea
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="영상 제목을 입력하세요 (줄바꿈 가능)"
                    rows={2}
                    style={{
                      width: '100%',
                      padding: '10px 12px',
                      fontSize: '15px',
                      border: '2px solid #D1D5DB',
                      borderRadius: '6px',
                      backgroundColor: '#FFFFFF',
                      transition: 'border-color 0.2s',
                      outline: 'none',
                      resize: 'vertical',
                      fontFamily: 'inherit',
                      lineHeight: '1.5'
                    }}
                    onFocus={(e) => e.target.style.borderColor = '#6f9fa0'}
                    onBlur={(e) => e.target.style.borderColor = '#D1D5DB'}
                  />
                </div>
                <p style={{ fontSize: '14px', color: '#6B7280' }}>
                  영상 렌더링 시 사용될 제목 블록과 자막 스타일을 설정합니다. 설정 후 "승인" 버튼을 누르면 영상 합성이 시작됩니다.
                </p>
              </div>

              {/* 2-Column Layout: Preview Left, Controls Right */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.2fr', gap: '24px', marginTop: '20px' }}>
                {/* Left Column: Preview */}
                <div style={sectionStyle}>
                  <h3 style={sectionTitleStyle}>👁️ 미리보기</h3>
                  <div style={previewContainerStyle}>
                    {/* Title Block */}
                    {config.use_title_block && (
                      <div style={{
                        backgroundColor: config.title_bg_color,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        padding: '20px 10px',  // Increased from 10px to match backend
                        boxSizing: 'border-box',
                        minHeight: '40px'
                      }}>
                        <span style={{
                          color: 'white',
                          fontSize: `${config.title_font_size / 4.32}px`,
                          fontFamily: config.title_font,
                          fontWeight: 'bold',
                          whiteSpace: 'pre-wrap',
                          textAlign: 'center',
                          lineHeight: '1.2'
                        }}>
                          {title || '샘플 타이틀'}
                        </span>
                      </div>
                    )}
                    {/* Content area */}
                    <div style={{
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
                          fontSize: `${config.subtitle_font_size / 4.32}px`,
                          fontFamily: config.subtitle_font,
                          color: 'black',
                          fontWeight: 'bold',
                          textAlign: 'center',
                          width: '90%'
                        }}>
                          자막 미리보기 텍스트
                        </span>
                      </div>
                      {/* Image placeholder area */}
                      <div style={{
                        flex: 1,
                        width: '100%',
                        position: 'relative',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        backgroundColor: '#f5f5f5'
                      }}>
                        <span style={{
                          fontSize: '12px',
                          color: '#9CA3AF'
                        }}>
                          이미지 영역
                        </span>
                      </div>
                    </div>
                  </div>
                  <p style={fieldHintStyle}>
                    실제 크기는 위 미리보기의 약 3.86배입니다
                  </p>
                </div>

                {/* Right Column: Controls */}
                <div>

              {/* 제목 블록 섹션 */}
              <div style={sectionStyle}>
                <h3 style={sectionTitleStyle}>📝 제목 블록</h3>

                <div style={formFieldStyle}>
                  <label style={checkboxLabelStyle}>
                    <input
                      type="checkbox"
                      checked={config.use_title_block}
                      onChange={(e) => updateConfig('use_title_block', e.target.checked)}
                      style={checkboxStyle}
                    />
                    <span style={labelTextStyle}>제목 블록 사용</span>
                  </label>
                  <p style={fieldHintStyle}>
                    체크하면 영상 상단에 제목 블록이 표시됩니다
                  </p>
                </div>

                {config.use_title_block && (
                  <>
                    <div style={formFieldStyle}>
                      <label style={fieldLabelStyle}>🎨 배경 색상</label>
                      <div style={colorPickerContainerStyle}>
                        <input
                          type="color"
                          value={config.title_bg_color}
                          onChange={(e) => updateConfig('title_bg_color', e.target.value)}
                          style={colorInputStyle}
                        />
                        <input
                          type="text"
                          value={config.title_bg_color}
                          onChange={(e) => updateConfig('title_bg_color', e.target.value)}
                          style={inputStyle}
                          placeholder="#323296"
                        />
                      </div>
                    </div>

                    <div style={formFieldStyle}>
                      <label style={fieldLabelStyle}>📏 제목 폰트 크기: {config.title_font_size}</label>
                      <input
                        type="range"
                        value={config.title_font_size}
                        onChange={(e) => updateConfig('title_font_size', parseInt(e.target.value))}
                        min={80}
                        max={120}
                        style={sliderStyle}
                      />
                      <p style={fieldHintStyle}>
                        추천 범위: 80 ~ 120
                      </p>
                    </div>

                    <div style={formFieldStyle}>
                      <label style={fieldLabelStyle}>🔤 제목 폰트</label>
                      <select
                        value={config.title_font}
                        onChange={(e) => updateConfig('title_font', e.target.value)}
                        style={selectStyle}
                      >
                        {fonts.map((font) => (
                          <option key={font.id} value={font.id}>
                            {font.name}
                          </option>
                        ))}
                      </select>
                    </div>
                  </>
                )}
              </div>

              {/* 자막 설정 섹션 */}
              <div style={sectionStyle}>
                <h3 style={sectionTitleStyle}>💬 자막 설정</h3>

                <div style={formFieldStyle}>
                  <label style={fieldLabelStyle}>📏 자막 폰트 크기: {config.subtitle_font_size}</label>
                  <input
                    type="range"
                    value={config.subtitle_font_size}
                    onChange={(e) => updateConfig('subtitle_font_size', parseInt(e.target.value))}
                    min={60}
                    max={100}
                    style={sliderStyle}
                  />
                  <p style={fieldHintStyle}>
                    추천 범위: 60 ~ 100
                  </p>
                </div>

                <div style={formFieldStyle}>
                  <label style={fieldLabelStyle}>🔤 자막 폰트</label>
                  <select
                    value={config.subtitle_font}
                    onChange={(e) => updateConfig('subtitle_font', e.target.value)}
                    style={selectStyle}
                  >
                    {fonts.map((font) => (
                      <option key={font.id} value={font.id}>
                        {font.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

                </div>
                {/* End Right Column */}
              </div>
              {/* End 2-Column Grid */}
            </div>

            <div style={footerStyle}>
              <button
                onClick={handleRegenerate}
                disabled={isRegenerating || isConfirming}
                style={{
                  ...buttonStyle,
                  ...rejectButtonStyle,
                  ...(isRegenerating ? disabledButtonStyle : {})
                }}
              >
                {isRegenerating ? '재생성 중...' : '거부 및 재생성'}
              </button>
              <button
                onClick={handleApprove}
                disabled={isConfirming || isRegenerating}
                style={{
                  ...buttonStyle,
                  ...approveButtonStyle,
                  ...(isConfirming ? disabledButtonStyle : {})
                }}
              >
                {isConfirming ? '처리 중...' : '승인 및 다음 단계'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// Styles
const overlayStyle: React.CSSProperties = {
  position: 'fixed',
  top: 0,
  left: 0,
  right: 0,
  bottom: 0,
  backgroundColor: 'rgba(0, 0, 0, 0.7)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  zIndex: 9999,
}

const modalStyle: React.CSSProperties = {
  backgroundColor: '#FFFFFF',
  borderRadius: '16px',
  maxWidth: '1200px',
  width: '90vw',
  maxHeight: '90vh',
  boxShadow: '0 20px 60px rgba(0, 0, 0, 0.3)',
  overflow: 'hidden',
}

// Unused style variables removed for TypeScript compliance

const infoBoxStyle: React.CSSProperties = {
  backgroundColor: '#F3F4F6',
  padding: '15px',
  borderRadius: '8px',
  marginBottom: '20px',
}

const sectionStyle: React.CSSProperties = {
  marginBottom: '32px',
}

const sectionTitleStyle: React.CSSProperties = {
  fontSize: '18px',
  fontWeight: '700',
  marginBottom: '16px',
  color: '#111827',
}

const formFieldStyle: React.CSSProperties = {
  marginBottom: '16px',
}

const fieldLabelStyle: React.CSSProperties = {
  display: 'block',
  fontSize: '13px',
  fontWeight: '600',
  color: '#4B5563',
  marginBottom: '6px',
}

const checkboxLabelStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: '8px',
  cursor: 'pointer',
}

const labelTextStyle: React.CSSProperties = {
  fontSize: '14px',
  fontWeight: '600',
  color: '#374151',
}

const checkboxStyle: React.CSSProperties = {
  width: '20px',
  height: '20px',
  cursor: 'pointer',
}

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '8px 10px',
  fontSize: '14px',
  border: '1px solid #D1D5DB',
  borderRadius: '4px',
  fontFamily: 'inherit',
}

const sliderStyle: React.CSSProperties = {
  width: '100%',
  height: '6px',
  borderRadius: '3px',
  background: '#E5E7EB',
  outline: 'none',
  cursor: 'pointer',
}

const selectStyle: React.CSSProperties = {
  width: '100%',
  padding: '8px 10px',
  fontSize: '14px',
  border: '1px solid #D1D5DB',
  borderRadius: '4px',
  backgroundColor: '#FFFFFF',
  cursor: 'pointer',
  fontFamily: 'inherit',
}

const colorPickerContainerStyle: React.CSSProperties = {
  display: 'flex',
  gap: '12px',
  alignItems: 'center',
}

const colorInputStyle: React.CSSProperties = {
  width: '60px',
  height: '40px',
  border: '1px solid #D1D5DB',
  borderRadius: '4px',
  cursor: 'pointer',
}

const fieldHintStyle: React.CSSProperties = {
  fontSize: '12px',
  color: '#9CA3AF',
  marginTop: '6px',
}

const previewContainerStyle: React.CSSProperties = {
  border: '2px solid #ddd',
  borderRadius: '8px',
  overflow: 'hidden',
  background: 'white',
  aspectRatio: '9/16',
  maxWidth: '250px',
  margin: '0 auto',
  display: 'flex',
  flexDirection: 'column',
}

const footerStyle: React.CSSProperties = {
  padding: '24px 32px',
  borderTop: '1px solid #E5E7EB',
  display: 'flex',
  gap: '12px',
  justifyContent: 'flex-end',
  backgroundColor: '#F9FAFB',
}

const buttonStyle: React.CSSProperties = {
  padding: '12px 24px',
  borderRadius: '8px',
  border: 'none',
  fontSize: '15px',
  fontWeight: '600',
  cursor: 'pointer',
  transition: 'all 0.2s',
}

const rejectButtonStyle: React.CSSProperties = {
  backgroundColor: '#FFFFFF',
  color: '#DC2626',
  border: '2px solid #DC2626',
}

const approveButtonStyle: React.CSSProperties = {
  backgroundColor: '#6f9fa0',
  color: '#FFFFFF',
}

const disabledButtonStyle: React.CSSProperties = {
  opacity: 0.5,
  cursor: 'not-allowed',
}
