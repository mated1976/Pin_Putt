from flask import Flask, render_template, request, jsonify, redirect, url_for
import os
from database import PinPuttDB
from functools import wraps
from config import Config
from werkzeug.utils import secure_filename
from ocr import OCRSpaceAPI

app = Flask(__name__)
app.config.from_object(Config)
db = PinPuttDB(Config.DATA_DIR)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        key = request.args.get('key')
        if key != app.config['ADMIN_KEY']:
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

@app.route('/')
def home():
    return render_template('index.html', target=db.get_current_target())

@app.route('/admin')
@admin_required
def admin():
    return render_template('admin.html', target=db.get_current_target())

@app.route('/player/<initials>')
def player_detail(initials):
    return render_template('player.html', initials=initials)

@app.route('/api/target', methods=['POST'])
@admin_required
def set_target():
    try:
        target = int(request.form.get('target', 0))
        db.set_target(target)
        return jsonify({'status': 'success', 'target': target})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/api/reset', methods=['POST'])
@admin_required
def reset_scores():
    try:
        archive_file = db.reset_scores()
        return jsonify({
            'status': 'success',
            'message': f'Scores archived to {os.path.basename(archive_file)}'
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/api/score', methods=['POST'])
def submit_score():
    try:
        initials = request.form.get('initials', '').upper()
        score = int(request.form.get('score', 0))
        attempt = db.add_attempt(initials, score)
        return jsonify({'status': 'success', 'attempt': attempt})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/api/process_image', methods=['POST'])
def process_image():
    app.logger.info("Process image endpoint hit")
    
    if 'image' not in request.files:
        app.logger.error("No image file in request")
        return jsonify({'error': 'No image file'}), 400
        
    file = request.files['image']
    if not file.filename:
        app.logger.error("No filename")
        return jsonify({'error': 'No selected file'}), 400
        
    if not allowed_file(file.filename):
        app.logger.error(f"Invalid file type: {file.filename}")
        return jsonify({'error': 'Invalid file type'}), 400
        
    try:
        filename = secure_filename(file.filename)
        filepath = os.path.join(Config.UPLOADS_DIR, filename)
        app.logger.info(f"Saving file to: {filepath}")
        file.save(filepath)
        
        ocr = OCRSpaceAPI(Config.OCR_API_KEY, debug=Config.OCR_DEBUG)
        app.logger.info("Starting OCR processing")
        score = ocr.extract_text(filepath)
        app.logger.info(f"OCR result: {score}")
        
        if score is None:
            app.logger.error("No score detected")
            return jsonify({'error': 'Could not detect score'}), 400
            
        return jsonify({'score': score})
        
    except Exception as e:
        app.logger.error(f"Error processing image: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)
            app.logger.info("Cleaned up uploaded file")

@app.route('/api/leaderboard')
def get_leaderboard():
    target = db.get_current_target()
    leaderboard = db.get_leaderboard()
    return jsonify({'target': target, 'leaderboard': leaderboard})

@app.route('/api/stats')
@admin_required
def get_stats():
    try:
        stats = db.get_enhanced_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/api/player/<initials>/stats')
def get_player_stats(initials):
    try:
        return jsonify(db.get_player_stats(initials))
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=False)