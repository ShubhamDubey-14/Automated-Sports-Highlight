from flask import Flask, request, jsonify, send_file, session
from flask_cors import CORS
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
import os
import cv2
import numpy as np
import librosa
import moviepy.editor as mp
from scipy import signal
from sklearn.preprocessing import MinMaxScaler
import tempfile
import json
from datetime import datetime
import uuid
import traceback # Import traceback for better error logging

# --- Flask App Initialization and Configuration ---
app = Flask(__name__)
# WARNING: Change this key in production
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sports_highlights.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

CORS(app, supports_credentials=True)
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' 
login_manager.session_protection = 'strong'

# Configuration
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'webm'}

# Create directories if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# --- Database Models ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    videos = db.relationship('VideoHistory', backref='user', lazy=True, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

class VideoHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    highlight_filename = db.Column(db.String(255))
    sport_type = db.Column(db.String(50))
    sensitivity = db.Column(db.String(20))
    duration = db.Column(db.Float)
    highlight_count = db.Column(db.Integer)
    analysis_stats = db.Column(db.Text)  # JSON string
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    # Placeholder for frontend serving
    if os.path.exists('index.html'):
        return send_file('index.html')
    return "Sports Highlight Generator API is running."

# --- Sports Highlight Generation Logic ---

class SportsHighlightGenerator:
    def __init__(self):
        self.scaler = MinMaxScaler()
        
    def allowed_file(self, filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    
    def extract_frames(self, video_path, fps=1):
        """Extract frames from video at specified FPS"""
        cap = cv2.VideoCapture(video_path)
        frames = []
        timestamps = []
        
        frame_count = 0
        fps_original = cap.get(cv2.CAP_PROP_FPS)
        
        if fps_original <= 0:
            return [], []

        frame_interval = int(fps_original / fps)
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            if frame_count % frame_interval == 0:
                frames.append(frame)
                timestamps.append(frame_count / fps_original)
            
            frame_count += 1
        
        cap.release()
        return frames, timestamps
    
    def calculate_motion_score(self, frames):
        """Calculate motion intensity between consecutive frames"""
        motion_scores = []
        
        for i in range(1, len(frames)):
            gray1 = cv2.cvtColor(frames[i-1], cv2.COLOR_BGR2GRAY)
            gray2 = cv2.cvtColor(frames[i], cv2.COLOR_BGR2GRAY)
            diff = cv2.absdiff(gray1, gray2)
            
            total_pixels = diff.shape[0] * diff.shape[1]
            if total_pixels > 0:
                motion_score = np.sum(diff > 30) / total_pixels * 100
                motion_scores.append(motion_score)
            else:
                motion_scores.append(0)
        
        # Add 0 for the first frame to align with timestamps
        return [0] + motion_scores
    
    def detect_objects(self, frame):
        """Simple object detection using color-based tracking"""
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        yellow_lower = np.array([20, 100, 100])
        yellow_upper = np.array([35, 255, 255])
        yellow_mask = cv2.inRange(hsv, yellow_lower, yellow_upper)
        
        white_lower = np.array([0, 0, 200])
        white_upper = np.array([180, 30, 255])
        white_mask = cv2.inRange(hsv, white_lower, white_upper)
        
        orange_lower = np.array([0, 100, 100])
        orange_upper = np.array([20, 255, 255])
        orange_mask = cv2.inRange(hsv, orange_lower, orange_upper)
        
        combined_mask = cv2.bitwise_or(yellow_mask, cv2.bitwise_or(white_mask, orange_mask))
        
        contours, _ = cv2.findContours(combined_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        object_centers = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if 50 < area < 10000:
                M = cv2.moments(contour)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                    object_centers.append((cx, cy, area))
        
        return object_centers
    
    def track_ball_movement(self, frames):
        """Track ball movement across frames"""
        ball_positions = []
        movement_scores = []
        
        for frame in frames:
            objects = self.detect_objects(frame)
            if objects:
                largest_obj = max(objects, key=lambda x: x[2])
                ball_positions.append((largest_obj[0], largest_obj[1]))
            else:
                ball_positions.append(None)
        
        movement_scores.append(0)
        for i in range(1, len(ball_positions)):
            if ball_positions[i] and ball_positions[i-1]:
                dx = ball_positions[i][0] - ball_positions[i-1][0]
                dy = ball_positions[i][1] - ball_positions[i-1][1]
                movement = np.sqrt(dx*dx + dy*dy)
                movement_scores.append(movement)
            else:
                movement_scores.append(0)
        
        return ball_positions, movement_scores
    
    def analyze_audio(self, video_path):
        """Analyze audio for volume spikes and frequency patterns"""
        video = None
        try:
            video = mp.VideoFileClip(video_path)
            audio = video.audio
            
            if audio is None:
                video.close()
                return [], [], [], []
            
            temp_audio_path = tempfile.mktemp(suffix='.wav')
            audio.write_audiofile(temp_audio_path, verbose=False, logger=None, codec='pcm_s16le')
            
            y, sr = librosa.load(temp_audio_path)
            
            frame_length = 2048
            hop_length = 512
            rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
            spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr, n_fft=frame_length, hop_length=hop_length)[0]
            zcr = librosa.feature.zero_crossing_rate(y, frame_length=frame_length, hop_length=hop_length)[0]
            
            times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop_length)
            
            os.unlink(temp_audio_path)
            video.close()
            
            return times, rms, spectral_centroid, zcr
            
        except Exception as e:
            print(f"Audio analysis error: {e}")
            if video: video.close()
            return [], [], [], []
    
    def detect_audio_events(self, times, rms, spectral_centroid, zcr):
        """Detect audio events (volume spikes, excitement)"""
        if len(rms) == 0:
            return []
        
        # Normalization
        rms_normalized = (rms - np.min(rms)) / (np.max(rms) - np.min(rms) + 1e-6)
        sc_normalized = (spectral_centroid - np.min(spectral_centroid)) / (np.max(spectral_centroid) - np.min(spectral_centroid) + 1e-6)
        zcr_normalized = (zcr - np.min(zcr)) / (np.max(zcr) - np.min(zcr) + 1e-6)
        
        # Thresholds
        volume_threshold = np.percentile(rms_normalized, 85)
        freq_threshold = np.percentile(sc_normalized, 75)
        activity_threshold = np.percentile(zcr_normalized, 70)
        
        audio_events = []
        for i in range(len(times)):
            score = 0
            if rms_normalized[i] > volume_threshold: score += 0.45
            if sc_normalized[i] > freq_threshold: score += 0.35
            if zcr_normalized[i] > activity_threshold: score += 0.20

            if score > 0.6:  
                audio_events.append({
                    'timestamp': times[i],
                    'score': score,
                    'volume': float(rms_normalized[i]),
                    'frequency': float(sc_normalized[i]),
                    'activity': float(zcr_normalized[i])
                })
        
        return audio_events
    
    def calculate_highlight_scores(self, motion_scores, movement_scores, audio_events, timestamps):
        """Calculate combined highlight scores for each time segment"""
        highlight_segments = []
        segment_duration = 5.0 
        max_time = max(timestamps) if timestamps else 0
        
        for start_time in np.arange(0, max_time, segment_duration / 2.0): # Overlapping segments
            end_time = min(start_time + segment_duration, max_time)
            
            segment_motion = []
            segment_movement = []
            segment_audio = []
            
            for i, timestamp in enumerate(timestamps):
                if start_time <= timestamp < end_time:
                    if i < len(motion_scores): segment_motion.append(motion_scores[i])
                    if i < len(movement_scores): segment_movement.append(movement_scores[i])
            
            for event in audio_events:
                if start_time <= event['timestamp'] < end_time:
                    segment_audio.append(event['score'])
            
            motion_score = np.mean(segment_motion) if segment_motion else 0
            movement_score = np.mean(segment_movement) if segment_movement else 0
            audio_score = np.mean(segment_audio) if segment_audio else 0
            
            # Simple weighted average (audio_score is normalized 0-1, so we multiply by 100 for balance)
            total_score = (motion_score * 0.4 + movement_score * 0.3 + audio_score * 100 * 0.3) / 1.0
            
            if total_score > 35 or audio_score > 0.6: 
                highlight_segments.append({
                    'start_time': start_time,
                    'end_time': end_time,
                    'duration': end_time - start_time,
                    'score': total_score,
                    'motion_score': motion_score,
                    'movement_score': movement_score,
                    'audio_score': audio_score,
                    'triggers': self._get_triggers(motion_score, movement_score, audio_score)
                })
        
        highlight_segments.sort(key=lambda x: x['score'], reverse=True)
        return highlight_segments
    
    def _get_triggers(self, motion_score, movement_score, audio_score):
        """Determine what triggered this highlight"""
        triggers = []
        if motion_score > 25: triggers.append('High Motion')
        if movement_score > 35: triggers.append('Ball Tracking')
        if audio_score > 0.6: triggers.append('Volume Spike')
        if audio_score > 0.4: triggers.append('Crowd Reaction')
        return triggers
    
    # CORRECTED: Renamed the main method to avoid conflict with the Flask route
    def process_highlights(self, video_path, sport_type='general', sensitivity='medium', max_duration=30):
        """Main function to generate highlights from video"""
        try:
            # 1. Analysis
            frames, timestamps = self.extract_frames(video_path, fps=5) 
            motion_scores = self.calculate_motion_score(frames)
            ball_positions, movement_scores = self.track_ball_movement(frames) 
            times, rms, spectral_centroid, zcr = self.analyze_audio(video_path)
            audio_events = self.detect_audio_events(times, rms, spectral_centroid, zcr)
            all_highlights = self.calculate_highlight_scores(motion_scores, movement_scores, audio_events, timestamps)
            
            # 2. Filtering
            if sensitivity == 'low': final_highlights = [h for h in all_highlights if h['score'] >= 55] 
            elif sensitivity == 'high': final_highlights = [h for h in all_highlights if h['score'] >= 25] 
            else: final_highlights = [h for h in all_highlights if h['score'] >= 35] 

            # 3. Duration Limiting
            total_duration = 0
            filtered_highlights = []
            for highlight in final_highlights:
                if total_duration + highlight['duration'] <= max_duration:
                    filtered_highlights.append(highlight)
                    total_duration += highlight['duration']
                else:
                    if max_duration - total_duration > 1.0: 
                         highlight['end_time'] = highlight['start_time'] + (max_duration - total_duration)
                         highlight['duration'] = max_duration - total_duration
                         filtered_highlights.append(highlight)
                         total_duration = max_duration
                    break
            
            filtered_highlights.sort(key=lambda x: x['start_time'])

            # 4. Compilation
            highlight_video_path = None
            highlight_filename = None
            if filtered_highlights:
                output_uuid = uuid.uuid4().hex
                highlight_filename = f"highlights_{output_uuid}.mp4"
                highlight_video_path = os.path.join(OUTPUT_FOLDER, highlight_filename)
                
                compilation_success = self.compile_highlight_video_moviepy(video_path, filtered_highlights, highlight_video_path)
                
                if not compilation_success:
                    highlight_video_path = None
                    highlight_filename = None
            
            analysis_stats = {
                'motion_events': len([s for s in motion_scores if s > 20]),
                'audio_peaks': len(audio_events),
                'ball_tracking_accuracy': len([p for p in ball_positions if p is not None]) / len(ball_positions) * 100 if ball_positions else 0
            }
            
            return {
                'highlights': filtered_highlights,
                'total_highlights': len(filtered_highlights),
                'total_duration': total_duration,
                'highlight_video_path': highlight_video_path,
                'highlight_filename': highlight_filename,
                'analysis_stats': analysis_stats
            }
            
        except Exception as e:
            print(f"Error generating highlights: {e}")
            traceback.print_exc()
            return {'error': f"Processing error: {str(e)}"}

    def compile_highlight_video(self, video_path, highlights, output_path):
        return self.compile_highlight_video_moviepy(video_path, highlights, output_path)
    
    def compile_highlight_video_moviepy(self, video_path, highlights, output_path):
        """Optimized MoviePy compilation"""
        original_video = None
        try:
            from moviepy.editor import VideoFileClip, concatenate_videoclips
            
            original_video = VideoFileClip(video_path, audio=True, target_resolution=(720, None))
            
            highlight_clips = []
            for highlight in highlights:
                start_time = highlight['start_time']
                end_time = highlight['end_time']
                video_duration = original_video.duration
                start_time = max(0, min(start_time, video_duration))
                end_time = max(start_time, min(end_time, video_duration))
                
                if end_time > start_time:
                    clip = original_video.subclip(start_time, end_time)
                    highlight_clips.append(clip)
            
            if highlight_clips:
                final_video = concatenate_videoclips(highlight_clips)
                final_video.write_videofile(
                    output_path,
                    codec='libx264',
                    audio_codec='aac',
                    preset='medium',
                    verbose=False,
                    threads=4, 
                    ffmpeg_params=["-crf", "23", "-pix_fmt", "yuv420p"] 
                )
                
                for clip in highlight_clips: clip.close()
                final_video.close()
                original_video.close()
                return True
            else:
                original_video.close()
                return False
                
        except Exception as e:
            print(f"MoviePy compilation failed: {e}")
            traceback.print_exc()
            if original_video: original_video.close()
            return False

