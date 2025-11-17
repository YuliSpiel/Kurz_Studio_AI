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
        <div style={headerStyle}>
          <h2>📋 플롯 검수</h2>
          <button onClick={onClose} style={closeButtonStyle}>✕</button>
        </div>

        <div style={contentStyle}>
          <div style={infoBoxStyle}>
            <p><strong>Run ID:</strong> {runId}</p>
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
              backgroundColor: isRegenerating ? '#9CA3AF' : '#EF4444',
            }}
          >
            {isRegenerating ? '재생성 중...' : '🔄 다시 만들기'}
          </button>
          <div style={{ display: 'flex', gap: '10px' }}>
            <button
              onClick={onClose}
              style={{
                ...buttonStyle,
                backgroundColor: '#6B7280',
              }}
            >
              취소
            </button>
            <button
              onClick={handleConfirm}
              disabled={isConfirming || isRegenerating}
              style={{
                ...buttonStyle,
                backgroundColor: isConfirming ? '#9CA3AF' : '#10B981',
              }}
            >
              {isConfirming ? '확정 중...' : '✓ 확정'}
            </button>
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
  backgroundColor: 'rgba(0, 0, 0, 0.75)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  zIndex: 2000,
}

const modalStyle: React.CSSProperties = {
  backgroundColor: 'white',
  borderRadius: '12px',
  width: '90%',
  maxWidth: '900px',
  maxHeight: '90vh',
  display: 'flex',
  flexDirection: 'column',
  boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
}

const headerStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  padding: '20px 30px',
  borderBottom: '1px solid #E5E7EB',
}

const closeButtonStyle: React.CSSProperties = {
  background: 'none',
  border: 'none',
  fontSize: '24px',
  cursor: 'pointer',
  color: '#6B7280',
  padding: '0',
  width: '30px',
  height: '30px',
}

const contentStyle: React.CSSProperties = {
  padding: '20px 30px',
  overflowY: 'auto',
  flex: 1,
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
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  padding: '20px 30px',
  borderTop: '1px solid #E5E7EB',
}

const buttonStyle: React.CSSProperties = {
  padding: '10px 20px',
  border: 'none',
  borderRadius: '6px',
  fontSize: '14px',
  fontWeight: '600',
  color: 'white',
  cursor: 'pointer',
  transition: 'opacity 0.2s',
}
