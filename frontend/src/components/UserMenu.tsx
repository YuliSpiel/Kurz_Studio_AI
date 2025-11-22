import { useState, useRef, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import './UserMenu.css'

interface UserMenuProps {
  onOpenAuthModal: (mode: 'login' | 'register') => void
  onOpenVideoSettings: () => void
}

export default function UserMenu({ onOpenAuthModal, onOpenVideoSettings }: UserMenuProps) {
  const { user, logout } = useAuth()
  const [isOpen, setIsOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Get first character of username for avatar
  const getInitial = (name: string) => {
    return name.charAt(0).toUpperCase()
  }

  if (!user) {
    return (
      <div className="user-menu-auth-buttons">
        <button
          className="auth-btn login-btn"
          onClick={() => onOpenAuthModal('login')}
        >
          Log in
        </button>
        <button
          className="auth-btn signup-btn"
          onClick={() => onOpenAuthModal('register')}
        >
          Get started
        </button>
      </div>
    )
  }

  return (
    <div className="user-menu-container" ref={menuRef}>
      <button
        className="user-menu-trigger"
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
        aria-haspopup="true"
      >
        <span className="user-avatar">
          {getInitial(user.username)}
        </span>
        <span className="user-name">{user.username}'s Studio</span>
        <svg
          className={`chevron-icon ${isOpen ? 'open' : ''}`}
          xmlns="http://www.w3.org/2000/svg"
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <path d="M6 9l6 6 6-6"/>
        </svg>
      </button>

      {isOpen && (
        <div className="user-menu-dropdown" role="menu">
          {/* User Info Section */}
          <div className="user-menu-header">
            <span className="user-avatar large">
              {getInitial(user.username)}
            </span>
            <div className="user-info">
              <p className="user-display-name">{user.username}'s Studio</p>
              <p className="user-email">{user.email}</p>
            </div>
          </div>

          {/* Credits Section */}
          <div className="user-menu-credits">
            <div className="credits-header">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm.31-8.86c-1.77-.45-2.34-.94-2.34-1.67 0-.84.79-1.43 2.1-1.43 1.38 0 1.9.66 1.94 1.64h1.71c-.05-1.34-.87-2.57-2.49-2.97V5H10.9v1.69c-1.51.32-2.72 1.3-2.72 2.81 0 1.79 1.49 2.69 3.66 3.21 1.95.46 2.34 1.15 2.34 1.87 0 .53-.39 1.39-2.1 1.39-1.6 0-2.23-.72-2.32-1.64H8.04c.1 1.7 1.36 2.66 2.86 2.97V19h2.34v-1.67c1.52-.29 2.72-1.16 2.73-2.77-.01-2.2-1.9-2.96-3.66-3.42z"/>
              </svg>
              <span className="credits-label">Credits</span>
            </div>
            <div className="credits-value">{user.credits}</div>
          </div>

          {/* Charge Button */}
          <button className="user-menu-item charge-btn" role="menuitem">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
            </svg>
            <span>충전하기</span>
          </button>

          <div className="user-menu-divider" />

          {/* Video Settings */}
          <button
            className="user-menu-item"
            role="menuitem"
            onClick={() => {
              onOpenVideoSettings()
              setIsOpen(false)
            }}
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3l-2.5-3z"/>
              <circle cx="12" cy="13" r="3"/>
            </svg>
            <span>영상 설정</span>
          </button>

          {/* Help */}
          <button className="user-menu-item" role="menuitem">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10"/>
              <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/>
              <line x1="12" y1="17" x2="12.01" y2="17"/>
            </svg>
            <span>도움말</span>
          </button>

          <div className="user-menu-divider" />

          {/* Logout */}
          <button
            className="user-menu-item logout"
            role="menuitem"
            onClick={() => {
              logout()
              setIsOpen(false)
            }}
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
              <polyline points="16 17 21 12 16 7"/>
              <line x1="21" y1="12" x2="9" y2="12"/>
            </svg>
            <span>로그아웃</span>
          </button>
        </div>
      )}
    </div>
  )
}
