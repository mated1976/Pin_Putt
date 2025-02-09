# database.py
import json
import os
from datetime import datetime
import shutil
from typing import Dict, List, Union, Optional

class PinPuttDB:
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.scores_file = os.path.join(data_dir, 'scores.json')
        self.init_db()
    
    def init_db(self) -> None:
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
        
        if not os.path.exists(self.scores_file):
            initial_data = {
                'current_target': None,
                'events': [],
                'players': {}
            }
            self.save_data(initial_data)
    
    def save_data(self, data: Dict) -> None:
        with open(self.scores_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    
    def load_data(self) -> Dict:
        with open(self.scores_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def set_target(self, target_score: int) -> None:
        data = self.load_data()
        data['current_target'] = target_score
        self.save_data(data)
    
    def add_attempt(self, initials: str, score: int) -> Dict:
        data = self.load_data()
        timestamp = datetime.now().isoformat()
        
        target = data['current_target']
        if target is None:
            raise ValueError("No target score has been set")
        
        distance = abs(score - target)
        attempt = {
            'score': score,
            'timestamp': timestamp,
            'distance': distance,
            'target': target
        }
        
        if initials not in data['players']:
            data['players'][initials] = {
                'attempts': [],
                'best_distance': None
            }
        
        player = data['players'][initials]
        player['attempts'].append(attempt)
        
        if player['best_distance'] is None or distance < player['best_distance']:
            player['best_distance'] = distance
        
        self.save_data(data)
        return attempt
    
    def get_leaderboard(self) -> List[Dict]:
        data = self.load_data()
        leaderboard = []
        
        for initials, player in data['players'].items():
            if player['attempts']:
                best_attempt = min(player['attempts'], 
                                 key=lambda x: x['distance'])
                
                leaderboard.append({
                    'initials': initials,
                    'score': best_attempt['score'],
                    'distance': best_attempt['distance'],
                    'timestamp': best_attempt['timestamp']
                })
        
        return sorted(leaderboard, key=lambda x: x['distance'])
    
    def get_player_stats(self, initials: str) -> Dict:
        data = self.load_data()
        if initials not in data['players']:
            return {
                'total_attempts': 0,
                'best_score': 0,
                'average_score': 0,
                'best_distance': 0,
                'attempts': []
            }
            
        player = data['players'][initials]
        attempts = player['attempts']
        if not attempts:
            return {
                'total_attempts': 0,
                'best_score': 0,
                'average_score': 0,
                'best_distance': 0,
                'attempts': []
            }
        
        scores = [a['score'] for a in attempts]
        return {
            'total_attempts': len(attempts),
            'best_score': max(scores),
            'average_score': int(sum(scores) / len(scores)),
            'best_distance': player['best_distance'],
            'attempts': attempts
        }
    
    def get_current_target(self) -> Optional[int]:
        data = self.load_data()
        return data['current_target']
    
    def reset_scores(self) -> str:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        archive_file = os.path.join(self.data_dir, f'closedscores_{timestamp}.json')
        
        if os.path.exists(self.scores_file):
            shutil.copy2(self.scores_file, archive_file)
        
        data = self.load_data()
        new_data = {
            'current_target': data['current_target'],
            'events': [],
            'players': {}
        }
        self.save_data(new_data)
        
        return archive_file
    
    def get_enhanced_stats(self) -> Dict:
        data = self.load_data()
        all_attempts = []
        stats = {
            'total_attempts': 0,
            'unique_players': len(data['players']),
            'average_score': 0,
            'best_score': 0,
            'top_players': [],
            'score_distribution': []
        }

        for initials, player in data['players'].items():
            attempts = player.get('attempts', [])
            if attempts:
                all_attempts.extend(attempts)
                best_attempt = min(attempts, key=lambda x: x['distance'])
                stats['top_players'].append({
                    'initials': initials,
                    'best_score': best_attempt['score'],
                    'distance': best_attempt['distance'],
                    'total_attempts': len(attempts)
                })

        if all_attempts:
            scores = [a['score'] for a in all_attempts]
            stats.update({
                'total_attempts': len(all_attempts),
                'average_score': int(sum(scores) / len(scores)),
                'best_score': max(scores),
                'score_distribution': self._calculate_score_bands(scores)
            })
            stats['top_players'].sort(key=lambda x: x['distance'])

        return stats
    
    def _calculate_score_bands(self, scores: List[int]) -> List[Dict]:
        if not scores:
            return []
            
        min_score = min(scores)
        max_score = max(scores)
        band_size = (max_score - min_score) / 8 if len(scores) > 1 else 1
        bands = []
        
        for i in range(8):
            lower = min_score + (i * band_size)
            upper = lower + band_size
            count = sum(1 for score in scores if lower <= score < upper)
            
            bands.append({
                'range': f'{int(lower):,}-{int(upper):,}',
                'count': count,
                'percentage': round((count / len(scores)) * 100, 1)
            })
        
        return bands