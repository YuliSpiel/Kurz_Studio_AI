import { useState, useEffect } from 'react'
import { getAvailableFonts, Font } from '../api/client'
import './VideoSettingsModal.css'

export interface VideoSettings {
  use_title_block: boolean
  title_bg_color: string
  title_font: string
  title_font_size: number
  subtitle_font: string
  subtitle_font_size: number
}

const DEFAULT_SETTINGS: VideoSettings = {
  use_title_block: true,
  title_bg_color: '#323296',
  title_font: 'AppleGothic',
  title_font_size: 100,
  subtitle_font: 'AppleGothic',
  subtitle_font_size: 80,
}

const STORAGE_KEY = 'kurz_video_settings'

export function loadVideoSettings(): VideoSettings {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) {
      return { ...DEFAULT_SETTINGS, ...JSON.parse(saved) }
    }
  } catch (e) {
    console.error('Failed to load video settings:', e)
  }
  return DEFAULT_SETTINGS
}

export function saveVideoSettings(settings: VideoSettings): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings))
  } catch (e) {
    console.error('Failed to save video settings:', e)
  }
}

interface VideoSettingsModalProps {
  isOpen: boolean
  onClose: () => void
}

export default function VideoSettingsModal({ isOpen, onClose }: VideoSettingsModalProps) {
  const [settings, setSettings] = useState<VideoSettings>(loadVideoSettings)
  const [fonts, setFonts] = useState<Font[]>([
    { id: 'AppleGothic', name: 'Apple Gothic (시스템)', path: 'AppleGothic' },
    { id: 'AppleMyungjo', name: 'Apple Myungjo (시스템)', path: 'AppleMyungjo' }
  ])
  const [isSaving, setIsSaving] = useState(false)

  useEffect(() => {
    if (isOpen) {
      setSettings(loadVideoSettings())
      loadFonts()
    }
  }, [isOpen])

  const loadFonts = async () => {
    try {
      const fontsData = await getAvailableFonts()
      if (fontsData && fontsData.length > 0) {
        setFonts(fontsData)

        // Dynamically load custom fonts for preview
        fontsData.forEach(font => {
          if (font.id.startsWith('Apple')) return

          const fontFace = new FontFace(font.id, `url(/api/fonts/${font.id})`)
          fontFace.load().then(loadedFont => {
            document.fonts.add(loadedFont)
          }).catch(err => {
            console.warn(`Failed to load font ${font.id}:`, err)
          })
        })
      }
    } catch (error) {
      console.error('Failed to load fonts:', error)
    }
  }

  const updateSetting = <K extends keyof VideoSettings>(key: K, value: VideoSettings[K]) => {
    setSettings(prev => ({ ...prev, [key]: value }))
  }

  const handleSave = () => {
    setIsSaving(true)
    saveVideoSettings(settings)
    setTimeout(() => {
      setIsSaving(false)
      onClose()
    }, 300)
  }

  const handleReset = () => {
    if (confirm('설정을 기본값으로 초기화하시겠습니까?')) {
      setSettings(DEFAULT_SETTINGS)
    }
  }

  if (!isOpen) return null

  return (
    <div className="video-settings-overlay" onClick={onClose}>
      <div className="video-settings-modal" onClick={e => e.stopPropagation()}>
        <div className="video-settings-header">
          <h2>영상 설정</h2>
          <p className="video-settings-subtitle">새로 만드는 영상에 기본으로 적용될 레이아웃을 설정합니다</p>
          <button className="video-settings-close" onClick={onClose}>
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>

        <div className="video-settings-content">
          <div className="video-settings-grid">
            {/* Preview Section */}
            <div className="video-settings-preview-section">
              <h3>미리보기</h3>
              <div className="video-settings-preview">
                {settings.use_title_block && (
                  <div
                    className="preview-title-block"
                    style={{ backgroundColor: settings.title_bg_color }}
                  >
                    <span style={{
                      fontFamily: settings.title_font,
                      fontSize: `${settings.title_font_size / 4.5}px`,
                    }}>
                      샘플 타이틀
                    </span>
                  </div>
                )}
                <div className="preview-content-area">
                  <div className="preview-subtitle" style={{
                    fontFamily: settings.subtitle_font,
                    fontSize: `${settings.subtitle_font_size / 4.5}px`,
                  }}>
                    자막 미리보기 텍스트
                  </div>
                  <div className="preview-image-placeholder">
                    <span>이미지 영역</span>
                  </div>
                </div>
              </div>
              <p className="preview-hint">실제 크기는 약 4.5배입니다</p>
            </div>

            {/* Settings Section */}
            <div className="video-settings-controls">
              {/* Title Block Section */}
              <div className="settings-section">
                <h3>제목 블록</h3>

                <label className="checkbox-field">
                  <input
                    type="checkbox"
                    checked={settings.use_title_block}
                    onChange={e => updateSetting('use_title_block', e.target.checked)}
                  />
                  <span>제목 블록 사용</span>
                </label>

                {settings.use_title_block && (
                  <>
                    <div className="form-field">
                      <label>배경 색상</label>
                      <div className="color-input-group">
                        <input
                          type="color"
                          value={settings.title_bg_color}
                          onChange={e => updateSetting('title_bg_color', e.target.value)}
                        />
                        <input
                          type="text"
                          value={settings.title_bg_color}
                          onChange={e => updateSetting('title_bg_color', e.target.value)}
                          placeholder="#323296"
                        />
                      </div>
                    </div>

                    <div className="form-field">
                      <label>제목 폰트</label>
                      <select
                        value={settings.title_font}
                        onChange={e => updateSetting('title_font', e.target.value)}
                      >
                        {fonts.map(font => (
                          <option key={font.id} value={font.id}>{font.name}</option>
                        ))}
                      </select>
                    </div>

                    <div className="form-field">
                      <label>제목 폰트 크기: {settings.title_font_size}</label>
                      <input
                        type="range"
                        min={80}
                        max={120}
                        value={settings.title_font_size}
                        onChange={e => updateSetting('title_font_size', parseInt(e.target.value))}
                      />
                    </div>
                  </>
                )}
              </div>

              {/* Subtitle Section */}
              <div className="settings-section">
                <h3>자막 설정</h3>

                <div className="form-field">
                  <label>자막 폰트</label>
                  <select
                    value={settings.subtitle_font}
                    onChange={e => updateSetting('subtitle_font', e.target.value)}
                  >
                    {fonts.map(font => (
                      <option key={font.id} value={font.id}>{font.name}</option>
                    ))}
                  </select>
                </div>

                <div className="form-field">
                  <label>자막 폰트 크기: {settings.subtitle_font_size}</label>
                  <input
                    type="range"
                    min={60}
                    max={100}
                    value={settings.subtitle_font_size}
                    onChange={e => updateSetting('subtitle_font_size', parseInt(e.target.value))}
                  />
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="video-settings-footer">
          <button className="btn-reset" onClick={handleReset}>
            기본값으로 초기화
          </button>
          <div className="footer-right">
            <button className="btn-cancel" onClick={onClose}>
              취소
            </button>
            <button className="btn-save" onClick={handleSave} disabled={isSaving}>
              {isSaving ? '저장 중...' : '저장'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
