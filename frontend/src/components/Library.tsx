import { useState, useEffect, useRef } from 'react'
import { getMyRuns, deleteRun, RunListItem } from '../api/client'
import './Library.css'

export default function Library({ onSelectVideo: _onSelectVideo }: { onSelectVideo?: (runId: string) => void }) {
  const [runs, setRuns] = useState<RunListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [deletingRunId, setDeletingRunId] = useState<string | null>(null)
  const [selectedVideo, setSelectedVideo] = useState<RunListItem | null>(null)
  const [hoveredRunId, setHoveredRunId] = useState<string | null>(null)
  const [videoDurations, setVideoDurations] = useState<Record<string, number>>({})
  const [videoCurrentTimes, setVideoCurrentTimes] = useState<Record<string, number>>({})
  const videoRefs = useRef<Record<string, HTMLVideoElement | null>>({})

  useEffect(() => {
    loadRuns()
  }, [])

  const loadRuns = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await getMyRuns()
      setRuns(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load videos')
      console.error('Failed to load runs:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (runId: string, event: React.MouseEvent) => {
    event.stopPropagation()

    if (!confirm('이 영상을 삭제하시겠습니까? 삭제된 영상은 복구할 수 없습니다.')) {
      return
    }

    try {
      setDeletingRunId(runId)
      await deleteRun(runId)
      setRuns(prev => prev.filter(run => run.run_id !== runId))
      console.log(`Deleted run: ${runId}`)
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete video')
      console.error('Failed to delete run:', err)
    } finally {
      setDeletingRunId(null)
    }
  }

  const handleFavorite = (event: React.MouseEvent) => {
    event.stopPropagation()
    // TODO: Implement favorite functionality
    alert('즐겨찾기 기능은 곧 추가됩니다')
  }

  const handleShare = (event: React.MouseEvent) => {
    event.stopPropagation()
    // TODO: Implement share functionality
    alert('공유 기능은 곧 추가됩니다')
  }

  const handleVideoClick = (run: RunListItem) => {
    if (run.state === 'COMPLETED' && run.video_url) {
      setSelectedVideo(run)
    }
  }

  const closeVideoPopup = () => {
    setSelectedVideo(null)
  }

  const handleLoadedMetadata = (runId: string, event: React.SyntheticEvent<HTMLVideoElement>) => {
    const duration = event.currentTarget.duration
    if (duration && !isNaN(duration)) {
      setVideoDurations(prev => ({ ...prev, [runId]: duration }))
    }
  }

  const handleTimeUpdate = (runId: string, event: React.SyntheticEvent<HTMLVideoElement>) => {
    const currentTime = event.currentTarget.currentTime
    setVideoCurrentTimes(prev => ({ ...prev, [runId]: currentTime }))
  }

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const getRemainingTime = (runId: string) => {
    const duration = videoDurations[runId] || 0
    const currentTime = videoCurrentTimes[runId] || 0
    return Math.max(0, duration - currentTime)
  }

  const getStateColor = (state: string) => {
    switch (state) {
      case 'COMPLETED':
        return '#10b981' // green
      case 'FAILED':
        return '#ef4444' // red
      case 'IDLE':
      case 'PLOT_GENERATION':
      case 'PLOT_REVIEW':
      case 'ASSET_GENERATION':
      case 'LAYOUT_REVIEW':
      case 'RENDERING':
      case 'QA':
        return '#f59e0b' // orange (in progress)
      default:
        return '#6b7280' // gray
    }
  }

  const getStateText = (state: string) => {
    const stateMap: Record<string, string> = {
      'IDLE': '대기중',
      'PLOT_GENERATION': '시나리오 생성중',
      'PLOT_REVIEW': '시나리오 검토',
      'ASSET_GENERATION': '에셋 생성중',
      'LAYOUT_REVIEW': '레이아웃 검토',
      'RENDERING': '영상 합성중',
      'QA': '품질 검수중',
      'COMPLETED': '완료',
      'FAILED': '실패',
    }
    return stateMap[state] || state
  }

  if (loading) {
    return (
      <div className="library-container">
        <div className="library-loading">영상 로딩중...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="library-container">
        <div className="library-error">
          <p>{error}</p>
          <button onClick={loadRuns} className="retry-btn">다시 시도</button>
        </div>
      </div>
    )
  }

  if (runs.length === 0) {
    return (
      <div className="library-container">
        <div className="library-empty">
          <h2>아직 만든 영상이 없어요</h2>
          <p>첫 번째 영상을 만들어보세요!</p>
        </div>
      </div>
    )
  }

  return (
    <div className="library-container">
      <div className="library-header">
        <h1>내 영상 라이브러리</h1>
        <p className="library-count">총 {runs.length}개의 영상</p>
      </div>

      <div className="library-grid">
        {runs.map((run) => (
          <div
            key={run.id}
            className="library-item"
            onClick={() => handleVideoClick(run)}
            onMouseEnter={() => setHoveredRunId(run.run_id)}
            onMouseLeave={() => setHoveredRunId(null)}
            style={{ cursor: run.state === 'COMPLETED' ? 'pointer' : 'default' }}
          >
            {/* 9:16 Thumbnail */}
            <div className="library-thumbnail">
              {run.video_url && run.state === 'COMPLETED' ? (
                <>
                  <video
                    ref={(el) => { videoRefs.current[run.run_id] = el }}
                    src={run.video_url}
                    className="thumbnail-video"
                    muted
                    playsInline
                    preload="metadata"
                    onLoadedMetadata={(e) => handleLoadedMetadata(run.run_id, e)}
                    onTimeUpdate={(e) => handleTimeUpdate(run.run_id, e)}
                    onMouseEnter={(e) => {
                      e.currentTarget.play()
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.pause()
                      e.currentTarget.currentTime = 0
                    }}
                    poster={run.thumbnail_url || undefined}
                  />

                  {/* Remaining Time Badge (shown on hover) */}
                  {hoveredRunId === run.run_id && videoDurations[run.run_id] && (
                    <div className="duration-badge">
                      {formatDuration(getRemainingTime(run.run_id))}
                    </div>
                  )}
                </>
              ) : (
                <div className="thumbnail-placeholder">
                  <div className="placeholder-icon">🎬</div>
                  <div className="placeholder-text">{getStateText(run.state)}</div>
                </div>
              )}

              {/* State Badge */}
              <div
                className="state-badge"
                style={{ backgroundColor: getStateColor(run.state) }}
              >
                {getStateText(run.state)}
              </div>

              {/* Progress Bar */}
              {run.state !== 'COMPLETED' && run.state !== 'FAILED' && (
                <div className="progress-bar-container">
                  <div
                    className="progress-bar-fill"
                    style={{ width: `${run.progress}%` }}
                  />
                </div>
              )}
            </div>

            {/* Action Buttons */}
            <div className="library-actions">
              <button
                className="action-btn favorite-btn"
                onClick={handleFavorite}
                title="즐겨찾기"
              >
                ⭐
              </button>
              <button
                className="action-btn share-btn"
                onClick={handleShare}
                title="공유"
              >
                ✈️
              </button>
              <button
                className="action-btn delete-btn"
                onClick={(e) => handleDelete(run.run_id, e)}
                disabled={deletingRunId === run.run_id}
                title="삭제"
              >
                {deletingRunId === run.run_id ? '⏳' : '🗑️'}
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Video Player Popup */}
      {selectedVideo && (
        <div className="video-popup-overlay" onClick={closeVideoPopup}>
          <div className="video-popup-container" onClick={(e) => e.stopPropagation()}>
            {/* Close Button */}
            <button className="popup-close-btn" onClick={closeVideoPopup}>
              ✕
            </button>

            {/* Video Player */}
            <div className="popup-video-wrapper">
              <video
                src={selectedVideo.video_url || ''}
                className="popup-video"
                controls
                autoPlay
                playsInline
              />
            </div>

            {/* Action Buttons */}
            <div className="popup-actions">
              <button className="popup-action-btn favorite-btn" onClick={handleFavorite}>
                ⭐ 즐겨찾기
              </button>
              <button className="popup-action-btn share-btn" onClick={handleShare}>
                ✈️ 공유
              </button>
              <button
                className="popup-action-btn delete-btn"
                onClick={(e) => {
                  handleDelete(selectedVideo.run_id, e)
                  closeVideoPopup()
                }}
                disabled={deletingRunId === selectedVideo.run_id}
              >
                {deletingRunId === selectedVideo.run_id ? '⏳ 삭제중...' : '🗑️ 삭제'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
