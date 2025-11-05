# =============================================================================
# DEPRECATED FILE - DO NOT USE
# =============================================================================
# This file has been deprecated and moved to backend/bin/
#
# Reason: CSV format removed due to GPT parsing issues
# Use instead:
#   - plot_generator.generate_plot_with_characters() for plot.json generation
#   - json_converter.convert_plot_to_json() for JSON conversion
#
# Migration: All flows now use plot.json instead of plot.csv
# Date: 2025-01-05
# =============================================================================

# """
# CSV to JSON conversion utilities.
# Handles plot planning CSV generation and conversion to final JSON schema.
# """
# import logging
# import csv
# import json
# from pathlib import Path
# from typing import List, Dict
# from datetime import datetime
#
# from app.utils.seeds import generate_char_seed, generate_bg_seed
# from app.utils.sfx_tags import extract_sfx_tags
#
# logger = logging.getLogger(__name__)
#
#
# def generate_plot_from_prompt(
#     run_id: str,
#     prompt: str,
#     num_characters: int,
#     num_cuts: int,
#     mode: str = "story"
# ) -> tuple[Path, Path]:
#     """
#     Generate characters.json and plot.csv from user prompt using GPT-4o-mini.
#
#     Args:
#         run_id: Run identifier
#         prompt: User prompt
#         num_characters: Number of characters
#         num_cuts: Number of scenes/cuts
#         mode: story or ad
#
#     Returns:
#         Tuple of (characters_json_path, plot_csv_path)
#     """
#     logger.info(f"Generating CSV for prompt: {prompt[:50]}...")
#
#     # run_id가 이미 타임스탬프_프롬프트 형식으로 전달됨
#     output_dir = Path(f"app/data/outputs/{run_id}")
#     output_dir.mkdir(parents=True, exist_ok=True)
#
#     characters_path = output_dir / "characters.json"
#     csv_path = output_dir / "plot.csv"
#
#     # GPT-4o-mini로 생성 시도
#     try:
#         from openai import OpenAI
#         from app.config import settings
#
#         if not settings.OPENAI_API_KEY:
#             logger.warning("OpenAI API key not set, using rule-based generation")
#             raise ValueError("No OpenAI API key")
#
#         client = OpenAI(api_key=settings.OPENAI_API_KEY)
#
#         # 1단계: 캐릭터 정의 생성
#         char_system_prompt = f"""당신은 숏폼 영상 콘텐츠의 캐릭터 디자이너입니다.
# 사용자의 요청에 맞는 {num_characters}명의 캐릭터를 만들어주세요.
#
# 각 캐릭터마다 다음 정보를 JSON 형식으로 제공하세요:
# - char_id: char_1, char_2, ... 형식
# - name: 캐릭터 이름 (창의적으로)
# - appearance: 외형 묘사 (이미지 생성에 사용됩니다. 상세하게 작성)
# - personality: 성격/특징
# - voice_profile: "default" (고정값)
# - seed: char_1은 1002, char_2는 1003, ... 순서대로
#
# **중요**:
# - 반드시 JSON 형식으로만 출력하세요
# - appearance는 이미지 생성 프롬프트로 사용되므로 시각적 특징을 상세히 작성
# - 해설자인 경우 appearance를 "음성만 있는 해설자 (이미지 없음)"으로 설정
#
# JSON 형식:
# {{
#   "characters": [
#     {{
#       "char_id": "char_1",
#       "name": "캐릭터 이름",
#       "appearance": "상세한 외형 묘사",
#       "personality": "성격 설명",
#       "voice_profile": "default",
#       "seed": 1002
#     }}
#   ]
# }}"""
#
#         logger.info(f"Calling GPT-4o-mini for plot generation...")
#
#         response = client.chat.completions.create(
#             model="gpt-4o-mini",
#             messages=[
#                 {"role": "system", "content": system_prompt},
#                 {"role": "user", "content": prompt}
#             ],
#             temperature=0.8,
#             max_tokens=1500
#         )
#
#         csv_content = response.choices[0].message.content.strip()
#
#         # CSV 내용에서 마크다운 코드 블록 제거 (있을 경우)
#         if csv_content.startswith("```"):
#             lines = csv_content.split("\n")
#             csv_content = "\n".join([line for line in lines if not line.startswith("```")])
#
#         # CSV 파일로 저장
#         with open(csv_path, "w", encoding="utf-8") as f:
#             f.write(csv_content.strip())
#
#         logger.info(f"✅ CSV generated with GPT-4o-mini: {csv_path}")
#
#         # CSV 검증 (행 개수 확인)
#         with open(csv_path, "r", encoding="utf-8") as f:
#             reader = csv.DictReader(f)
#             rows = list(reader)
#             logger.info(f"Generated {len(rows)} scenes")
#
#         return csv_path
#
#     except Exception as e:
#         logger.warning(f"GPT-4o-mini failed: {e}, falling back to rule-based generation")
#
#         # 폴백: 룰 기반 생성
#         rows = []
#         char_names = ["주인공", "친구"] if num_characters == 2 else ["주인공"]
#
#         for i in range(num_cuts):
#             scene_id = f"scene_{i+1}"
#             char_id = f"char_{(i % num_characters) + 1}"
#             char_name = char_names[i % num_characters]
#
#             if mode == "story":
#                 text = f"{prompt}의 {i+1}번째 장면입니다."
#                 text_type = "dialogue"
#             else:
#                 text = f"{prompt}를 소개하는 {i+1}번째 내용입니다."
#                 text_type = "dialogue"
#
#             emotion = "neutral" if i % 2 == 0 else "happy"
#
#             rows.append({
#                 "scene_id": scene_id,
#                 "char_id": char_id,
#                 "char_name": char_name,
#                 "text": text,
#                 "text_type": text_type,
#                 "emotion": emotion,
#                 "subtitle_position": "bottom" if i % 2 == 0 else "top",
#                 "duration_ms": 5000
#             })
#
#         # CSV 작성
#         with open(csv_path, "w", encoding="utf-8", newline="") as f:
#             fieldnames = [
#                 "scene_id", "char_id", "char_name", "text", "text_type",
#                 "emotion", "subtitle_position", "duration_ms"
#             ]
#             writer = csv.DictWriter(f, fieldnames=fieldnames)
#             writer.writeheader()
#             writer.writerows(rows)
#
#         logger.info(f"CSV generated (rule-based fallback): {csv_path} ({len(rows)} rows)")
#         return csv_path
#
#
# def csv_to_json(
#     csv_path: str,
#     run_id: str,
#     art_style: str = "파스텔 수채화",
#     music_genre: str = "ambient"
# ) -> Path:
#     """
#     Convert plot CSV to final JSON schema.
#
#     Args:
#         csv_path: Path to CSV file
#         run_id: Run identifier
#         art_style: Art style for image generation
#         music_genre: Music genre for BGM
#
#     Returns:
#         Path to generated JSON file
#     """
#     logger.info(f"Converting CSV to JSON: {csv_path}")
#
#     # Read CSV
#     rows = []
#     with open(csv_path, "r", encoding="utf-8") as f:
#         reader = csv.DictReader(f)
#         rows = list(reader)
#
#     if not rows:
#         raise ValueError("CSV is empty")
#
#     # Group rows by scene
#     scenes_data: Dict[str, List[dict]] = {}
#     characters_set = set()
#
#     for row in rows:
#         scene_id = row["scene_id"]
#         char_id = row["char_id"]
#
#         if scene_id not in scenes_data:
#             scenes_data[scene_id] = []
#
#         scenes_data[scene_id].append(row)
#         characters_set.add((char_id, row.get("char_name", "Character")))
#
#     # Build JSON structure
#     from app.schemas.json_layout import (
#         ShortsJSON, Timeline, Character, Scene, ImageSlot,
#         TextLine, BGM
#     )
#
#     # Create characters
#     characters = []
#     for char_id, char_name in sorted(characters_set):
#         characters.append(
#             Character(
#                 char_id=char_id,
#                 name=char_name,
#                 persona=f"{char_name} 설정",
#                 voice_profile="default",
#                 seed=generate_char_seed(char_id)
#             ).model_dump()
#         )
#
#     # Create scenes
#     scenes = []
#     total_duration = 0
#
#     for scene_id, scene_rows in sorted(scenes_data.items(), key=lambda x: int(x[0].split("_")[1])):
#         first_row = scene_rows[0]
#         # Extract sequence from scene_id (e.g., "scene_1" -> 1)
#         sequence = int(scene_id.split("_")[1])
#         duration_ms = int(first_row["duration_ms"])
#         total_duration += duration_ms
#
#         # Create text lines (통합: 대사 + 해설)
#         texts = []
#         for idx, row in enumerate(scene_rows):
#             line_id = f"{scene_id}_line_{idx+1}"
#             text = row["text"]
#             text_type = row.get("text_type", "dialogue")
#
#             # text_type이 dialogue일 경우에만 큰따옴표 추가
#             display_text = f'"{text}"' if text_type == "dialogue" else text
#
#             texts.append(
#                 TextLine(
#                     line_id=line_id,
#                     char_id=row["char_id"],
#                     text=display_text,
#                     text_type=text_type,
#                     emotion=row.get("emotion", "neutral"),
#                     position=row.get("subtitle_position", "bottom"),
#                     audio_url="",  # Will be filled by voice task
#                     start_ms=idx * 2000,  # Stagger by 2 seconds
#                     duration_ms=duration_ms
#                 ).model_dump()
#             )
#
#         # Create image slots (placeholder)
#         images = [
#             ImageSlot(
#                 slot_id="center",
#                 type="character",
#                 ref_id=first_row["char_id"],
#                 image_url="",  # Will be filled by designer task
#                 z_index=1
#             ).model_dump()
#         ]
#
#         # SFX tags
#         sfx_list = []
#         sfx_tags = extract_sfx_tags(first_row["text"], first_row.get("emotion", "neutral"))
#         if sfx_tags:
#             from app.schemas.json_layout import SFX
#             sfx_list.append(
#                 SFX(
#                     sfx_id=f"{scene_id}_sfx",
#                     tags=sfx_tags,
#                     audio_url="",
#                     start_ms=0,
#                     volume=0.5
#                 ).model_dump()
#             )
#
#         # Create scene
#         scene = Scene(
#             scene_id=scene_id,
#             sequence=sequence,
#             duration_ms=duration_ms,
#             images=images,
#             texts=texts,
#             bgm=None,  # Will use global BGM
#             sfx=sfx_list,
#             bg_seed=generate_bg_seed(sequence),
#             transition="fade"
#         )
#
#         scenes.append(scene.model_dump())
#
#     # Create timeline
#     timeline = Timeline(
#         total_duration_ms=total_duration,
#         aspect_ratio="9:16",
#         fps=30,
#         resolution="1080x1920"
#     )
#
#     # Create final JSON
#     shorts_json = ShortsJSON(
#         project_id=run_id,
#         title=f"AutoShorts {run_id}",
#         mode="story",
#         timeline=timeline.model_dump(),
#         characters=characters,
#         scenes=scenes,
#         global_bgm=None,  # Will be filled by composer task
#         metadata={
#             "art_style": art_style,
#             "music_genre": music_genre,
#             "generated_from": str(csv_path)
#         }
#     )
#
#     # Write JSON (same folder as CSV)
#     json_path = Path(csv_path).parent / "layout.json"
#     with open(json_path, "w", encoding="utf-8") as f:
#         json.dump(shorts_json.model_dump(), f, indent=2, ensure_ascii=False)
#
#     logger.info(f"JSON generated: {json_path}")
#     return json_path
#
#
# # =============================================================================
# # Backward Compatibility Aliases (Deprecated)
# # =============================================================================
# # These aliases are provided for backward compatibility with older code.
# # Please use the new functions from plot_generator.py and json_converter.py instead.
#
# # Deprecated: Use plot_generator.generate_plot_with_characters() instead
# generate_csv_from_prompt = generate_plot_from_prompt
