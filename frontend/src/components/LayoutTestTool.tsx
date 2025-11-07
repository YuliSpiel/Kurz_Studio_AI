import { useState } from 'react'

type Position = 'left' | 'center' | 'right'

const positionMap: Record<Position, number> = {
  left: 0.2,
  center: 0.5,
  right: 0.8,
}

export default function LayoutTestTool() {
  const [position, setPosition] = useState<Position>('center')
  const [xPos, setXPos] = useState<number>(positionMap['center'])
  const [text, setText] = useState<string>('여기에 자막을 입력하세요')
  const [showText, setShowText] = useState<boolean>(true)

  // Update x_pos when position changes
  const handlePositionChange = (newPosition: Position) => {
    setPosition(newPosition)
    setXPos(positionMap[newPosition])
  }

  // 9:16 aspect ratio (1080x1920)
  // Scale down for display (e.g., 360x640)
  const frameWidth = 360
  const frameHeight = 640

  // Character image dimensions (2:3 ratio at 60% of screen height)
  const charHeight = frameHeight * 0.6
  const charWidth = charHeight * (2 / 3)

  // Calculate character position (x_pos is center of image)
  // Director.py logic: x_center = x_pos * width, y_center = height * 0.5
  const xCenter = xPos * frameWidth
  const yCenter = frameHeight * 0.5

  // Calculate top-left corner so image center is at (xCenter, yCenter)
  const charLeft = xCenter - charWidth / 2
  const charTop = yCenter - charHeight / 2

  // Text position (top 10%)
  const textTop = frameHeight * 0.1

  return (
    <div className="layout-test-tool">
      <h2>레이아웃 테스트 도구</h2>
      <p>이미지와 자막 배치를 실시간으로 확인하세요</p>

      <div className="test-container">
        {/* Preview Frame */}
        <div className="preview-section">
          <div
            className="frame"
            style={{
              width: `${frameWidth}px`,
              height: `${frameHeight}px`,
              position: 'relative',
              background: 'linear-gradient(to bottom, #87ceeb, #90ee90)',
              border: '2px solid #333',
              overflow: 'hidden',
            }}
          >
            {/* Character Image */}
            <img
              src="/outputs/20251106_1906_카피바라와고양이/images/scene_1_center.png"
              alt="Character"
              style={{
                position: 'absolute',
                left: `${charLeft}px`,
                top: `${charTop}px`,
                height: `${charHeight}px`,
                width: `${charWidth}px`,
                objectFit: 'cover',
                border: '1px solid rgba(255,255,255,0.5)',
              }}
            />

            {/* Text Overlay */}
            {showText && text && (
              <div
                style={{
                  position: 'absolute',
                  top: `${textTop}px`,
                  left: '5%',
                  width: '90%',
                  color: 'white',
                  fontSize: '20px',
                  fontWeight: 'bold',
                  textAlign: 'center',
                  textShadow: '2px 2px 4px black',
                  lineHeight: '1.4',
                  wordWrap: 'break-word',
                }}
              >
                {text}
              </div>
            )}

            {/* Position Indicator - Vertical (x_pos) */}
            <div
              style={{
                position: 'absolute',
                left: `${xPos * frameWidth}px`,
                top: '0',
                bottom: '0',
                width: '2px',
                background: 'red',
                opacity: 0.5,
              }}
              title={`x_pos: ${xPos.toFixed(2)}`}
            />

            {/* Position Indicator - Horizontal (y_center = 0.5) */}
            <div
              style={{
                position: 'absolute',
                top: `${yCenter}px`,
                left: '0',
                right: '0',
                height: '2px',
                background: 'blue',
                opacity: 0.5,
              }}
              title="y_center: 0.5 (화면 중앙)"
            />
          </div>

          <div className="position-info">
            <p>
              <strong>Frame:</strong> {frameWidth}x{frameHeight} (9:16)
            </p>
            <p>
              <strong>Character:</strong> {charWidth.toFixed(0)}x{charHeight.toFixed(0)} (2:3 ratio, 60% height)
            </p>
            <p>
              <strong>Image Center:</strong> ({xCenter.toFixed(0)}, {yCenter.toFixed(0)})px
            </p>
            <p>
              <strong>Top-Left Corner:</strong> ({charLeft.toFixed(0)}, {charTop.toFixed(0)})px
            </p>
          </div>
        </div>

        {/* Controls */}
        <div className="controls-section">
          <div className="control-group">
            <h3>캐릭터 위치</h3>
            <div className="position-buttons">
              <button
                className={`pos-btn ${position === 'left' ? 'active' : ''}`}
                onClick={() => handlePositionChange('left')}
              >
                Left (0.2)
              </button>
              <button
                className={`pos-btn ${position === 'center' ? 'active' : ''}`}
                onClick={() => handlePositionChange('center')}
              >
                Center (0.5)
              </button>
              <button
                className={`pos-btn ${position === 'right' ? 'active' : ''}`}
                onClick={() => handlePositionChange('right')}
              >
                Right (0.8)
              </button>
            </div>
          </div>

          <div className="control-group">
            <h3>정확한 x_pos 조정</h3>
            <input
              type="range"
              min="0"
              max="1"
              step="0.01"
              value={xPos}
              onChange={(e) => setXPos(parseFloat(e.target.value))}
              style={{ width: '100%' }}
            />
            <div className="slider-labels">
              <span>0.0 (왼쪽 끝)</span>
              <span>{xPos.toFixed(2)}</span>
              <span>1.0 (오른쪽 끝)</span>
            </div>
          </div>

          <div className="control-group">
            <h3>자막 입력</h3>
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              rows={3}
              style={{ width: '100%', padding: '8px', fontSize: '14px' }}
              placeholder="자막을 입력하세요..."
            />
            <label style={{ display: 'block', marginTop: '8px' }}>
              <input
                type="checkbox"
                checked={showText}
                onChange={(e) => setShowText(e.target.checked)}
              />
              {' '}자막 표시
            </label>
          </div>

          <div className="control-group">
            <h3>참고 정보</h3>
            <ul style={{ fontSize: '12px', lineHeight: '1.6' }}>
              <li>프레임: 9:16 비율 (1080x1920)</li>
              <li>캐릭터 이미지: 2:3 비율, 화면 높이의 60%</li>
              <li>이미지 중심: x_pos (가변), y=0.5 (화면 수직 중앙 고정)</li>
              <li>자막 위치: 상단 10% (고정)</li>
              <li>x_pos: 이미지 중심점의 x 좌표 (0.0 ~ 1.0)</li>
              <li>빨간 세로선: x_pos 위치 표시</li>
              <li>파란 가로선: y_center (0.5) 위치 표시</li>
            </ul>
          </div>
        </div>
      </div>

      <style>{`
        .layout-test-tool {
          max-width: 1200px;
          margin: 0 auto;
          padding: 20px;
        }

        .test-container {
          display: flex;
          gap: 40px;
          margin-top: 20px;
        }

        .preview-section {
          flex-shrink: 0;
        }

        .position-info {
          margin-top: 16px;
          padding: 12px;
          background: #f5f5f5;
          border-radius: 4px;
          font-size: 13px;
        }

        .position-info p {
          margin: 4px 0;
        }

        .controls-section {
          flex: 1;
          display: flex;
          flex-direction: column;
          gap: 24px;
        }

        .control-group h3 {
          margin: 0 0 12px 0;
          font-size: 16px;
          color: #333;
        }

        .position-buttons {
          display: flex;
          gap: 8px;
        }

        .pos-btn {
          flex: 1;
          padding: 10px 16px;
          border: 2px solid #ddd;
          background: white;
          border-radius: 4px;
          cursor: pointer;
          font-size: 14px;
          transition: all 0.2s;
        }

        .pos-btn:hover {
          border-color: #666;
        }

        .pos-btn.active {
          background: #007bff;
          color: white;
          border-color: #007bff;
        }

        .slider-labels {
          display: flex;
          justify-content: space-between;
          font-size: 11px;
          color: #666;
          margin-top: 4px;
        }

        @media (max-width: 768px) {
          .test-container {
            flex-direction: column;
          }
        }
      `}</style>
    </div>
  )
}
