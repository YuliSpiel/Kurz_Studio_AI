import { useState } from 'react'
import HeroChat from './components/HeroChat'
import RunForm from './components/RunForm'
import StoryModeForm from './components/StoryModeForm'
import AdModeForm from './components/AdModeForm'
import RunStatus from './components/RunStatus'
import Player from './components/Player'
import AuthModal from './components/AuthModal'
import Library from './components/Library'
import UserMenu from './components/UserMenu'
import VideoSettingsModal from './components/VideoSettingsModal'
import { PromptEnhancementResult } from './api/client'
import { useAuth } from './contexts/AuthContext'

type AppMode = 'general' | 'story' | 'ad'
type ViewMode = 'home' | 'library'

function App() {
  const { user } = useAuth()
  const [viewMode, setViewMode] = useState<ViewMode>('home')
  const [appMode, setAppMode] = useState<AppMode>('general')
  const [currentRunId, setCurrentRunId] = useState<string | null>(null)
  const [completedRun, setCompletedRun] = useState<any>(null)
  const [showDetailedForm, setShowDetailedForm] = useState(false)
  const [showAuthModal, setShowAuthModal] = useState(false)
  const [authModalMode, setAuthModalMode] = useState<'login' | 'register'>('login')

  // Enhancement data from HeroChat
  const [enhancementData, setEnhancementData] = useState<{
    enhancement: PromptEnhancementResult
    originalPrompt: string
  } | null>(null)

  // Review mode flag
  const [isReviewMode, setIsReviewMode] = useState(false)

  // Modal visibility state
  const [isRunStatusMinimized, setIsRunStatusMinimized] = useState(false)
  const [showVideoSettings, setShowVideoSettings] = useState(false)

  const handleRunCreated = (runId: string, reviewMode: boolean = false, minimized: boolean = false) => {
    console.log('[App] handleRunCreated called:', { runId, reviewMode, minimized })
    setCurrentRunId(runId)
    setCompletedRun(null)
    setIsReviewMode(reviewMode)
    // Only set to false if not minimized - allows HeroChat to pass minimized=true
    setIsRunStatusMinimized(minimized)
    console.log('[App] After setState - minimized should be:', minimized)
  }

  const handleRunCompleted = (runData: any) => {
    setCompletedRun(runData)
    setCurrentRunId(null)
    setIsRunStatusMinimized(false)
  }

  const handleReset = () => {
    setCurrentRunId(null)
    setCompletedRun(null)
    setShowDetailedForm(false)
    setEnhancementData(null)
    setIsReviewMode(false)
    setViewMode('home')
  }

  const handleEditorMode = () => {
    setShowDetailedForm(true)
    setAppMode('general')
    setEnhancementData(null)
    setViewMode('home')
  }

  const handleLibraryClick = () => {
    if (!user) {
      setAuthModalMode('login')
      setShowAuthModal(true)
      return
    }
    setViewMode('library')
  }

  const handleHeroChatSubmit = (_prompt: string, mode: 'general' | 'story' | 'ad') => {
    setAppMode(mode)
    setShowDetailedForm(true)
  }

  const handleEnhancementReady = (enhancement: PromptEnhancementResult, originalPrompt: string) => {
    setEnhancementData({ enhancement, originalPrompt })
    setAppMode('general')
    setShowDetailedForm(true)
  }

  const handleAuthRequired = () => {
    setAuthModalMode('login')
    setShowAuthModal(true)
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
        return <RunForm onRunCreated={handleRunCreated} onAuthRequired={handleAuthRequired} enhancementData={enhancementData} />
      case 'story':
        return <StoryModeForm onRunCreated={handleRunCreated} onAuthRequired={handleAuthRequired} />
      case 'ad':
        return <AdModeForm onRunCreated={handleRunCreated} onAuthRequired={handleAuthRequired} />
    }
  }

  return (
    <>
      <nav className="navbar">
        <div className="navbar-content">
          <div className="navbar-left">
            <div className="navbar-logo" onClick={handleReset} style={{ cursor: 'pointer', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.0001px' }}>
                <img src="/logo/kurz_logo.png" alt="Kurz Logo" style={{ height: '2.7rem', width: 'auto' }} />
                <h1>KURZ AI</h1>
              </div>
              <p style={{ textAlign: 'center', marginLeft: '5px' }}>가장 쉬운 숏폼 제작 플랫폼</p>
            </div>
            <div className="navbar-menu">
              <a href="#" onClick={(e) => { e.preventDefault(); handleEditorMode(); }} className="navbar-menu-item">에디터 모드</a>
              <a href="#" onClick={(e) => { e.preventDefault(); handleLibraryClick(); }} className="navbar-menu-item">라이브러리</a>
              <a href="#" className="navbar-menu-item">캘린더</a>
              <a href="#" className="navbar-menu-item">커뮤니티</a>
            </div>
          </div>
          <div className="navbar-right">
            <UserMenu
              onOpenAuthModal={(mode) => {
                setAuthModalMode(mode)
                setShowAuthModal(true)
              }}
              onOpenVideoSettings={() => setShowVideoSettings(true)}
            />
          </div>
        </div>
      </nav>

      <div className="app">
        {viewMode === 'library' ? (
          <Library onSelectVideo={(runId) => {
            setCurrentRunId(runId)
            setIsRunStatusMinimized(false) // Open the modal when selecting from library
            setViewMode('home')
          }} />
        ) : (
          <>
            {!currentRunId && !completedRun && !showDetailedForm && (
              <HeroChat
                onSubmit={handleHeroChatSubmit}
                onEnhancementReady={handleEnhancementReady}
                onRunCreated={handleRunCreated}
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

                {currentRunId && !isRunStatusMinimized && (
                  <RunStatus
                    runId={currentRunId}
                    onCompleted={handleRunCompleted}
                    reviewMode={isReviewMode}
                    onMinimize={() => setIsRunStatusMinimized(true)}
                    onClose={() => setCurrentRunId(null)}
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
          </>
        )}
      </div>

      {/* Auth Modal */}
      <AuthModal
        isOpen={showAuthModal}
        onClose={() => setShowAuthModal(false)}
        initialMode={authModalMode}
      />

      {/* Video Settings Modal */}
      <VideoSettingsModal
        isOpen={showVideoSettings}
        onClose={() => setShowVideoSettings(false)}
      />

      {/* Minimized Tab - Always rendered outside of main for visibility */}
      {console.log('[App] Minimized tab check:', { currentRunId, isRunStatusMinimized, viewMode })}
      {currentRunId && isRunStatusMinimized && viewMode === 'home' && (
        <div
          onClick={() => setIsRunStatusMinimized(false)}
          style={{
            position: 'fixed',
            bottom: '20px',
            right: '20px',
            padding: '12px 20px',
            backgroundColor: '#7189a0',
            color: '#FFFFFF',
            borderRadius: '8px',
            cursor: 'pointer',
            boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            fontSize: '14px',
            fontWeight: '600',
            zIndex: 1000,
            transition: 'all 0.2s',
          }}
          onMouseOver={(e) => {
            e.currentTarget.style.backgroundColor = '#6f9fa0'
            e.currentTarget.style.transform = 'translateY(-2px)'
            e.currentTarget.style.boxShadow = '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)'
          }}
          onMouseOut={(e) => {
            e.currentTarget.style.backgroundColor = '#7189a0'
            e.currentTarget.style.transform = 'translateY(0)'
            e.currentTarget.style.boxShadow = '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)'
          }}
        >
          <span style={{
            width: '8px',
            height: '8px',
            backgroundColor: '#10B981',
            borderRadius: '50%',
            animation: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite'
          }} />
          영상 제작 중...
        </div>
      )}
    </>
  )
}

export default App
