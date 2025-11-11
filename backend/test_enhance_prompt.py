"""
Simple test script for prompt enhancement API endpoint.
Run this after starting the backend server.
"""
import requests
import json

def test_enhance_prompt():
    url = "http://localhost:8000/api/v1/enhance-prompt"

    test_cases = [
        {
            "name": "Simple cat story",
            "payload": {
                "original_prompt": "고양이가 우주를 여행하는 이야기",
                "mode": "general"
            }
        },
        {
            "name": "Food review",
            "payload": {
                "original_prompt": "맛있는 파스타 레시피",
                "mode": "general"
            }
        },
        {
            "name": "Travel vlog",
            "payload": {
                "original_prompt": "제주도 여행 브이로그",
                "mode": "general"
            }
        }
    ]

    for test_case in test_cases:
        print(f"\n{'='*60}")
        print(f"Test: {test_case['name']}")
        print(f"{'='*60}")
        print(f"Original prompt: {test_case['payload']['original_prompt']}")
        print(f"\nSending request...")

        try:
            response = requests.post(url, json=test_case['payload'])

            if response.status_code == 200:
                result = response.json()
                print(f"\n✅ SUCCESS")
                print(f"\nEnhanced prompt: {result['enhanced_prompt']}")
                print(f"\nSuggested parameters:")
                print(f"  - Cuts: {result['suggested_num_cuts']}")
                print(f"  - Characters: {result['suggested_num_characters']}")
                print(f"  - Art style: {result['suggested_art_style']}")
                print(f"  - Music genre: {result['suggested_music_genre']}")
                print(f"\nReasoning: {result['reasoning']}")
            else:
                print(f"\n❌ FAILED")
                print(f"Status code: {response.status_code}")
                print(f"Response: {response.text}")

        except Exception as e:
            print(f"\n❌ ERROR: {e}")

if __name__ == "__main__":
    print("Prompt Enhancement API Test")
    print("Make sure the backend server is running on http://localhost:8000")
    input("\nPress Enter to start testing...")

    test_enhance_prompt()

    print(f"\n{'='*60}")
    print("Testing complete!")
    print(f"{'='*60}")
