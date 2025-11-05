# Deprecated Files

이 폴더에는 더 이상 사용되지 않는 레거시 코드가 보관되어 있습니다.

## 파일 목록

### csv_to_json.py
**Deprecated Date:** 2025-01-05
**Reason:** CSV 포맷 제거 (GPT 파싱 오류 문제)
**Migration:**
- `plot_generator.generate_plot_with_characters()` - plot.json 생성
- `json_converter.convert_plot_to_json()` - JSON 변환

**변경 사항:**
- ❌ CSV 포맷 (plot.csv)
- ✅ JSON 포맷 (plot.json)
- 이유: GPT가 CSV 생성 시 따옴표/쉼표 파싱 오류 발생

## 사용 금지

이 폴더의 파일들은 **절대 사용하지 마세요**. 참고용으로만 보관됩니다.
