import os
import requests
from PIL import Image
import io
import re
from config import Config

class OCRSpaceAPI:
    BASE_URL = 'https://api.ocr.space/parse/image'
    
    def __init__(self, api_key, debug=True):
        self.api_key = api_key
        self.debug = debug

    def _log(self, message):
        if self.debug:
            print(f"[OCR DEBUG] {message}")


    def _compress_image(self, image_path, max_size_mb=0.5):
        with Image.open(image_path) as img:
            # First resize by half
            new_width = img.width // 2
            new_height = img.height // 2
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Convert to RGB if needed
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Compress with quality reduction if needed
            buffer = io.BytesIO()
            quality = 95
            while True:
                buffer.seek(0)
                buffer.truncate(0)
                img.save(buffer, format='JPEG', quality=quality)
                size_mb = buffer.tell() / (1024 * 1024)
                
                if size_mb <= max_size_mb:
                    break
                
                quality -= 5
                if quality < 10:
                    raise ValueError("Cannot compress image under 0.5MB")
            
            compressed_path = os.path.splitext(image_path)[0] + '_compressed.jpg'
            img.save(compressed_path, format='JPEG', quality=quality)
            self._log(f"Image compressed to {size_mb:.2f}MB")
            return compressed_path
    
    def extract_text(self, image_path):
        try:
            compressed_image = self._compress_image(image_path)
            self._log(f"Processing image: {compressed_image}")

            with open(compressed_image, 'rb') as image_file:
                payload = {
                    'apikey': self.api_key,
                    'language': Config.OCR_LANGUAGE,
                    'OCREngine': Config.OCR_ENGINE,
                    'isOverlayRequired': True,
                    'detectOrientation': True,
                }
                
                files = {'image': ('image.jpg', image_file, 'image/jpeg')}
                
                self._log("Sending request to OCR.space API")
                response = requests.post(self.BASE_URL, files=files, data=payload)
                result = response.json()
                self._log(f"API Response: {result}")

                if result.get('OCRExitCode') not in [1, 2]:
                    self._log(f"OCR Failed: {result.get('ErrorMessage', 'Unknown error')}")
                    return None

                parsed_text = result['ParsedResults'][0]['ParsedText']
                self._log(f"Raw Parsed Text:\n{parsed_text}")

                # Try different strategies to find the score
                strategies = [
                    self._extract_score_near_player,
                    self._extract_score_with_commas,
                    self._extract_longest_number
                ]

                for strategy in strategies:
                    score = strategy(parsed_text)
                    if score is not None:
                        self._log(f"Found score using strategy {strategy.__name__}: {score}")
                        return score

                self._log("No score found using any strategy")
                return None

        except Exception as e:
            self._log(f"Error processing image: {e}")
            return None
        finally:
            if 'compressed_image' in locals():
                try:
                    os.remove(compressed_image)
                except:
                    pass

    def _extract_score_near_player(self, text):
        lines = text.split('\n')
        for i, line in enumerate(lines):
            if 'PLAYER' in line.upper():
                # Check next line for score
                if i + 1 < len(lines):
                    score = self._extract_number(lines[i + 1])
                    if score:
                        return score
        return None

    def _extract_score_with_commas(self, text):
        # Handle both periods and commas as separators
        text = text.replace('.', ',')
        matches = re.findall(r'[\d,]+', text)
        for match in matches:
            clean_num = match.replace(',', '')
            if len(clean_num) >= Config.OCR_MIN_SCORE_LENGTH:
                return int(clean_num)
        return None

    def _extract_longest_number(self, text):
        # Clean text of both periods and commas
        clean_text = text.replace(',', '').replace('.', '')
        numbers = re.findall(r'\d+', clean_text)
        if numbers:
            longest = max(numbers, key=len)
            if len(longest) >= Config.OCR_MIN_SCORE_LENGTH:
                return int(longest)
        return None

    def _extract_number(self, text):
        # Remove both periods and commas, then find numbers
        clean_text = text.replace(',', '').replace('.', '')
        numbers = re.findall(r'\d+', clean_text)
        valid_numbers = [n for n in numbers if len(n) >= Config.OCR_MIN_SCORE_LENGTH]
        return int(valid_numbers[0]) if valid_numbers else None