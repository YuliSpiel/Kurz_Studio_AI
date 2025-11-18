import { useState, useEffect } from 'react'
import { getPlotJson, confirmPlot, regeneratePlot, PlotJsonData } from '../api/client'

interface PlotReviewModalProps {
  runId: string
  onClose: () => void
  onConfirmed: () => void
}

interface Scene {
  scene_id: string
  image_prompt: string
  text: string
  speaker: string
  duration_ms: number
}

export default function PlotReviewModal({ runId, onClose, onConfirmed }: PlotReviewModalProps) {
  const [plotData, setPlotData] = useState<PlotJsonData | null>(null)
  const [scenes, setScenes] = useState<Scene[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isConfirming, setIsConfirming] = useState(false)
  const [isRegenerating, setIsRegenerating] = useState(false)
  const [hasEdited, setHasEdited] = useState(false)

  useEffect(() => {
    loadPlotJson()
  }, [runId])

  const loadPlotJson = async () => {
    setIsLoading(true)
    let retries = 0
    const maxRetries = 10 // 최대 10초 대기 (1초 간격)

    while (retries < maxRetries) {
      try {
        const data = await getPlotJson(runId)
        setPlotData(data)
        setScenes(data.plot.scenes)
        setIsLoading(false)
        return // 성공하면 종료
      } catch (error) {
        retries++
        if (retries >= maxRetries) {
          console.error('Failed to load plot JSON after retries:', error)
          alert('플롯 JSON 로드 실패: ' + error)
          setIsLoading(false)
          return
        }
        // 1초 대기 후 재시도
        console.log(`Plot JSON not ready yet, retrying (${retries}/${maxRetries})...`)
        await new Promise(resolve => setTimeout(resolve, 1000))
      }
    }
  }

  const handleConfirm = async () => {
    setIsConfirming(true)
    try {
      const editedPlot = hasEdited ? {
        title: plotData?.plot.title,
        bgm_prompt: plotData?.plot.bgm_prompt,
        scenes: scenes
      } : undefined
      await confirmPlot(runId, editedPlot)
      alert('플롯이 확정되었습니다. 에셋 생성이 시작됩니다.')
      onConfirmed()
      onClose()
    } catch (error) {
      console.error('Failed to confirm plot:', error)
      alert('플롯 확정 실패: ' + error)
    } finally {
      setIsConfirming(false)
    }
  }

  const handleRegenerate = async () => {
    if (!confirm('플롯을 재생성하시겠습니까? 현재 플롯은 삭제됩니다.')) {
      return
    }

    setIsRegenerating(true)
    try {
      await regeneratePlot(runId)
      alert('플롯 재생성이 시작되었습니다. 잠시 후 새로운 플롯이 표시됩니다.')
      onClose()
    } catch (error) {
      console.error('Failed to regenerate plot:', error)
      alert('플롯 재생성 실패: ' + error)
    } finally {
      setIsRegenerating(false)
    }
  }

  const handleSceneEdit = (sceneId: string, field: keyof Scene, value: string | number) => {
    setScenes(prevScenes =>
      prevScenes.map(scene =>
        scene.scene_id === sceneId ? { ...scene, [field]: value } : scene
      )
    )
    setHasEdited(true)
  }

  const handleDeleteScene = (sceneId: string) => {
    if (!confirm('이 장면을 삭제하시겠습니까?')) return
    setScenes(prevScenes => prevScenes.filter(scene => scene.scene_id !== sceneId))
    setHasEdited(true)
  }

  if (isLoading) {
    return (
      <div style={overlayStyle}>
        <div style={modalStyle}>
          <h2>플롯 로딩 중...</h2>
          <p>잠시만 기다려주세요.</p>
        </div>
      </div>
    )
  }

  return (
    <div style={overlayStyle}>
      <div style={modalStyle}>
        <div style={modalContentStyle}>
          {/* Left Stepper */}
          <div style={stepperContainerStyle}>
            <h3 style={stepperTitleStyle}>검수 단계</h3>
            <div style={stepperListStyle}>
              {/* Step 1: 시나리오 작성 (PLOT_REVIEW) */}
              <div style={stepItemStyle}>
                <div style={{
                  ...stepCircleStyle,
                  ...activeStepCircleStyle
                }}>
                  <span style={stepIconStyle}>📋</span>
                </div>
                <div style={stepLabelContainerStyle}>
                  <div style={{
                    ...stepLabelStyle,
                    ...activeStepLabelStyle
                  }}>
                    시나리오 작성
                  </div>
                  <div style={stepDescriptionStyle}>
                    플롯을 검토하고 수정합니다
                  </div>
                </div>
              </div>
              <div style={stepConnectorStyle} />

              {/* Step 2: 에셋 생성 (Pending) */}
              <div style={stepItemStyle}>
                <div style={{
                  ...stepCircleStyle,
                  ...pendingStepCircleStyle
                }}>
                  <span style={stepIconStyle}>🎨</span>
                </div>
                <div style={stepLabelContainerStyle}>
                  <div style={stepLabelStyle}>
                    에셋 생성
                  </div>
                  <div style={stepDescriptionStyle}>
                    이미지, 음악, 음성을 생성합니다
                  </div>
                </div>
              </div>
              <div style={stepConnectorStyle} />

              {/* Step 3: 영상 합성 (Pending) */}
              <div style={stepItemStyle}>
                <div style={{
                  ...stepCircleStyle,
                  ...pendingStepCircleStyle
                }}>
                  <span style={stepIconStyle}>🎬</span>
                </div>
                <div style={stepLabelContainerStyle}>
                  <div style={stepLabelStyle}>
                    영상 합성
                  </div>
                  <div style={stepDescriptionStyle}>
                    최종 영상을 합성합니다
                  </div>
                </div>
              </div>
              <div style={stepConnectorStyle} />

              {/* Step 4: 품질 검수 (Pending) */}
              <div style={stepItemStyle}>
                <div style={{
                  ...stepCircleStyle,
                  ...pendingStepCircleStyle
                }}>
                  <span style={stepIconStyle}>✅</span>
                </div>
                <div style={stepLabelContainerStyle}>
                  <div style={stepLabelStyle}>
                    품질 검수
                  </div>
                  <div style={stepDescriptionStyle}>
                    최종 품질을 검수합니다
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Right Content */}
          <div style={contentContainerStyle}>
            <div style={headerStyle}>
              <div>
                <h2 style={titleStyle}>📋 시나리오 작성</h2>
                <p style={runIdStyle}>Run ID: {runId}</p>
              </div>
              <button onClick={onClose} style={closeButtonStyle}>✕</button>
            </div>

            <div style={contentScrollStyle}>
              <div style={infoBoxStyle}>
                <p><strong>모드:</strong> {plotData?.mode || 'general'}</p>
                <p><strong>총 장면 수:</strong> {scenes.length}개</p>
                <p style={{ marginTop: '10px', fontSize: '14px', color: '#6B7280' }}>
                  각 장면을 클릭하여 수정할 수 있습니다. 수정 후 "확정" 버튼을 누르면 수정된 내용으로 영상이 생성됩니다.
                </p>
              </div>

              {hasEdited && (
                <p style={editedWarningStyle}>
                  ⚠️ 플롯이 수정되었습니다. 확정 시 수정된 내용이 반영됩니다.
                </p>
              )}

              <div style={scenesContainerStyle}>
                {scenes.map((scene, index) => (
                  <div key={scene.scene_id} style={sceneCardStyle}>
                    <div style={sceneHeaderStyle}>
                      <span style={sceneNumberStyle}>장면 {index + 1}</span>
                      <button
                        onClick={() => handleDeleteScene(scene.scene_id)}
                        style={deleteButtonStyle}
                        title="장면 삭제"
                      >
                        🗑️
                      </button>
                    </div>

                    <div style={sceneFieldStyle}>
                      <label style={fieldLabelStyle}>🎬 장면 ID</label>
                      <input
                        type="text"
                        value={scene.scene_id}
                        onChange={(e) => handleSceneEdit(scene.scene_id, 'scene_id', e.target.value)}
                        style={inputStyle}
                      />
                    </div>

                    <div style={sceneFieldStyle}>
                      <label style={fieldLabelStyle}>🖼️ 이미지 프롬프트</label>
                      <textarea
                        value={scene.image_prompt}
                        onChange={(e) => handleSceneEdit(scene.scene_id, 'image_prompt', e.target.value)}
                        style={textareaFieldStyle}
                        rows={3}
                      />
                    </div>

                    <div style={sceneFieldStyle}>
                      <label style={fieldLabelStyle}>💬 대사/자막</label>
                      <textarea
                        value={scene.text}
                        onChange={(e) => handleSceneEdit(scene.scene_id, 'text', e.target.value)}
                        style={textareaFieldStyle}
                        rows={2}
                      />
                    </div>

                    <div style={sceneRowStyle}>
                      <div style={{ ...sceneFieldStyle, flex: 1 }}>
                        <label style={fieldLabelStyle}>🎤 화자</label>
                        <input
                          type="text"
                          value={scene.speaker}
                          onChange={(e) => handleSceneEdit(scene.scene_id, 'speaker', e.target.value)}
                          style={inputStyle}
                        />
                      </div>

                      <div style={{ ...sceneFieldStyle, flex: 1 }}>
                        <label style={fieldLabelStyle}>⏱️ 길이 (ms)</label>
                        <input
                          type="number"
                          value={scene.duration_ms}
                          onChange={(e) => handleSceneEdit(scene.scene_id, 'duration_ms', parseInt(e.target.value, 10))}
                          style={inputStyle}
                          min={1000}
                          step={500}
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
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
                onClick={handleConfirm}
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

const modalContentStyle: React.CSSProperties = {
  display: 'flex',
  height: '90vh',
}

const stepperContainerStyle: React.CSSProperties = {
  width: '280px',
  backgroundColor: '#F9FAFB',
  borderRight: '1px solid #E5E7EB',
  padding: '32px 24px',
  overflowY: 'auto',
}

const stepperTitleStyle: React.CSSProperties = {
  fontSize: '18px',
  fontWeight: '700',
  marginBottom: '24px',
  color: '#111827',
}

const stepperListStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: '8px',
}

const stepItemStyle: React.CSSProperties = {
  position: 'relative',
  display: 'flex',
  alignItems: 'flex-start',
  gap: '12px',
  paddingBottom: '24px',
}

const stepCircleStyle: React.CSSProperties = {
  width: '44px',
  height: '44px',
  borderRadius: '50%',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  flexShrink: 0,
  backgroundColor: '#E5E7EB',
  border: '2px solid #D1D5DB',
}

const activeStepCircleStyle: React.CSSProperties = {
  backgroundColor: '#6f9fa0',
  border: '2px solid #6f9fa0',
  boxShadow: '0 0 0 4px rgba(111, 159, 160, 0.1)',
}

const completedStepCircleStyle: React.CSSProperties = {
  backgroundColor: '#10B981',
  border: '2px solid #10B981',
}

const pendingStepCircleStyle: React.CSSProperties = {
  backgroundColor: '#F3F4F6',
  border: '2px solid #E5E7EB',
}

const stepIconStyle: React.CSSProperties = {
  fontSize: '20px',
}

const stepLabelContainerStyle: React.CSSProperties = {
  flex: 1,
  paddingTop: '4px',
}

const stepLabelStyle: React.CSSProperties = {
  fontSize: '15px',
  fontWeight: '600',
  color: '#6B7280',
  marginBottom: '4px',
}

const activeStepLabelStyle: React.CSSProperties = {
  color: '#111827',
  fontWeight: '700',
}

const stepDescriptionStyle: React.CSSProperties = {
  fontSize: '13px',
  color: '#9CA3AF',
  lineHeight: '1.4',
}

const contentContainerStyle: React.CSSProperties = {
  flex: 1,
  display: 'flex',
  flexDirection: 'column',
  overflow: 'hidden',
}

const headerStyle: React.CSSProperties = {
  padding: '32px',
  borderBottom: '1px solid #E5E7EB',
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'flex-start',
}

const titleStyle: React.CSSProperties = {
  fontSize: '24px',
  fontWeight: '700',
  marginBottom: '8px',
  color: '#111827',
}

const runIdStyle: React.CSSProperties = {
  fontSize: '14px',
  color: '#6B7280',
}

const closeButtonStyle: React.CSSProperties = {
  background: 'none',
  border: 'none',
  fontSize: '24px',
  cursor: 'pointer',
  color: '#9CA3AF',
  padding: '4px 8px',
  transition: 'color 0.2s',
}

const contentScrollStyle: React.CSSProperties = {
  flex: 1,
  overflowY: 'auto',
  padding: '32px',
}

const infoBoxStyle: React.CSSProperties = {
  backgroundColor: '#F3F4F6',
  padding: '15px',
  borderRadius: '8px',
  marginBottom: '20px',
}

const editedWarningStyle: React.CSSProperties = {
  marginTop: '0',
  marginBottom: '16px',
  padding: '12px',
  fontSize: '13px',
  color: '#D97706',
  backgroundColor: '#FEF3C7',
  border: '1px solid #F59E0B',
  borderRadius: '6px',
  fontWeight: '500',
}

const scenesContainerStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: '16px',
}

const sceneCardStyle: React.CSSProperties = {
  backgroundColor: '#FFFFFF',
  border: '2px solid #E5E7EB',
  borderRadius: '8px',
  padding: '16px',
  transition: 'all 0.2s',
}

const sceneHeaderStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  marginBottom: '12px',
  paddingBottom: '8px',
  borderBottom: '1px solid #E5E7EB',
}

const sceneNumberStyle: React.CSSProperties = {
  fontSize: '16px',
  fontWeight: 'bold',
  color: '#1F2937',
}

const deleteButtonStyle: React.CSSProperties = {
  background: 'none',
  border: 'none',
  fontSize: '20px',
  cursor: 'pointer',
  padding: '4px',
  opacity: 0.6,
  transition: 'opacity 0.2s',
}

const sceneFieldStyle: React.CSSProperties = {
  marginBottom: '12px',
}

const sceneRowStyle: React.CSSProperties = {
  display: 'flex',
  gap: '12px',
  marginBottom: '0',
}

const fieldLabelStyle: React.CSSProperties = {
  display: 'block',
  fontSize: '13px',
  fontWeight: '600',
  color: '#4B5563',
  marginBottom: '6px',
}

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '8px 10px',
  fontSize: '14px',
  border: '1px solid #D1D5DB',
  borderRadius: '4px',
  fontFamily: 'inherit',
}

const textareaFieldStyle: React.CSSProperties = {
  width: '100%',
  padding: '8px 10px',
  fontSize: '14px',
  border: '1px solid #D1D5DB',
  borderRadius: '4px',
  fontFamily: 'inherit',
  resize: 'vertical',
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
