import { useState } from 'react'
import RunForm from './components/RunForm'
import StoryModeForm from './components/StoryModeForm'
import AdModeForm from './components/AdModeForm'
import RunStatus from './components/RunStatus'
import Player from './components/Player'
import LayoutTestTool from './components/LayoutTestTool'

type AppMode = 'general' | 'story' | 'ad' | 'test'

function App() {
  const [appMode, setAppMode] = useState<AppMode>('general')
  const [currentRunId, setCurrentRunId] = useState<string | null>(null)
  const [completedRun, setCompletedRun] = useState<any>(null)

  const handleRunCreated = (runId: string) => {
    setCurrentRunId(runId)
    setCompletedRun(null)
  }

  const handleRunCompleted = (runData: any) => {
    setCompletedRun(runData)
    setCurrentRunId(null)
  }

  const handleReset = () => {
    setCurrentRunId(null)
    setCompletedRun(null)
  }

  const renderModeButtons = () => (
    <div className="mode-selector">
      <button
        className={`mode-btn ${appMode === 'general' ? 'active' : ''}`}
        onClick={() => setAppMode('general')}
        disabled={!!currentRunId || !!completedRun}
      >
        일반 모드
      </button>
      <button
        className={`mode-btn ${appMode === 'story' ? 'active' : ''}`}
        onClick={() => setAppMode('story')}
        disabled={!!currentRunId || !!completedRun}
      >
        스토리 모드
      </button>
      <button
        className={`mode-btn ${appMode === 'ad' ? 'active' : ''}`}
        onClick={() => setAppMode('ad')}
        disabled={!!currentRunId || !!completedRun}
      >
        광고모드
      </button>
      <button
        className={`mode-btn ${appMode === 'test' ? 'active' : ''}`}
        onClick={() => setAppMode('test')}
        disabled={!!currentRunId || !!completedRun}
      >
        레이아웃 테스트
      </button>
    </div>
  )

  const renderInputForm = () => {
    switch (appMode) {
      case 'general':
        return <RunForm onRunCreated={handleRunCreated} />
      case 'story':
        return <StoryModeForm onRunCreated={handleRunCreated} />
      case 'ad':
        return <AdModeForm onRunCreated={handleRunCreated} />
      case 'test':
        return <LayoutTestTool />
    }
  }

  return (
    <div className="app">
      <header className="header">
        <h1>AutoShorts</h1>
        <p>스토리텔링형 숏츠 자동 제작 시스템</p>
      </header>

      <main className="main">
        {renderModeButtons()}

        {!currentRunId && !completedRun && renderInputForm()}

        {currentRunId && (
          <RunStatus
            runId={currentRunId}
            onCompleted={handleRunCompleted}
          />
        )}

        {completedRun && (
          <>
            <Player runData={completedRun} />
            <button onClick={handleReset} className="btn-reset">
              새로 만들기
            </button>
          </>
        )}
      </main>

      <footer className="footer">
        <p>Powered by FastAPI + Celery + ComfyUI + React</p>
      </footer>
    </div>
  )
}

export default App