# Initialize the generator
generator = SportsHighlightGenerator()

# --- Authentication Routes (No Change) ---
@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        if not username or not email or not password:
            return jsonify({'error': 'All fields are required'}), 400
        if User.query.filter_by(username=username).first():
            return jsonify({'error': 'Username already exists'}), 409
        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Email already exists'}), 409
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return jsonify({'message': 'User registered successfully', 'user': {'id': user.id, 'username': user.username, 'email': user.email}}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        if not username or not password:
            return jsonify({'error': 'Username and password are required'}), 400
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user, remember=True) 
            return jsonify({'message': 'Login successful', 'user': {'id': user.id, 'username': user.username, 'email': user.email}})
        else:
            return jsonify({'error': 'Invalid username or password'}), 401
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({'message': 'Logout successful'})

@app.route('/api/user', methods=['GET'])
@login_required
def get_current_user():
    return jsonify({'user': {'id': current_user.id, 'username': current_user.username, 'email': current_user.email}})

@app.route('/api/history', methods=['GET'])
@login_required
def get_user_history():
    try:
        videos = VideoHistory.query.filter_by(user_id=current_user.id).order_by(VideoHistory.created_at.desc()).all()
        history = []
        for video in videos:
            stats = json.loads(video.analysis_stats) if video.analysis_stats else {}
            history.append({
                'id': video.id, 'original_filename': video.original_filename, 'highlight_filename': video.highlight_filename, 
                'sport_type': video.sport_type, 'sensitivity': video.sensitivity, 'duration': video.duration,
                'highlight_count': video.highlight_count, 'analysis_stats': stats, 'created_at': video.created_at.isoformat()
            })
        return jsonify({'history': history})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- Highlight Generation Routes (Corrected) ---

