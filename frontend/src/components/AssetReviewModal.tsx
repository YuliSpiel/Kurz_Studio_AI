import { useState, useEffect } from 'react'
import {
  getAssets,
  confirmAssets,
  regenerateSceneImage,
  regenerateBgm,
  SceneAsset,
  BgmAsset
} from '../api/client'

interface AssetReviewModalProps {
  runId: string
  isOpen: boolean
  onConfirm: () => void
  onClose: () => void
}

export default function AssetReviewModal({
  runId,
  isOpen,
  onConfirm,
  onClose
}: AssetReviewModalProps) {
  const [scenes, setScenes] = useState<SceneAsset[]>([])
  const [bgm, setBgm] = useState<BgmAsset | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [regeneratingScenes, setRegeneratingScenes] = useState<Set<string>>(new Set())
  const [regeneratingBgm, setRegeneratingBgm] = useState(false)
  const [editingPrompt, setEditingPrompt] = useState<{ sceneId: string; prompt: string } | null>(null)
  const [editingBgmPrompt, setEditingBgmPrompt] = useState<string | null>(null)
  const [confirming, setConfirming] = useState(false)
  const [selectedScene, setSelectedScene] = useState<SceneAsset | null>(null)

  useEffect(() => {
    if (isOpen && runId) {
      loadAssets()
    }
  }, [isOpen, runId])

  const loadAssets = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await getAssets(runId)
      setScenes(data.scenes)
      setBgm(data.bgm)
      if (data.scenes.length > 0) {
        setSelectedScene(data.scenes[0])
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load assets')
    } finally {
      setLoading(false)
    }
  }

  const handleRegenerateImage = async (sceneId: string, newPrompt?: string) => {
    setRegeneratingScenes(prev => new Set(prev).add(sceneId))
    try {
      const result = await regenerateSceneImage(runId, sceneId, newPrompt)
      setScenes(prev =>
        prev.map(s =>
          s.scene_id === sceneId
            ? { ...s, image_url: result.image_url + '?t=' + Date.now() }
            : s
        )
      )
      if (selectedScene?.scene_id === sceneId) {
        setSelectedScene(prev => prev ? { ...prev, image_url: result.image_url + '?t=' + Date.now() } : null)
      }
      setEditingPrompt(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to regenerate image')
    } finally {
      setRegeneratingScenes(prev => {
        const next = new Set(prev)
        next.delete(sceneId)
        return next
      })
    }
  }

  const handleRegenerateBgm = async (newPrompt?: string) => {
    setRegeneratingBgm(true)
    try {
      const result = await regenerateBgm(runId, newPrompt)
      setBgm(prev => prev ? { ...prev, audio_url: result.audio_url + '?t=' + Date.now() } : null)
      setEditingBgmPrompt(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to regenerate BGM')
    } finally {
      setRegeneratingBgm(false)
    }
  }

  const handleConfirm = async () => {
    setConfirming(true)
    try {
      await confirmAssets(runId)
      onConfirm()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to confirm assets')
    } finally {
      setConfirming(false)
    }
  }

  if (!isOpen) return null

  if (loading) {
    return (
      <div className="enhancement-modal-overlay">
        <div className="enhancement-modal-container">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '400px', flexDirection: 'column', gap: '16px' }}>
            <div className="enhancement-step-spinner" style={{ width: '40px', height: '40px' }}></div>
            <p style={{ color: '#6B7280' }}>에셋 로딩 중...</p>
          </div>
        </div>
      </div>
    )
  }

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

              {/* Step 2: 에셋 검수 (Active) */}
              <div style={{ position: 'relative', display: 'flex', alignItems: 'flex-start', gap: '12px', paddingBottom: '24px' }}>
                <div className="enhancement-step-icon" style={{ backgroundColor: '#6f9fa0', border: '2px solid #6f9fa0', boxShadow: '0 0 0 4px rgba(111, 159, 160, 0.1)' }}>
                  <div className="enhancement-step-spinner"></div>
                </div>
                <div style={{ flex: 1, paddingTop: '4px' }}>
                  <div style={{ fontSize: '15px', fontWeight: '700', color: '#111827', marginBottom: '4px' }}>
                    에셋 검수
                  </div>
                  <div style={{ fontSize: '13px', color: '#9CA3AF', lineHeight: '1.4' }}>
                    이미지와 BGM을 확인합니다
                  </div>
                </div>
                <div style={{ position: 'absolute', left: '21px', top: '44px', bottom: '0', width: '2px', backgroundColor: '#E5E7EB' }} />
              </div>

              {/* Step 3: 레이아웃 설정 (Pending) */}
              <div style={{ position: 'relative', display: 'flex', alignItems: 'flex-start', gap: '12px', paddingBottom: '24px' }}>
                <div className="enhancement-step-icon" style={{ backgroundColor: '#FFFFFF', border: '2px solid #E5E7EB' }}>
                  <span style={{ color: '#9CA3AF', fontSize: '12px', fontWeight: '600' }}>4</span>
                </div>
                <div style={{ flex: 1, paddingTop: '4px' }}>
                  <div style={{ fontSize: '15px', fontWeight: '600', color: '#9CA3AF', marginBottom: '4px' }}>
                    레이아웃 설정
                  </div>
                  <div style={{ fontSize: '13px', color: '#D1D5DB', lineHeight: '1.4' }}>
                    제목 블록과 폰트
                  </div>
                </div>
                <div style={{ position: 'absolute', left: '21px', top: '44px', bottom: '0', width: '2px', backgroundColor: '#E5E7EB' }} />
              </div>

              {/* Step 4: 영상 생성 (Pending) */}
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
                <div className="enhancement-step-icon" style={{ backgroundColor: '#FFFFFF', border: '2px solid #E5E7EB' }}>
                  <span style={{ color: '#9CA3AF', fontSize: '12px', fontWeight: '600' }}>5</span>
                </div>
                <div style={{ flex: 1, paddingTop: '4px' }}>
                  <div style={{ fontSize: '15px', fontWeight: '600', color: '#9CA3AF', marginBottom: '4px' }}>
                    영상 생성
                  </div>
                  <div style={{ fontSize: '13px', color: '#D1D5DB', lineHeight: '1.4' }}>
                    최종 영상 렌더링
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Right Content */}
          <div className="enhancement-content">
            <h2 style={{ fontSize: '24px', fontWeight: '700', color: '#111827', marginBottom: '8px' }}>
              에셋 검수
            </h2>
            <p style={{ fontSize: '14px', color: '#6B7280', marginBottom: '24px' }}>
              생성된 이미지와 BGM을 확인하고, 필요시 재생성할 수 있습니다
            </p>

            {error && (
              <div style={{ padding: '12px', backgroundColor: '#FEE2E2', borderRadius: '8px', marginBottom: '16px', color: '#DC2626', fontSize: '14px' }}>
                {error}
              </div>
            )}

            {/* BGM Section */}
            <div style={{ marginBottom: '24px', padding: '16px', backgroundColor: '#F9FAFB', borderRadius: '12px' }}>
              <h3 style={{ fontSize: '16px', fontWeight: '600', color: '#111827', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#6f9fa0" strokeWidth="2">
                  <path d="M9 18V5l12-2v13"/>
                  <circle cx="6" cy="18" r="3"/>
                  <circle cx="18" cy="16" r="3"/>
                </svg>
                배경음악 (BGM)
              </h3>
              {bgm?.audio_url ? (
                <audio controls src={bgm.audio_url} style={{ width: '100%', marginBottom: '12px' }} />
              ) : (
                <p style={{ color: '#9CA3AF', marginBottom: '12px' }}>배경음악이 없습니다</p>
              )}
              <div style={{ fontSize: '13px', color: '#6B7280', marginBottom: '8px' }}>
                <span style={{ fontWeight: '500' }}>프롬프트:</span> {bgm?.prompt || '(없음)'}
              </div>
              {editingBgmPrompt !== null ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <textarea
                    value={editingBgmPrompt}
                    onChange={e => setEditingBgmPrompt(e.target.value)}
                    rows={2}
                    style={{ padding: '8px', borderRadius: '6px', border: '1px solid #D1D5DB', fontSize: '13px' }}
                  />
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button onClick={() => setEditingBgmPrompt(null)} style={{ padding: '6px 12px', fontSize: '13px', border: '1px solid #D1D5DB', borderRadius: '6px', background: 'white', cursor: 'pointer' }}>
                      취소
                    </button>
                    <button
                      onClick={() => handleRegenerateBgm(editingBgmPrompt)}
                      disabled={regeneratingBgm}
                      style={{ padding: '6px 12px', fontSize: '13px', border: 'none', borderRadius: '6px', background: '#6f9fa0', color: 'white', cursor: 'pointer' }}
                    >
                      {regeneratingBgm ? '재생성 중...' : '재생성'}
                    </button>
                  </div>
                </div>
              ) : (
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button onClick={() => setEditingBgmPrompt(bgm?.prompt || '')} style={{ padding: '6px 12px', fontSize: '13px', border: '1px solid #D1D5DB', borderRadius: '6px', background: 'white', cursor: 'pointer' }}>
                    프롬프트 수정
                  </button>
                  <button
                    onClick={() => handleRegenerateBgm()}
                    disabled={regeneratingBgm}
                    style={{ padding: '6px 12px', fontSize: '13px', border: 'none', borderRadius: '6px', background: '#6f9fa0', color: 'white', cursor: 'pointer' }}
                  >
                    {regeneratingBgm ? '재생성 중...' : '재생성'}
                  </button>
                </div>
              )}
            </div>

            {/* Scenes Section */}
            <div>
              <h3 style={{ fontSize: '16px', fontWeight: '600', color: '#111827', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#6f9fa0" strokeWidth="2">
                  <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
                  <circle cx="8.5" cy="8.5" r="1.5"/>
                  <polyline points="21 15 16 10 5 21"/>
                </svg>
                씬 이미지 ({scenes.length}개)
              </h3>

              {/* Scene thumbnails */}
              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '16px' }}>
                {scenes.map(scene => (
                  <div
                    key={scene.scene_id}
                    onClick={() => setSelectedScene(scene)}
                    style={{
                      width: '60px',
                      height: '80px',
                      borderRadius: '8px',
                      overflow: 'hidden',
                      cursor: 'pointer',
                      border: selectedScene?.scene_id === scene.scene_id ? '3px solid #6f9fa0' : '2px solid #E5E7EB',
                      position: 'relative'
                    }}
                  >
                    {regeneratingScenes.has(scene.scene_id) ? (
                      <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#F3F4F6' }}>
                        <div className="enhancement-step-spinner" style={{ width: '20px', height: '20px' }}></div>
                      </div>
                    ) : (
                      <img src={scene.image_url || ''} alt={`Scene ${scene.scene_number}`} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                    )}
                    <div style={{ position: 'absolute', bottom: '2px', left: '50%', transform: 'translateX(-50%)', fontSize: '10px', fontWeight: '600', color: 'white', textShadow: '0 1px 2px rgba(0,0,0,0.5)' }}>
                      {scene.scene_number}
                    </div>
                  </div>
                ))}
              </div>

              {/* Selected scene detail */}
              {selectedScene && (
                <div style={{ padding: '16px', backgroundColor: '#F9FAFB', borderRadius: '12px' }}>
                  <div style={{ display: 'flex', gap: '16px' }}>
                    <div style={{ width: '200px', flexShrink: 0 }}>
                      {regeneratingScenes.has(selectedScene.scene_id) ? (
                        <div style={{ width: '200px', height: '280px', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#E5E7EB', borderRadius: '8px' }}>
                          <div className="enhancement-step-spinner" style={{ width: '32px', height: '32px' }}></div>
                        </div>
                      ) : (
                        <img src={selectedScene.image_url || ''} alt={`Scene ${selectedScene.scene_number}`} style={{ width: '200px', height: '280px', objectFit: 'cover', borderRadius: '8px' }} />
                      )}
                    </div>
                    <div style={{ flex: 1 }}>
                      <h4 style={{ fontSize: '15px', fontWeight: '600', color: '#111827', marginBottom: '8px' }}>
                        씬 {selectedScene.scene_number}
                      </h4>
                      <div style={{ fontSize: '13px', color: '#6B7280', marginBottom: '8px' }}>
                        <span style={{ fontWeight: '500' }}>대사:</span> {selectedScene.narration || '(없음)'}
                      </div>
                      <div style={{ fontSize: '13px', color: '#6B7280', marginBottom: '12px' }}>
                        <span style={{ fontWeight: '500' }}>프롬프트:</span> {selectedScene.image_prompt?.slice(0, 150)}{(selectedScene.image_prompt?.length || 0) > 150 ? '...' : ''}
                      </div>
                      {editingPrompt?.sceneId === selectedScene.scene_id ? (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                          <textarea
                            value={editingPrompt.prompt}
                            onChange={e => setEditingPrompt({ ...editingPrompt, prompt: e.target.value })}
                            rows={3}
                            style={{ padding: '8px', borderRadius: '6px', border: '1px solid #D1D5DB', fontSize: '13px' }}
                          />
                          <div style={{ display: 'flex', gap: '8px' }}>
                            <button onClick={() => setEditingPrompt(null)} style={{ padding: '6px 12px', fontSize: '13px', border: '1px solid #D1D5DB', borderRadius: '6px', background: 'white', cursor: 'pointer' }}>
                              취소
                            </button>
                            <button
                              onClick={() => handleRegenerateImage(selectedScene.scene_id, editingPrompt.prompt)}
                              disabled={regeneratingScenes.has(selectedScene.scene_id)}
                              style={{ padding: '6px 12px', fontSize: '13px', border: 'none', borderRadius: '6px', background: '#6f9fa0', color: 'white', cursor: 'pointer' }}
                            >
                              재생성
                            </button>
                          </div>
                        </div>
                      ) : (
                        <div style={{ display: 'flex', gap: '8px' }}>
                          <button onClick={() => setEditingPrompt({ sceneId: selectedScene.scene_id, prompt: selectedScene.image_prompt || '' })} style={{ padding: '6px 12px', fontSize: '13px', border: '1px solid #D1D5DB', borderRadius: '6px', background: 'white', cursor: 'pointer' }}>
                            프롬프트 수정
                          </button>
                          <button
                            onClick={() => handleRegenerateImage(selectedScene.scene_id)}
                            disabled={regeneratingScenes.has(selectedScene.scene_id)}
                            style={{ padding: '6px 12px', fontSize: '13px', border: 'none', borderRadius: '6px', background: '#6f9fa0', color: 'white', cursor: 'pointer' }}
                          >
                            재생성
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Footer Buttons */}
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '24px', paddingTop: '24px', borderTop: '1px solid #E5E7EB' }}>
              <button
                onClick={onClose}
                style={{ padding: '12px 24px', fontSize: '15px', fontWeight: '500', border: '1px solid #D1D5DB', borderRadius: '8px', background: 'white', cursor: 'pointer' }}
              >
                닫기
              </button>
              <button
                onClick={handleConfirm}
                disabled={loading || confirming || regeneratingScenes.size > 0 || regeneratingBgm}
                style={{
                  padding: '12px 24px',
                  fontSize: '15px',
                  fontWeight: '600',
                  border: 'none',
                  borderRadius: '8px',
                  background: (confirming || regeneratingScenes.size > 0 || regeneratingBgm) ? '#9CA3AF' : '#6f9fa0',
                  color: 'white',
                  cursor: (confirming || regeneratingScenes.size > 0 || regeneratingBgm) ? 'not-allowed' : 'pointer'
                }}
              >
                {confirming ? '확인 중...' : '확인 및 계속'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
