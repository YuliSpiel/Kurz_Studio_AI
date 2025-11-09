import { useState, FormEvent } from 'react'
import { createRun } from '../api/client'

interface AdModeFormProps {
  onRunCreated: (runId: string) => void
}

export default function AdModeForm({ onRunCreated }: AdModeFormProps) {
  const [productUrl, setProductUrl] = useState('')
  const [numCuts, setNumCuts] = useState(5)
  const [artStyle, setArtStyle] = useState('현대적이고 세련된')
  const [musicGenre, setMusicGenre] = useState('upbeat')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isFetching, setIsFetching] = useState(false)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setIsSubmitting(true)

    try {
      const result = await createRun({
        mode: 'ad',
        prompt: productUrl,  // URL을 prompt로 전달
        num_characters: 1,
        num_cuts: numCuts,
        art_style: artStyle,
        music_genre: musicGenre,
      })

      onRunCreated(result.run_id)
    } catch (error) {
      console.error('Failed to create run:', error)
      alert('광고 생성 실패: ' + error)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="run-form ad-mode-form">
      <h2>광고 모드</h2>
      <p className="mode-description">제품 URL을 입력하면 자동으로 정보를 수집하여 홍보 숏츠를 생성합니다</p>

      <div className="form-group">
        <label>제품 페이지 URL</label>
        <input
          type="url"
          value={productUrl}
          onChange={(e) => setProductUrl(e.target.value)}
          placeholder="예: https://example.com/product/123"
          required
        />
        <p className="field-hint">쿠팡, 네이버 쇼핑, 자사 쇼핑몰 등 제품 페이지 URL을 입력하세요</p>
      </div>

      <div className="form-group">
        <label>장면 수</label>
        <input
          type="number"
          value={numCuts}
          onChange={(e) => setNumCuts(Number(e.target.value))}
          min={3}
          max={10}
          required
        />
      </div>

      <div className="form-group">
        <label>비주얼 스타일</label>
        <select
          value={artStyle}
          onChange={(e) => setArtStyle(e.target.value)}
        >
          <option value="현대적이고 세련된">현대적이고 세련된</option>
          <option value="미니멀하고 깔끔한">미니멀하고 깔끔한</option>
          <option value="생동감 넘치는">생동감 넘치는</option>
          <option value="프리미엄 럭셔리">프리미엄 럭셔리</option>
        </select>
      </div>

      <div className="form-group">
        <label>배경음악</label>
        <select
          value={musicGenre}
          onChange={(e) => setMusicGenre(e.target.value)}
        >
          <option value="upbeat">경쾌하고 활기찬</option>
          <option value="corporate">기업용 프로페셔널</option>
          <option value="energetic">에너제틱하고 강렬한</option>
          <option value="modern">모던하고 트렌디한</option>
        </select>
      </div>

      <button
        type="submit"
        disabled={isSubmitting || !productUrl}
        className="btn-submit"
      >
        {isSubmitting ? '광고 생성 중...' : '광고 숏츠 만들기'}
      </button>
    </form>
  )
}
