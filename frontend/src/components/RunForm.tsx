import { useState, FormEvent } from 'react'
import { createRun, uploadReferenceImage } from '../api/client'

interface RunFormProps {
  onRunCreated: (runId: string) => void
}

export default function RunForm({ onRunCreated }: RunFormProps) {
  const [mode, setMode] = useState<'general' | 'story' | 'ad'>('general')
  const [prompt, setPrompt] = useState('')
  const [numCharacters, setNumCharacters] = useState<1 | 2>(1)
  const [numCuts, setNumCuts] = useState(3)
  const [artStyle, setArtStyle] = useState('파스텔 수채화')
  const [musicGenre, setMusicGenre] = useState('ambient')
  const [referenceFiles, setReferenceFiles] = useState<File[]>([])
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setIsSubmitting(true)

    try {
      // Upload reference images
      const referenceImages: string[] = []
      for (const file of referenceFiles) {
        const filename = await uploadReferenceImage(file)
        referenceImages.push(filename)
      }

      // Create run
      const result = await createRun({
        mode,
        prompt,
        num_characters: numCharacters,
        num_cuts: numCuts,
        art_style: artStyle,
        music_genre: musicGenre,
        reference_images: referenceImages.length > 0 ? referenceImages : undefined,
      })

      onRunCreated(result.run_id)
    } catch (error) {
      console.error('Failed to create run:', error)
      alert('Run 생성 실패: ' + error)
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setReferenceFiles(Array.from(e.target.files))
    }
  }

  return (
    <form onSubmit={handleSubmit} className="run-form">
      <h2>새 숏츠 생성</h2>

      <div className="form-group">
        <label>모드</label>
        <select value={mode} onChange={(e) => setMode(e.target.value as 'general' | 'story' | 'ad')}>
          <option value="general">일반</option>
          <option value="story">스토리텔링</option>
          <option value="ad">광고</option>
        </select>
      </div>

      <div className="form-group">
        <label>프롬프트</label>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="예: 우주를 여행하는 고양이 이야기"
          rows={4}
          required
        />
      </div>

      <div className="form-row">
        <div className="form-group">
          <label>등장인물 수</label>
          <select
            value={numCharacters}
            onChange={(e) => setNumCharacters(Number(e.target.value) as 1 | 2)}
          >
            <option value={1}>1명</option>
            <option value={2}>2명</option>
          </select>
        </div>

        <div className="form-group">
          <label>컷 수 (1-10)</label>
          <input
            type="number"
            value={numCuts}
            onChange={(e) => setNumCuts(Number(e.target.value))}
            min={1}
            max={10}
            required
          />
        </div>
      </div>

      <div className="form-group">
        <label>화풍</label>
        <input
          type="text"
          value={artStyle}
          onChange={(e) => setArtStyle(e.target.value)}
          placeholder="예: 파스텔 수채화, 애니메이션, 사실적"
        />
      </div>

      <div className="form-group">
        <label>음악 장르</label>
        <input
          type="text"
          value={musicGenre}
          onChange={(e) => setMusicGenre(e.target.value)}
          placeholder="예: ambient, cinematic, upbeat"
        />
      </div>

      <div className="form-group">
        <label>참조 이미지 (선택)</label>
        <input
          type="file"
          accept="image/*"
          multiple
          onChange={handleFileChange}
        />
        {referenceFiles.length > 0 && (
          <p className="file-count">{referenceFiles.length}개 파일 선택됨</p>
        )}
      </div>

      <button type="submit" disabled={isSubmitting || !prompt} className="btn-submit">
        {isSubmitting ? '생성 중...' : '숏츠 생성 시작'}
      </button>
    </form>
  )
}
