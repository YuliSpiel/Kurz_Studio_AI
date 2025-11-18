import { useEffect, useState } from 'react'
import { getRun } from '../api/client'
import PlotReviewModal from './PlotReviewModal'

interface RunStatusProps {
  runId: string
  onCompleted: (runData: any) => void
  reviewMode: boolean
}

export default function RunStatus({ runId, onCompleted, reviewMode }: RunStatusProps) {
  const [status, setStatus] = useState<any>(null)
  const [logs, setLogs] = useState<string[]>([])
  const [showPlotReview, setShowPlotReview] = useState(false)

  useEffect(() => {
    // Initial status fetch
    getRun(runId).then(setStatus)

    // WebSocket connection
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/ws/${runId}`
    const websocket = new WebSocket(wsUrl)

    websocket.onopen = () => {
      console.log('WebSocket connected')
    }

    websocket.onmessage = (event) => {
      const data = JSON.parse(event.data)

      if (data.type === 'initial_state') {
        setStatus(data)
        setLogs(data.logs || [])
      } else if (data.type === 'state_change') {
        setLogs((prev) => [...prev, data.message])
        // Refresh status
        getRun(runId).then(setStatus)
      } else if (data.type === 'progress') {
        // 진행도 업데이트 시 로그 메시지도 추가
        if (data.message) {
          setLogs((prev) => [...prev, data.message])
        }
        // 상태 업데이트 (진행도, state, artifacts 등)
        setStatus((prev: any) => ({
          ...prev,
          progress: data.progress ?? prev?.progress,
          state: data.state ?? prev?.state,
          artifacts: data.artifacts ?? prev?.artifacts,
        }))

        // PLOT_REVIEW 상태일 때 모달 표시 (review mode일 때만)
        if (data.state === 'PLOT_REVIEW' && reviewMode) {
          setShowPlotReview(true)
        }

        // END 상태일 때 모달을 표시하므로 onCompleted 호출 제거
        // (onCompleted를 호출하면 App.tsx가 Player 컴포넌트로 전환되어 팝업이 아닌 페이지에 영상이 표시됨)
      }
    }

    websocket.onerror = (error) => {
      console.error('WebSocket error:', error)
    }

    websocket.onclose = () => {
      console.log('WebSocket disconnected')
    }

    // Polling fallback
    const interval = setInterval(() => {
      getRun(runId).then((data) => {
        setStatus(data)

        // PLOT_REVIEW 상태 감지 (review mode일 때만)
        if (data.state === 'PLOT_REVIEW' && reviewMode) {
          setShowPlotReview(true)
        }

        // END 상태일 때 모달을 표시하므로 onCompleted 호출 제거
        // (onCompleted를 호출하면 App.tsx가 Player 컴포넌트로 전환되어 팝업이 아닌 페이지에 영상이 표시됨)
        if (data.state === 'END' || data.state === 'FAILED') {
          clearInterval(interval)
        }
      })
    }, 2000)

    return () => {
      clearInterval(interval)
      websocket.close()
    }
  }, [runId, onCompleted])

  if (!status) {
    return <div className="status-loading">로딩 중...</div>
  }

  const progressPercent = Math.round(status.progress * 100)

  // END 상태일 때 전체 화면 모달 표시 (영상 완성)
  if (status.state === 'END') {
    return (
      <div className="enhancement-modal-overlay">
        <div className="enhancement-modal-container">
          <div className="enhancement-modal-layout">
            {/* Left: Stepper - All 5 steps completed */}
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

                {/* Step 3: 영상 합성 (Completed) */}
                <div style={{ position: 'relative', display: 'flex', alignItems: 'flex-start', gap: '12px', paddingBottom: '24px' }}>
                  <div className="enhancement-step-icon" style={{ backgroundColor: '#7189a0', border: '2px solid #7189a0' }}>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="#FFFFFF">
                      <path d="M19.7071 6.29289C20.0976 6.68342 20.0976 7.31658 19.7071 7.70711L9.70711 17.7071C9.31658 18.0976 8.68342 18.0976 8.29289 17.7071L4.29289 13.7071C3.90237 13.3166 3.90237 12.6834 4.29289 12.2929C4.68342 11.9024 5.31658 11.9024 5.70711 12.2929L9 15.5858L18.2929 6.29289C18.6834 5.90237 19.3166 5.90237 19.7071 6.29289Z"/>
                    </svg>
                  </div>
                  <div style={{ flex: 1, paddingTop: '4px' }}>
                    <div style={{ fontSize: '15px', fontWeight: '600', color: '#6B7280', marginBottom: '4px' }}>
                      영상 합성
                    </div>
                    <div style={{ fontSize: '13px', color: '#9CA3AF', lineHeight: '1.4' }}>
                      완료됨
                    </div>
                  </div>
                  <div style={{ position: 'absolute', left: '21px', top: '44px', bottom: '0', width: '2px', backgroundColor: '#7189a0' }} />
                </div>

                {/* Step 4: 품질 검수 (Completed) */}
                <div style={{ position: 'relative', display: 'flex', alignItems: 'flex-start', gap: '12px', paddingBottom: '0px' }}>
                  <div className="enhancement-step-icon" style={{ backgroundColor: '#7189a0', border: '2px solid #7189a0' }}>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="#FFFFFF">
                      <path d="M19.7071 6.29289C20.0976 6.68342 20.0976 7.31658 19.7071 7.70711L9.70711 17.7071C9.31658 18.0976 8.68342 18.0976 8.29289 17.7071L4.29289 13.7071C3.90237 13.3166 3.90237 12.6834 4.29289 12.2929C4.68342 11.9024 5.31658 11.9024 5.70711 12.2929L9 15.5858L18.2929 6.29289C18.6834 5.90237 19.3166 5.90237 19.7071 6.29289Z"/>
                    </svg>
                  </div>
                  <div style={{ flex: 1, paddingTop: '4px' }}>
                    <div style={{ fontSize: '15px', fontWeight: '600', color: '#6B7280', marginBottom: '4px' }}>
                      품질 검수
                    </div>
                    <div style={{ fontSize: '13px', color: '#9CA3AF', lineHeight: '1.4' }}>
                      완료됨
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Right: Content - Video preview + download */}
            <div className="enhancement-content">
              <div className="enhancement-content-header">
                <h3 className="enhancement-modal-title">🎉 영상 생성 완료!</h3>
              </div>

              <div style={{
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                padding: '40px 20px'
              }}>
                <div style={{ fontSize: '64px', marginBottom: '24px' }}>🎉</div>
                <h3 style={{ fontSize: '20px', fontWeight: '700', color: '#111827', marginBottom: '12px' }}>
                  영상 생성이 완료되었습니다!
                </h3>
                <p style={{ fontSize: '15px', color: '#6B7280', marginBottom: '32px', textAlign: 'center' }}>
                  아래에서 영상을 미리보고 다운로드 할 수 있습니다
                </p>

                {/* Video Preview */}
                {status.artifacts?.video_url && (
                  <div style={{
                    width: '100%',
                    maxWidth: '500px',
                    marginBottom: '24px',
                    borderRadius: '12px',
                    overflow: 'hidden',
                    boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)'
                  }}>
                    <video
                      src={status.artifacts.video_url}
                      controls
                      style={{
                        width: '100%',
                        display: 'block',
                        backgroundColor: '#000'
                      }}
                    />
                  </div>
                )}

                {/* Download Button */}
                <a
                  href={status.artifacts?.video_url || `/outputs/${runId}/final_video.mp4`}
                  download={`${runId}.mp4`}
                  style={{ textDecoration: 'none' }}
                >
                  <button style={{
                    padding: '12px 24px',
                    backgroundColor: '#6f9fa0',
                    color: '#FFFFFF',
                    border: 'none',
                    borderRadius: '8px',
                    fontSize: '15px',
                    fontWeight: '600',
                    cursor: 'pointer',
                    transition: 'background-color 0.2s',
                    boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)'
                  }}
                  onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#5a8081'}
                  onMouseOut={(e) => e.currentTarget.style.backgroundColor = '#6f9fa0'}
                  >
                    📥 영상 다운로드
                  </button>
                </a>

                {/* Optional: Add "Create New Video" button */}
                <button
                  onClick={() => window.location.reload()}
                  style={{
                    marginTop: '16px',
                    padding: '10px 20px',
                    backgroundColor: 'transparent',
                    color: '#6B7280',
                    border: '1px solid #D1D5DB',
                    borderRadius: '8px',
                    fontSize: '14px',
                    fontWeight: '500',
                    cursor: 'pointer',
                    transition: 'all 0.2s'
                  }}
                  onMouseOver={(e) => {
                    e.currentTarget.style.backgroundColor = '#F3F4F6'
                    e.currentTarget.style.borderColor = '#9CA3AF'
                  }}
                  onMouseOut={(e) => {
                    e.currentTarget.style.backgroundColor = 'transparent'
                    e.currentTarget.style.borderColor = '#D1D5DB'
                  }}
                >
                  새 영상 만들기
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  // RENDERING 상태일 때 전체 화면 모달 표시
  if (status.state === 'RENDERING') {
    return (
      <div className="enhancement-modal-overlay">
        <div className="enhancement-modal-container">
          <div className="enhancement-modal-layout">
            {/* Left: Stepper */}
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

                {/* Step 3: 영상 합성 (Active) */}
                <div style={{ position: 'relative', display: 'flex', alignItems: 'flex-start', gap: '12px', paddingBottom: '24px' }}>
                  <div className="enhancement-step-icon" style={{ backgroundColor: '#6f9fa0', border: '2px solid #6f9fa0', boxShadow: '0 0 0 4px rgba(111, 159, 160, 0.1)' }}>
                    <div className="enhancement-step-spinner"></div>
                  </div>
                  <div style={{ flex: 1, paddingTop: '4px' }}>
                    <div style={{ fontSize: '15px', fontWeight: '700', color: '#111827', marginBottom: '4px' }}>
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
            </div>

            {/* Right: Content - 영상 합성 진행 상황 */}
            <div className="enhancement-content">
              <div className="enhancement-content-header">
                <h3 className="enhancement-modal-title">🎬 영상 합성 중...</h3>
              </div>

              {/* TODO: 나중에 애니메이션으로 교체 */}
              <div style={{
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                padding: '40px 20px'
              }}>
                <div style={{ fontSize: '64px', marginBottom: '24px' }}>🎬</div>
                <h3 style={{ fontSize: '20px', fontWeight: '700', color: '#111827', marginBottom: '12px' }}>
                  영상을 합성하고 있습니다
                </h3>
                <p style={{ fontSize: '15px', color: '#6B7280', marginBottom: '32px', textAlign: 'center' }}>
                  감독이 이미지, 음성, 음악을 하나의 영상으로 합성하고 있습니다
                </p>

                {/* Progress info */}
                <div style={{
                  width: '100%',
                  maxWidth: '500px',
                  backgroundColor: '#F9FAFB',
                  borderRadius: '8px',
                  padding: '20px',
                  marginBottom: '24px'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px' }}>
                    <span style={{ fontSize: '14px', fontWeight: '600', color: '#4B5563' }}>전체 진행률</span>
                    <span style={{ fontSize: '14px', fontWeight: '700', color: '#6f9fa0' }}>{progressPercent}%</span>
                  </div>
                  <div style={{
                    width: '100%',
                    height: '8px',
                    backgroundColor: '#E5E7EB',
                    borderRadius: '4px',
                    overflow: 'hidden'
                  }}>
                    <div style={{
                      width: `${progressPercent}%`,
                      height: '100%',
                      backgroundColor: '#6f9fa0',
                      transition: 'width 0.3s ease'
                    }} />
                  </div>
                </div>

                {/* Logs */}
                {logs.length > 0 && (
                  <div style={{
                    width: '100%',
                    maxWidth: '500px',
                    backgroundColor: '#FFFFFF',
                    border: '1px solid #E5E7EB',
                    borderRadius: '8px',
                    padding: '16px',
                    maxHeight: '200px',
                    overflowY: 'auto'
                  }}>
                    <h4 style={{ fontSize: '14px', fontWeight: '600', color: '#4B5563', marginBottom: '12px' }}>
                      최근 로그
                    </h4>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      {[...logs].reverse().slice(0, 5).map((log, idx) => (
                        <div key={idx} style={{
                          fontSize: '13px',
                          color: '#6B7280',
                          paddingLeft: '12px',
                          borderLeft: '2px solid #E5E7EB'
                        }}>
                          {log}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  // QA 상태일 때 전체 화면 모달 표시
  if (status.state === 'QA') {
    return (
      <div className="enhancement-modal-overlay">
        <div className="enhancement-modal-container">
          <div className="enhancement-modal-layout">
            {/* Left: Stepper */}
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

                {/* Step 3: 영상 합성 (Completed) */}
                <div style={{ position: 'relative', display: 'flex', alignItems: 'flex-start', gap: '12px', paddingBottom: '24px' }}>
                  <div className="enhancement-step-icon" style={{ backgroundColor: '#7189a0', border: '2px solid #7189a0' }}>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="#FFFFFF">
                      <path d="M19.7071 6.29289C20.0976 6.68342 20.0976 7.31658 19.7071 7.70711L9.70711 17.7071C9.31658 18.0976 8.68342 18.0976 8.29289 17.7071L4.29289 13.7071C3.90237 13.3166 3.90237 12.6834 4.29289 12.2929C4.68342 11.9024 5.31658 11.9024 5.70711 12.2929L9 15.5858L18.2929 6.29289C18.6834 5.90237 19.3166 5.90237 19.7071 6.29289Z"/>
                    </svg>
                  </div>
                  <div style={{ flex: 1, paddingTop: '4px' }}>
                    <div style={{ fontSize: '15px', fontWeight: '600', color: '#6B7280', marginBottom: '4px' }}>
                      영상 합성
                    </div>
                    <div style={{ fontSize: '13px', color: '#9CA3AF', lineHeight: '1.4' }}>
                      완료됨
                    </div>
                  </div>
                  <div style={{ position: 'absolute', left: '21px', top: '44px', bottom: '0', width: '2px', backgroundColor: '#7189a0' }} />
                </div>

                {/* Step 4: 품질 검수 (Active) */}
                <div style={{ position: 'relative', display: 'flex', alignItems: 'flex-start', gap: '12px', paddingBottom: '0px' }}>
                  <div className="enhancement-step-icon" style={{ backgroundColor: '#6f9fa0', border: '2px solid #6f9fa0', boxShadow: '0 0 0 4px rgba(111, 159, 160, 0.1)' }}>
                    <div className="enhancement-step-spinner"></div>
                  </div>
                  <div style={{ flex: 1, paddingTop: '4px' }}>
                    <div style={{ fontSize: '15px', fontWeight: '700', color: '#111827', marginBottom: '4px' }}>
                      품질 검수
                    </div>
                    <div style={{ fontSize: '13px', color: '#9CA3AF', lineHeight: '1.4' }}>
                      최종 품질을 검수합니다
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Right: Content - 품질 검수 진행 상황 */}
            <div className="enhancement-content">
              <div className="enhancement-content-header">
                <h3 className="enhancement-modal-title">✅ 품질 검수 중...</h3>
              </div>

              {/* TODO: 나중에 애니메이션으로 교체 */}
              <div style={{
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                padding: '40px 20px'
              }}>
                <div style={{ fontSize: '64px', marginBottom: '24px' }}>✅</div>
                <h3 style={{ fontSize: '20px', fontWeight: '700', color: '#111827', marginBottom: '12px' }}>
                  품질을 검수하고 있습니다
                </h3>
                <p style={{ fontSize: '15px', color: '#6B7280', marginBottom: '32px', textAlign: 'center' }}>
                  QA 담당자가 영상 품질을 검사하고 최종 승인하고 있습니다
                </p>

                {/* Progress info */}
                <div style={{
                  width: '100%',
                  maxWidth: '500px',
                  backgroundColor: '#F9FAFB',
                  borderRadius: '8px',
                  padding: '20px',
                  marginBottom: '24px'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px' }}>
                    <span style={{ fontSize: '14px', fontWeight: '600', color: '#4B5563' }}>전체 진행률</span>
                    <span style={{ fontSize: '14px', fontWeight: '700', color: '#6f9fa0' }}>{progressPercent}%</span>
                  </div>
                  <div style={{
                    width: '100%',
                    height: '8px',
                    backgroundColor: '#E5E7EB',
                    borderRadius: '4px',
                    overflow: 'hidden'
                  }}>
                    <div style={{
                      width: `${progressPercent}%`,
                      height: '100%',
                      backgroundColor: '#6f9fa0',
                      transition: 'width 0.3s ease'
                    }} />
                  </div>
                </div>

                {/* Logs */}
                {logs.length > 0 && (
                  <div style={{
                    width: '100%',
                    maxWidth: '500px',
                    backgroundColor: '#FFFFFF',
                    border: '1px solid #E5E7EB',
                    borderRadius: '8px',
                    padding: '16px',
                    maxHeight: '200px',
                    overflowY: 'auto'
                  }}>
                    <h4 style={{ fontSize: '14px', fontWeight: '600', color: '#4B5563', marginBottom: '12px' }}>
                      최근 로그
                    </h4>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      {[...logs].reverse().slice(0, 5).map((log, idx) => (
                        <div key={idx} style={{
                          fontSize: '13px',
                          color: '#6B7280',
                          paddingLeft: '12px',
                          borderLeft: '2px solid #E5E7EB'
                        }}>
                          {log}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  // ASSET_GENERATION 상태일 때 전체 화면 모달 표시
  if (status.state === 'ASSET_GENERATION') {
    return (
      <div className="enhancement-modal-overlay">
        <div className="enhancement-modal-container">
          <div className="enhancement-modal-layout">
            {/* Left: Stepper */}
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

                {/* Step 2: 에셋 생성 (Active) */}
                <div style={{ position: 'relative', display: 'flex', alignItems: 'flex-start', gap: '12px', paddingBottom: '24px' }}>
                  <div className="enhancement-step-icon" style={{ backgroundColor: '#6f9fa0', border: '2px solid #6f9fa0', boxShadow: '0 0 0 4px rgba(111, 159, 160, 0.1)' }}>
                    <div className="enhancement-step-spinner"></div>
                  </div>
                  <div style={{ flex: 1, paddingTop: '4px' }}>
                    <div style={{ fontSize: '15px', fontWeight: '700', color: '#111827', marginBottom: '4px' }}>
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
            </div>

            {/* Right: Content - 에셋 생성 진행 상황 */}
            <div className="enhancement-content">
              <div className="enhancement-content-header">
                <h3 className="enhancement-modal-title">🎨 에셋 생성 중...</h3>
              </div>

              {/* TODO: 나중에 애니메이션으로 교체 */}
              <div style={{
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                padding: '40px 20px'
              }}>
                <div style={{ fontSize: '64px', marginBottom: '24px' }}>🎨</div>
                <h3 style={{ fontSize: '20px', fontWeight: '700', color: '#111827', marginBottom: '12px' }}>
                  에셋을 생성하고 있습니다
                </h3>
                <p style={{ fontSize: '15px', color: '#6B7280', marginBottom: '32px', textAlign: 'center' }}>
                  디자이너가 이미지를 그리고, 작곡가가 음악을 만들고, 성우가 대사를 녹음하고 있습니다
                </p>

                {/* Progress info */}
                <div style={{
                  width: '100%',
                  maxWidth: '500px',
                  backgroundColor: '#F9FAFB',
                  borderRadius: '8px',
                  padding: '20px',
                  marginBottom: '24px'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px' }}>
                    <span style={{ fontSize: '14px', fontWeight: '600', color: '#4B5563' }}>전체 진행률</span>
                    <span style={{ fontSize: '14px', fontWeight: '700', color: '#6f9fa0' }}>{progressPercent}%</span>
                  </div>
                  <div style={{
                    width: '100%',
                    height: '8px',
                    backgroundColor: '#E5E7EB',
                    borderRadius: '4px',
                    overflow: 'hidden'
                  }}>
                    <div style={{
                      width: `${progressPercent}%`,
                      height: '100%',
                      backgroundColor: '#6f9fa0',
                      transition: 'width 0.3s ease'
                    }} />
                  </div>
                </div>

                {/* Logs */}
                {logs.length > 0 && (
                  <div style={{
                    width: '100%',
                    maxWidth: '500px',
                    backgroundColor: '#FFFFFF',
                    border: '1px solid #E5E7EB',
                    borderRadius: '8px',
                    padding: '16px',
                    maxHeight: '200px',
                    overflowY: 'auto'
                  }}>
                    <h4 style={{ fontSize: '14px', fontWeight: '600', color: '#4B5563', marginBottom: '12px' }}>
                      최근 로그
                    </h4>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      {[...logs].reverse().slice(0, 5).map((log, idx) => (
                        <div key={idx} style={{
                          fontSize: '13px',
                          color: '#6B7280',
                          paddingLeft: '12px',
                          borderLeft: '2px solid #E5E7EB'
                        }}>
                          {log}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <>
      <div className="run-status">
        <h2>생성 진행 중...</h2>

        <div className="status-card">
          <div className="status-row">
            <span className="label">Run ID:</span>
            <span className="value">{runId}</span>
          </div>

          <div className="status-row">
            <span className="label">상태:</span>
            <span className={`value state-${status.state.toLowerCase()}`}>
              {status.state}
            </span>
          </div>

          <div className="status-row">
            <span className="label">진행률:</span>
            <span className="value">{progressPercent}%</span>
          </div>

          <div className="progress-bar">
            <div
              className="progress-fill"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>

        {logs.length > 0 && (
          <div className="logs">
            <h3>로그 (최신순)</h3>
            <div className="logs-content">
              {[...logs].reverse().map((log, idx) => (
                <div key={idx} className="log-entry">
                  {log}
                </div>
              ))}
            </div>
          </div>
        )}

        {status.state === 'FAILED' && (
          <div className="error-message">
            생성 실패. 로그를 확인하세요.
          </div>
        )}

        {reviewMode && status.state === 'PLOT_REVIEW' && !showPlotReview && (
          <div style={{
            marginTop: '20px',
            padding: '15px',
            backgroundColor: '#FEF3C7',
            borderRadius: '8px',
            border: '2px solid #F59E0B',
          }}>
            <p style={{ margin: 0, fontWeight: 'bold', color: '#92400E' }}>
              📋 플롯 검수 대기 중...
            </p>
            <p style={{ margin: '8px 0 0 0', fontSize: '14px', color: '#78350F' }}>
              플롯이 생성되었습니다. 잠시 후 검수 모달이 표시됩니다.
            </p>
          </div>
        )}
      </div>

      {/* Plot Review Modal */}
      {reviewMode && showPlotReview && status.state === 'PLOT_REVIEW' && (
        <PlotReviewModal
          runId={runId}
          onClose={() => setShowPlotReview(false)}
          onConfirmed={() => {
            setShowPlotReview(false)
            // Refresh status after confirmation
            getRun(runId).then(setStatus)
          }}
        />
      )}
    </>
  )
}
