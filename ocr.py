import os
import requests
from PIL import Image
import io
import re
from typing import Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum

class OCREndpoint(Enum):
    PRIMARY = "https://apipro1.ocr.space/parse/image"
    BACKUP = "https://apipro2.ocr.space/parse/image"
    FREE = "https://api.ocr.space/parse/image"

@dataclass
class OCRConfig:
    pro_key: str
    free_key: str
    debug: bool = True

@dataclass
class OCRResult:
    score: Optional[int]
    raw_text: str
    strategy_used: str
    confidence: float
    endpoint_used: str

class OCRSpaceAPI:
    def __init__(self, config: OCRConfig):
        self.pro_key = config.pro_key
        self.free_key = config.free_key
        self.debug = config.debug
        self.endpoints = [
            (OCREndpoint.PRIMARY.value, self.pro_key),
            (OCREndpoint.BACKUP.value, self.pro_key),
            (OCREndpoint.FREE.value, self.free_key)
        ]

    def _log(self, message: str) -> None:
        if self.debug:
            print(f"[OCR DEBUG] {message}")

    def _compress_image(self, image_path: str, max_size_mb: float = 0.25) -> str:
        with Image.open(image_path) as img:
            # First resize by half
            new_width = img.width // 2
            new_height = img.height // 2
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
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
            
            compressed_path = f"{os.path.splitext(image_path)[0]}_compressed.jpg"
            img.save(compressed_path, format='JPEG', quality=quality)
            self._log(f"Image compressed to {size_mb:.2f}MB at quality {quality}")
            return compressed_path

    def _make_ocr_request(self, image_file, endpoint: str, api_key: str) -> Tuple[Optional[dict], Optional[str]]:
        try:
            payload = {
                'apikey': api_key,
                'language': 'eng',
                'OCREngine': 2,
                'isOverlayRequired': True,
                'detectOrientation': True,
                'scale': True
            }
            
            files = {'image': image_file}
            response = requests.post(endpoint, files=files, data=payload)
            result = response.json()
            
            if result.get('OCRExitCode') in [1, 2]:
                return result, None
            return None, result.get('ErrorMessage', 'Unknown error')
            
        except requests.RequestException as e:
            return None, str(e)

    def extract_text(self, image_path: str) -> Optional[OCRResult]:
        try:
            compressed_image = self._compress_image(image_path)
            
            with open(compressed_image, 'rb') as image_file:
                for endpoint, api_key in self.endpoints:
                    self._log(f"Trying endpoint: {endpoint}")
                    image_file.seek(0)
                    
                    result, error = self._make_ocr_request(image_file, endpoint, api_key)
                    if result:
                        parsed_text = result['ParsedResults'][0]['ParsedText']
                        confidence = float(result['ParsedResults'][0].get('TextOverlay', {}).get('Lines', [{}])[0].get('WordsConfidence', [0])[0])
                        
                        self._log(f"Success with endpoint {endpoint}")
                        self._log(f"Raw Parsed Text:\n{parsed_text}")
                        self._log(f"Confidence: {confidence}")

                        strategies = [
                            (self._extract_between_markers, "between_markers"),
                            (self._extract_near_player_lines, "near_player_lines"),
                            (self._extract_first_numeric_sequence, "first_numeric")
                        ]

                        for strategy_func, strategy_name in strategies:
                            score = strategy_func(parsed_text)
                            if score is not None:
                                return OCRResult(score, parsed_text, strategy_name, confidence, endpoint)
                    else:
                        self._log(f"Failed with endpoint {endpoint}: {error}")

                return None

        except Exception as e:
            self._log(f"Error processing image: {e}")
            return None
        finally:
            if os.path.exists(compressed_image):
                os.remove(compressed_image)

    def _extract_between_markers(self, text: str) -> Optional[int]:
        lines = text.split('\n')
        try:
            player_index = next((i for i, line in enumerate(lines) if 'PLAYER' in line.upper()), -1)
            level_index = next((i for i, line in enumerate(lines) if 'LEVEL' in line.upper()), -1)
            
            if player_index != -1 and level_index != -1 and player_index + 1 < level_index:
                score_line = lines[player_index + 1]
                score = re.sub(r'[^\d]', '', score_line)
                self._log(f"Between markers strategy: {score}")
                return int(score) if score else None
        except Exception as e:
            self._log(f"Between markers strategy failed: {e}")
        return None

    def _extract_near_player_lines(self, text: str) -> Optional[int]:
        lines = text.split('\n')
        for i, line in enumerate(lines):
            if 'PLAYER' in line.upper():
                for j in range(1, 3):
                    if i + j < len(lines):
                        score_line = lines[i + j]
                        score = re.sub(r'[^\d]', '', score_line)
                        if score:
                            self._log(f"Near player lines strategy: {score}")
                            return int(score)
        return None

    def _extract_first_numeric_sequence(self, text: str) -> Optional[int]:
        scores = re.findall(r'\d{5,}', text.replace('.', ''))
        if scores:
            score = int(scores[0])
            self._log(f"First numeric sequence strategy: {score}")
            return score
        return None