@app.route('/api/upload', methods=['POST'])
def upload_video():
    """Handle video upload, returning the unique filename."""
    if 'video' not in request.files:
        return jsonify({'error': 'No video file provided'}), 400
    
    file = request.files['video']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and generator.allowed_file(file.filename):
        original_filename = file.filename
        file_extension = original_filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
        filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
        file.save(filepath)
        
        return jsonify({
            'message': 'Video uploaded successfully',
            'filename': unique_filename,       # <-- Key to pass to generate-highlights
            'original_filename': original_filename 
        }), 201
    
    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/api/generate-highlights', methods=['POST'])
def generate_highlights_route():
    """Generates highlights using the unique filename and cleans up the original file."""
    data = request.get_json()
    
    if not data or 'filename' not in data:
        return jsonify({'error': 'No unique filename provided from upload step.'}), 400
    
    unique_filename = data['filename']
    original_filename = data.get('original_filename', unique_filename)
    sport_type = data.get('sport_type', 'general')
    sensitivity = data.get('sensitivity', 'medium')
    max_duration = data.get('max_duration', 30)
    
    # CORRECTED: Construct the file path reliably
    filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
    
    if not os.path.exists(filepath):
        return jsonify({'error': f'Video file not found: {unique_filename}'}), 404
    
    try:
        # CORRECTED: Call the renamed class method
        results = generator.process_highlights(filepath, sport_type, sensitivity, max_duration)
        
        if 'error' in results:
            return jsonify(results), 500

        # Save to User History (if authenticated)
        if current_user.is_authenticated:
            highlight_filename = results.get('highlight_filename')
            history_entry = VideoHistory(
                user_id=current_user.id, original_filename=original_filename, highlight_filename=highlight_filename,
                sport_type=sport_type, sensitivity=sensitivity, duration=results.get('total_duration', 0.0),
                highlight_count=results.get('total_highlights', 0), analysis_stats=json.dumps(results.get('analysis_stats', {}))
            )
            db.session.add(history_entry)
            db.session.commit()
            results['history_id'] = history_entry.id
        
        # ADDED: Cleanup: Delete the large uploaded file after processing
        try:
             os.remove(filepath)
             print(f"Cleaned up uploaded file: {filepath}")
        except OSError as e:
             print(f"Error deleting uploaded file {filepath}: {e}")
        
        # Remove full path from the result
        if 'highlight_video_path' in results:
            del results['highlight_video_path']
        
        return jsonify(results)
    
    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return jsonify({'error': f"Highlight generation failed: {str(e)}"}), 500

