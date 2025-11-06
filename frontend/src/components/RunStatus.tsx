import { useEffect, useState } from 'react'
import { getRun } from '../api/client'

interface RunStatusProps {
  runId: string
  onCompleted: (runData: any) => void
}

export default function RunStatus({ runId, onCompleted }: RunStatusProps) {
  const [status, setStatus] = useState<any>(null)
  const [logs, setLogs] = useState<string[]>([])
  const [ws, setWs] = useState<WebSocket | null>(null)

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

        // END 상태일 때 완료 콜백 호출
        if (data.state === 'END') {
          onCompleted({
            ...status,
            state: data.state,
            progress: data.progress,
            artifacts: data.artifacts,
          })
        }
      }
    }

    websocket.onerror = (error) => {
      console.error('WebSocket error:', error)
    }

    websocket.onclose = () => {
      console.log('WebSocket disconnected')
    }

    setWs(websocket)

    // Polling fallback
    const interval = setInterval(() => {
      getRun(runId).then((data) => {
        setStatus(data)
        if (data.state === 'END') {
          clearInterval(interval)
          onCompleted(data)
        } else if (data.state === 'FAILED') {
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

  return (
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
          <h3>로그</h3>
          <div className="logs-content">
            {logs.map((log, idx) => (
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
    </div>
  )
}
