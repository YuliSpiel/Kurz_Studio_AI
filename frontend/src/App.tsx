import { useState } from 'react'
import HeroChat from './components/HeroChat'
import RunForm from './components/RunForm'
import StoryModeForm from './components/StoryModeForm'
import AdModeForm from './components/AdModeForm'
import RunStatus from './components/RunStatus'
import Player from './components/Player'

type AppMode = 'general' | 'story' | 'ad'

function App() {
  const [appMode, setAppMode] = useState<AppMode>('general')
  const [currentRunId, setCurrentRunId] = useState<string | null>(null)
  const [completedRun, setCompletedRun] = useState<any>(null)
  const [showDetailedForm, setShowDetailedForm] = useState(false)

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
    setShowDetailedForm(false)
  }

  const handleHeroChatSubmit = (prompt: string, mode: 'general' | 'story' | 'ad') => {
    setAppMode(mode)
    setShowDetailedForm(true)
    // TODO: 간단한 프롬프트로 바로 실행하거나, 상세 폼으로 이동
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
    }
  }

  return (
    <>
      <nav className="navbar">
        <div className="navbar-content">
          <div className="navbar-left">
            <div className="navbar-logo" onClick={handleReset} style={{ cursor: 'pointer' }}>
              <h1>KURZ AI</h1>
              <p>가장 쉬운 숏폼 제작 플랫폼</p>
            </div>
            <div className="navbar-menu">
              <a href="#" className="navbar-menu-item">라이브러리</a>
              <a href="#" className="navbar-menu-item">캘린더</a>
              <a href="#" className="navbar-menu-item">커뮤니티</a>
            </div>
          </div>
          <div className="navbar-right">
            <a href="#" className="navbar-menu-item">마이페이지</a>
          </div>
        </div>
      </nav>

      <div className="app">
        {!currentRunId && !completedRun && !showDetailedForm && (
          <HeroChat
            onSubmit={handleHeroChatSubmit}
            disabled={!!currentRunId || !!completedRun}
          />
        )}

        {(showDetailedForm || currentRunId || completedRun) && (
          <main className="main">
            {showDetailedForm && !currentRunId && !completedRun && (
              <>
                {renderModeButtons()}
                {renderInputForm()}
              </>
            )}

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
        )}
      </div>
    </>
  )
}

export default App