# --- File Serving Routes (Minor Clean-up) ---

@app.route('/api/stream-highlights/<path:filename>', methods=['GET'])
def stream_highlights(filename):
    try:
        # Sanitize filename to prevent directory traversal
        base_filename = os.path.basename(filename)
        file_path = os.path.join(OUTPUT_FOLDER, base_filename)
        
        if os.path.exists(file_path):
            return send_file(file_path, mimetype='video/mp4', conditional=True)
        else:
            return jsonify({'error': f'Highlight video not found: {base_filename}'}), 404
    except Exception as e:
        print(f"Streaming error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/download-highlights/<path:filename>', methods=['GET'])
def download_highlights(filename):
    try:
        base_filename = os.path.basename(filename)
        file_path = os.path.join(OUTPUT_FOLDER, base_filename)
        
        if os.path.exists(file_path):
            download_name = f'highlights_{base_filename}'
            
            if current_user.is_authenticated:
                history_entry = VideoHistory.query.filter_by(highlight_filename=base_filename, user_id=current_user.id).first()
                if history_entry:
                    name_part = os.path.splitext(history_entry.original_filename)[0]
                    download_name = f'{name_part}_highlights.mp4'
            
            return send_file(file_path, as_attachment=True, download_name=download_name)
        else:
            return jsonify({'error': f'Highlight video not found: {base_filename}'}), 404
    except Exception as e:
        print(f"Download error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

# --- Main Run Block ---

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)