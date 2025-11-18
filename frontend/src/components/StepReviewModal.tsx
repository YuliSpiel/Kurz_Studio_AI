import { useState } from 'react'

interface StepReviewModalProps {
  runId: string
  currentStep: 'PLOT_GENERATION' | 'ASSET_GENERATION' | 'VIDEO_COMPOSITION' | 'QA'
  onApprove: () => void
  onReject: () => void
  onClose: () => void
  children: React.ReactNode
}

const STEP_INFO = {
  PLOT_GENERATION: {
    label: '기획단계',
    icon: '📋',
    description: '시나리오와 플롯을 검토합니다'
  },
  ASSET_GENERATION: {
    label: '에셋생성',
    icon: '🎨',
    description: '이미지, 음악, 음성을 검토합니다'
  },
  VIDEO_COMPOSITION: {
    label: '감독',
    icon: '🎬',
    description: '영상 합성을 검토합니다'
  },
  QA: {
    label: 'QA',
    icon: '✅',
    description: '최종 품질을 검토합니다'
  }
}

const STEP_ORDER: Array<keyof typeof STEP_INFO> = [
  'PLOT_GENERATION',
  'ASSET_GENERATION',
  'VIDEO_COMPOSITION',
  'QA'
]

export default function StepReviewModal({
  runId,
  currentStep,
  onApprove,
  onReject,
  onClose,
  children
}: StepReviewModalProps) {
  const [isProcessing, setIsProcessing] = useState(false)

  const handleApprove = async () => {
    setIsProcessing(true)
    try {
      await onApprove()
    } finally {
      setIsProcessing(false)
    }
  }

  const handleReject = async () => {
    if (!confirm('이 단계를 거부하고 재생성하시겠습니까?')) {
      return
    }
    setIsProcessing(true)
    try {
      await onReject()
    } finally {
      setIsProcessing(false)
    }
  }

  const currentStepIndex = STEP_ORDER.indexOf(currentStep)

  return (
    <div style={overlayStyle}>
      <div style={modalStyle}>
        <div style={modalContentStyle}>
          {/* Left Stepper */}
          <div style={stepperContainerStyle}>
            <h3 style={stepperTitleStyle}>진행 단계</h3>
            <div style={stepperListStyle}>
              {STEP_ORDER.map((step, index) => {
                const info = STEP_INFO[step]
                const isActive = step === currentStep
                const isCompleted = index < currentStepIndex
                const isPending = index > currentStepIndex

                return (
                  <div key={step} style={stepItemStyle}>
                    <div style={{
                      ...stepCircleStyle,
                      ...(isActive ? activeStepCircleStyle : {}),
                      ...(isCompleted ? completedStepCircleStyle : {}),
                      ...(isPending ? pendingStepCircleStyle : {})
                    }}>
                      <span style={stepIconStyle}>{info.icon}</span>
                    </div>
                    <div style={stepLabelContainerStyle}>
                      <div style={{
                        ...stepLabelStyle,
                        ...(isActive ? activeStepLabelStyle : {})
                      }}>
                        {info.label}
                      </div>
                      <div style={stepDescriptionStyle}>
                        {info.description}
                      </div>
                    </div>
                    {index < STEP_ORDER.length - 1 && (
                      <div style={{
                        ...stepConnectorStyle,
                        ...(isCompleted ? completedConnectorStyle : {})
                      }} />
                    )}
                  </div>
                )
              })}
            </div>
          </div>

          {/* Right Content */}
          <div style={contentContainerStyle}>
            <div style={headerStyle}>
              <div>
                <h2 style={titleStyle}>
                  {STEP_INFO[currentStep].icon} {STEP_INFO[currentStep].label} 검수
                </h2>
                <p style={runIdStyle}>Run ID: {runId}</p>
              </div>
              <button onClick={onClose} style={closeButtonStyle}>✕</button>
            </div>

            <div style={contentScrollStyle}>
              {children}
            </div>

            <div style={footerStyle}>
              <button
                onClick={handleReject}
                disabled={isProcessing}
                style={{
                  ...buttonStyle,
                  ...rejectButtonStyle,
                  ...(isProcessing ? disabledButtonStyle : {})
                }}
              >
                {isProcessing ? '처리 중...' : '거부 및 재생성'}
              </button>
              <button
                onClick={handleApprove}
                disabled={isProcessing}
                style={{
                  ...buttonStyle,
                  ...approveButtonStyle,
                  ...(isProcessing ? disabledButtonStyle : {})
                }}
              >
                {isProcessing ? '처리 중...' : '승인 및 다음 단계'}
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

const stepConnectorStyle: React.CSSProperties = {
  position: 'absolute',
  left: '21px',
  top: '44px',
  bottom: '0',
  width: '2px',
  backgroundColor: '#E5E7EB',
}

const completedConnectorStyle: React.CSSProperties = {
  backgroundColor: '#10B981',
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
