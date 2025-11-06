import { useState, FormEvent } from 'react'
import { createRun, uploadReferenceImage } from '../api/client'

interface Character {
  name: string
  gender: 'male' | 'female' | 'other'
  role: string
  personality: string
  appearance: string
  referenceImage?: File
}

interface StoryModeFormProps {
  onRunCreated: (runId: string) => void
}

export default function StoryModeForm({ onRunCreated }: StoryModeFormProps) {
  const [storyText, setStoryText] = useState('')
  const [characters, setCharacters] = useState<Character[]>([
    {
      name: '',
      gender: 'female',
      role: '',
      personality: '',
      appearance: '',
    }
  ])
  const [referenceImage, setReferenceImage] = useState<File | null>(null)
  const [stylePreset, setStylePreset] = useState<string>('dreamy')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const addCharacter = () => {
    if (characters.length < 3) {
      setCharacters([...characters, {
        name: '',
        gender: 'female',
        role: '',
        personality: '',
        appearance: '',
      }])
    }
  }

  const removeCharacter = (index: number) => {
    if (characters.length > 1) {
      setCharacters(characters.filter((_, i) => i !== index))
    }
  }

  const updateCharacter = (index: number, field: keyof Character, value: any) => {
    const updated = [...characters]
    updated[index] = { ...updated[index], [field]: value }
    setCharacters(updated)
  }

  const handleCharacterImageChange = (index: number, file: File | undefined) => {
    const updated = [...characters]
    updated[index] = { ...updated[index], referenceImage: file }
    setCharacters(updated)
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setIsSubmitting(true)

    try {
      // Upload reference images for characters
      const characterData = await Promise.all(
        characters.map(async (char) => {
          let referenceImagePath: string | undefined
          if (char.referenceImage) {
            referenceImagePath = await uploadReferenceImage(char.referenceImage)
          }
          return {
            name: char.name,
            gender: char.gender,
            role: char.role,
            personality: char.personality,
            appearance: char.appearance,
            reference_image: referenceImagePath,
          }
        })
      )

      // Upload general reference image
      let generalReferenceImage: string | undefined
      if (referenceImage) {
        generalReferenceImage = await uploadReferenceImage(referenceImage)
      }

      const result = await createRun({
        mode: 'story',
        prompt: storyText,
        num_characters: characters.length,
        num_cuts: 0, // Will be determined by story length
        art_style: stylePreset,
        music_genre: 'cinematic',
        characters: characterData,
        reference_images: generalReferenceImage ? [generalReferenceImage] : undefined,
      })

      onRunCreated(result.run_id)
    } catch (error) {
      console.error('Failed to create run:', error)
      alert('Run 생성 실패: ' + error)
    } finally {
      setIsSubmitting(false)
    }
  }

  const isFormValid = () => {
    return (
      storyText.trim() !== '' &&
      characters.every(char =>
        char.name.trim() !== '' &&
        char.personality.trim() !== '' &&
        char.appearance.trim() !== ''
      )
    )
  }

  return (
    <form onSubmit={handleSubmit} className="run-form story-mode-form">
      <h2>스토리 모드</h2>
      <p className="mode-description">비주얼노벨 스타일의 스토리텔링 숏폼을 생성합니다</p>

      {/* Story Text */}
      <div className="form-group">
        <label>스토리 텍스트 (필수)</label>
        <textarea
          value={storyText}
          onChange={(e) => setStoryText(e.target.value)}
          placeholder="줄글 형태로 스토리를 작성하세요. 대사와 해설을 자유롭게 섞어서 쓸 수 있습니다.&#10;&#10;예시:&#10;어느 날, 작은 마을에 살던 루피는 친구를 찾아 모험을 떠났다.&#10;'안녕, 나는 루피야! 너는 누구니?'&#10;낯선 고양이 미야가 조심스럽게 대답했다.&#10;'나는 미야야. 너도 모험을 좋아해?'"
          rows={8}
          required
        />
      </div>

      {/* Characters Section */}
      <div className="characters-section">
        <div className="section-header">
          <label>캐릭터 정보 ({characters.length}/3)</label>
          <div className="character-buttons">
            <button
              type="button"
              onClick={addCharacter}
              disabled={characters.length >= 3}
              className="btn-add-character"
            >
              + 캐릭터 추가
            </button>
          </div>
        </div>

        {characters.map((char, index) => (
          <div key={index} className="character-card">
            <div className="character-card-header">
              <h3>캐릭터 {index + 1}</h3>
              {characters.length > 1 && (
                <button
                  type="button"
                  onClick={() => removeCharacter(index)}
                  className="btn-remove-character"
                >
                  ✕ 제거
                </button>
              )}
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>이름 (필수)</label>
                <input
                  type="text"
                  value={char.name}
                  onChange={(e) => updateCharacter(index, 'name', e.target.value)}
                  placeholder="예: 루피"
                  required
                />
              </div>

              <div className="form-group">
                <label>성별</label>
                <select
                  value={char.gender}
                  onChange={(e) => updateCharacter(index, 'gender', e.target.value)}
                >
                  <option value="female">여성</option>
                  <option value="male">남성</option>
                  <option value="other">기타</option>
                </select>
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>역할</label>
                <input
                  type="text"
                  value={char.role}
                  onChange={(e) => updateCharacter(index, 'role', e.target.value)}
                  placeholder="예: 주인공, 친구, 조력자"
                />
              </div>

              <div className="form-group">
                <label>성격 (필수)</label>
                <input
                  type="text"
                  value={char.personality}
                  onChange={(e) => updateCharacter(index, 'personality', e.target.value)}
                  placeholder="예: 활발하고 호기심 많음"
                  required
                />
              </div>
            </div>

            <div className="form-group">
              <label>외형 설명 (필수)</label>
              <textarea
                value={char.appearance}
                onChange={(e) => updateCharacter(index, 'appearance', e.target.value)}
                placeholder="이미지 생성에 사용됩니다. 헤어스타일, 의상, 특징 등을 상세히 적어주세요.&#10;예: 금발의 긴 머리를 포니테일로 묶은 소녀. 파란색 원피스를 입고 있으며 큰 갈색 눈동자가 인상적."
                rows={3}
                required
              />
            </div>

            <div className="form-group">
              <label>레퍼런스 이미지 (선택)</label>
              <input
                type="file"
                accept="image/*"
                onChange={(e) => handleCharacterImageChange(index, e.target.files?.[0])}
              />
              {char.referenceImage && (
                <p className="file-name">{char.referenceImage.name}</p>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* General Settings */}
      <div className="form-group">
        <label>분위기 레퍼런스 이미지 (선택)</label>
        <input
          type="file"
          accept="image/*"
          onChange={(e) => setReferenceImage(e.target.files?.[0] || null)}
        />
        {referenceImage && (
          <p className="file-name">{referenceImage.name}</p>
        )}
      </div>

      <div className="form-group">
        <label>스타일 프리셋</label>
        <select
          value={stylePreset}
          onChange={(e) => setStylePreset(e.target.value)}
        >
          <option value="dreamy">Dreamy (꿈결 같은)</option>
          <option value="melancholic">Melancholic (우울한)</option>
          <option value="cinematic">Cinematic (영화 같은)</option>
          <option value="vibrant">Vibrant (화사한)</option>
          <option value="noir">Noir (어두운)</option>
        </select>
      </div>

      <button
        type="submit"
        disabled={isSubmitting || !isFormValid()}
        className="btn-submit"
      >
        {isSubmitting ? '스토리 생성 중...' : '스토리 숏츠 만들기'}
      </button>
    </form>
  )
}
