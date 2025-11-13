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
from waitress import serve 

from flask import Flask, request, jsonify, send_file, session
from flask_cors import CORS
# ... (rest of your imports)
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///sports_highlights.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

CORS(app, supports_credentials=True)
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Configuration
UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
OUTPUT_FOLDER = os.getenv('OUTPUT_FOLDER', 'outputs')
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'webm'}

# Create directories if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    videos = db.relationship('VideoHistory', backref='user', lazy=True)

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
    return send_file('index.html')

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
        # Guard against invalid FPS values from the video metadata
        try:
            if not fps_original or fps_original <= 0 or np.isnan(fps_original):
                fps_original = float(fps)
        except Exception:
            fps_original = float(fps)
        # Ensure we never compute a zero frame interval
        frame_interval = max(1, int(round(fps_original / float(fps))))
        
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
            # Convert to grayscale
            gray1 = cv2.cvtColor(frames[i-1], cv2.COLOR_BGR2GRAY)
            gray2 = cv2.cvtColor(frames[i], cv2.COLOR_BGR2GRAY)
            
            # Calculate frame difference
            diff = cv2.absdiff(gray1, gray2)
            
            # Calculate motion score as percentage of changed pixels
            motion_score = np.sum(diff > 30) / (diff.shape[0] * diff.shape[1]) * 100
            motion_scores.append(motion_score)
        
        return motion_scores
    
    def detect_objects(self, frame):
        """Simple object detection using color-based tracking"""
        # Convert to HSV for better color detection
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # Define color ranges for common sports objects
        # Yellow (tennis ball, soccer ball)
        yellow_lower = np.array([20, 100, 100])
        yellow_upper = np.array([30, 255, 255])
        yellow_mask = cv2.inRange(hsv, yellow_lower, yellow_upper)
        
        # White (soccer ball, baseball)
        white_lower = np.array([0, 0, 200])
        white_upper = np.array([180, 30, 255])
        white_mask = cv2.inRange(hsv, white_lower, white_upper)
        
        # Orange (basketball)
        orange_lower = np.array([5, 100, 100])
        orange_upper = np.array([15, 255, 255])
        orange_mask = cv2.inRange(hsv, orange_lower, orange_upper)
        
        # Combine masks
        combined_mask = cv2.bitwise_or(yellow_mask, cv2.bitwise_or(white_mask, orange_mask))
        
        # Find contours
        contours, _ = cv2.findContours(combined_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter contours by area
        object_centers = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > 100:  # Minimum area threshold
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
                # Take the largest object (likely the ball)
                largest_obj = max(objects, key=lambda x: x[2])
                ball_positions.append((largest_obj[0], largest_obj[1]))
            else:
                ball_positions.append(None)
        
        # Calculate movement scores
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
        try:
            # Extract audio from video
            video = mp.VideoFileClip(video_path)
            audio = video.audio
            
            if audio is None:
                return [], []
            
            # Save audio temporarily
            temp_audio_path = tempfile.mktemp(suffix='.wav')
            audio.write_audiofile(temp_audio_path, verbose=False, logger=None)
            
            # Load audio with librosa
            y, sr = librosa.load(temp_audio_path)
            
            # Calculate RMS energy (volume)
            frame_length = 2048
            hop_length = 512
            rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
            
            # Calculate spectral centroid (brightness)
            spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
            
            # Calculate zero crossing rate (noise/activity)
            zcr = librosa.feature.zero_crossing_rate(y)[0]
            
            # Convert to time domain
            times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop_length)
            
            # Clean up temp file
            os.unlink(temp_audio_path)
            video.close()
            
            return times, rms, spectral_centroid, zcr
            
        except Exception as e:
            print(f"Audio analysis error: {e}")
            return [], [], [], []
    
    def detect_audio_events(self, times, rms, spectral_centroid, zcr):
        """Detect audio events (volume spikes, excitement)"""
        if len(rms) == 0:
            return []
        
        # Normalize RMS values
        rms_normalized = (rms - np.min(rms)) / (np.max(rms) - np.min(rms))
        
        # Detect volume spikes (above 80th percentile)
        volume_threshold = np.percentile(rms_normalized, 80)
        volume_spikes = rms_normalized > volume_threshold
        
        # Detect high frequency content (excitement)
        freq_threshold = np.percentile(spectral_centroid, 75)
        high_freq = spectral_centroid > freq_threshold
        
        # Detect high activity (noise)
        activity_threshold = np.percentile(zcr, 70)
        high_activity = zcr > activity_threshold
        
        # Combine conditions for audio events
        audio_events = []
        for i in range(len(times)):
            score = 0
            if volume_spikes[i]:
                score += 0.4
            if high_freq[i]:
                score += 0.3
            if high_activity[i]:
                score += 0.3
            
            if score > 0.5:  # Threshold for significant audio event
                audio_events.append({
                    'timestamp': times[i],
                    'score': score,
                    'volume': rms_normalized[i],
                    'frequency': spectral_centroid[i],
                    'activity': zcr[i]
                })
        
        return audio_events
    
    def calculate_highlight_scores(self, motion_scores, movement_scores, audio_events, timestamps):
        """Calculate combined highlight scores for each time segment"""
        highlight_segments = []
        
        # Create time segments (5-second windows)
        segment_duration = 5.0
        max_time = max(timestamps) if timestamps else 0
        
        for start_time in np.arange(0, max_time, segment_duration):
            end_time = min(start_time + segment_duration, max_time)
            
            # Find motion scores in this segment
            segment_motion = []
            segment_movement = []
            segment_audio = []
            
            for i, timestamp in enumerate(timestamps):
                if start_time <= timestamp < end_time:
                    if i < len(motion_scores):
                        segment_motion.append(motion_scores[i])
                    if i < len(movement_scores):
                        segment_movement.append(movement_scores[i])
            
            # Find audio events in this segment
            for event in audio_events:
                if start_time <= event['timestamp'] < end_time:
                    segment_audio.append(event['score'])
            
            # Calculate segment score
            motion_score = np.mean(segment_motion) if segment_motion else 0
            movement_score = np.mean(segment_movement) if segment_movement else 0
            audio_score = np.mean(segment_audio) if segment_audio else 0
            
            # Weighted combination
            total_score = (motion_score * 0.4 + movement_score * 0.3 + audio_score * 0.3)
            
            if total_score > 20:  # Threshold for highlight
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
        
        # Sort by score and return top segments
        highlight_segments.sort(key=lambda x: x['score'], reverse=True)
        return highlight_segments[:10]  # Top 10 highlights
    
    def _get_triggers(self, motion_score, movement_score, audio_score):
        """Determine what triggered this highlight"""
        triggers = []
        if motion_score > 15:
            triggers.append('High Motion')
        if movement_score > 20:
            triggers.append('Ball Tracking')
        if audio_score > 0.3:
            triggers.append('Volume Spike')
        if audio_score > 0.2:
            triggers.append('Crowd Reaction')
        return triggers
    
    def compile_highlight_video(self, video_path, highlights, output_path):
        """Compile highlights into a single video - Using MoviePy directly"""
        # Skip FFmpeg attempt and go straight to MoviePy which is already installed
        print("Using MoviePy for video compilation...")
        return self.compile_highlight_video_moviepy(video_path, highlights, output_path)
    
    def compile_highlight_video_moviepy(self, video_path, highlights, output_path):
        """Optimized MoviePy compilation for faster processing"""
        try:
            from moviepy.editor import VideoFileClip, concatenate_videoclips
            
            print("Using optimized MoviePy processing...")
            # Use lower resolution and faster processing settings
            original_video = VideoFileClip(video_path, audio=True, target_resolution=(480, None))
            
            # Extract highlight clips with optimized settings
            highlight_clips = []
            for highlight in highlights:
                start_time = highlight['start_time']
                # Calculate end_time if not present
                if 'end_time' in highlight:
                    end_time = highlight['end_time']
                else:
                    # Use duration to calculate end_time
                    end_time = start_time + highlight['duration']
                
                # Ensure times are within video bounds
                video_duration = original_video.duration
                start_time = max(0, min(start_time, video_duration))
                end_time = max(start_time, min(end_time, video_duration))
                
                clip = original_video.subclip(start_time, end_time)
                highlight_clips.append(clip)
            
            if highlight_clips:
                final_video = concatenate_videoclips(highlight_clips)
                final_video.write_videofile(
                    output_path,
                    codec='libx264',
                    audio_codec='aac',
                    preset='ultrafast',  # Fastest encoding
                    verbose=False,  # Hide detailed progress for speed
                    threads=8,     # Use more threads for faster processing
                    ffmpeg_params=["-crf", "30", "-tune", "fastdecode", "-movflags", "+faststart"]  # Optimize for speed
                )
                
                for clip in highlight_clips:
                    clip.close()
                final_video.close()
                original_video.close()
                return True
            else:
                original_video.close()
                return False
                
        except Exception as e:
            import traceback
            print(f"MoviePy compilation failed: {e}")
            traceback.print_exc()
            return False
            return False

    def generate_highlights(self, video_path, sport_type='general', sensitivity='medium', max_duration=30):
        """Main function to generate highlights from video"""
        try:
            # Extract frames
            frames, timestamps = self.extract_frames(video_path)
            
            # Computer vision analysis
            motion_scores = self.calculate_motion_score(frames)
            ball_positions, movement_scores = self.track_ball_movement(frames)
            
            # Audio analysis
            times, rms, spectral_centroid, zcr = self.analyze_audio(video_path)
            audio_events = self.detect_audio_events(times, rms, spectral_centroid, zcr)
            
            # Calculate highlight scores
            highlights = self.calculate_highlight_scores(motion_scores, movement_scores, audio_events, timestamps)
            
            # Adjust sensitivity
            if sensitivity == 'low':
                highlights = [h for h in highlights if h['score'] > 40]
            elif sensitivity == 'high':
                highlights = [h for h in highlights if h['score'] > 15]
            
            # Limit total duration
            total_duration = 0
            filtered_highlights = []
            for highlight in highlights:
                if total_duration + highlight['duration'] <= max_duration:
                    filtered_highlights.append(highlight)
                    total_duration += highlight['duration']
                else:
                    break
            
            # Generate compiled highlight video
            highlight_video_path = None
            if filtered_highlights:
                highlight_video_path = os.path.join(OUTPUT_FOLDER, f"highlights_{uuid.uuid4().hex}.mp4")
                compilation_success = self.compile_highlight_video(video_path, filtered_highlights, highlight_video_path)
                
                if not compilation_success:
                    highlight_video_path = None
            
            return {
                'highlights': filtered_highlights,
                'total_highlights': len(filtered_highlights),
                'total_duration': total_duration,
                'highlight_video_path': highlight_video_path,
                'analysis_stats': {
                    'motion_events': len([s for s in motion_scores if s > 10]),
                    'audio_peaks': len(audio_events),
                    'ball_tracking_accuracy': len([p for p in ball_positions if p is not None]) / len(ball_positions) * 100
                }
            }
            
        except Exception as e:
            print(f"Error generating highlights: {e}")
            return {'error': str(e)}

# Initialize the generator
generator = SportsHighlightGenerator()

# Authentication Routes
@app.route('/api/register', methods=['POST'])
def register():
    """Register a new user"""
    try:
        data = request.get_json()
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')

        if not username or not email or not password:
            return jsonify({'error': 'All fields are required'}), 400

        # Check if user already exists
        if User.query.filter_by(username=username).first():
            return jsonify({'error': 'Username already exists'}), 400
        
        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Email already exists'}), 400

        # Create new user
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        login_user(user)
        return jsonify({
            'message': 'User registered successfully',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email
            }
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login():
    """Login user"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({'error': 'Username and password are required'}), 400

        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            return jsonify({
                'message': 'Login successful',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email
                }
            })
        else:
            return jsonify({'error': 'Invalid username or password'}), 401

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/logout', methods=['POST'])
@login_required
def logout():
    """Logout user"""
    logout_user()
    return jsonify({'message': 'Logout successful'})

@app.route('/api/user', methods=['GET'])
@login_required
def get_current_user():
    """Get current user info"""
    return jsonify({
        'user': {
            'id': current_user.id,
            'username': current_user.username,
            'email': current_user.email
        }
    })

@app.route('/api/history', methods=['GET'])
@login_required
def get_user_history():
    """Get user's video history"""
    try:
        videos = VideoHistory.query.filter_by(user_id=current_user.id).order_by(VideoHistory.created_at.desc()).all()
        
        history = []
        for video in videos:
            stats = json.loads(video.analysis_stats) if video.analysis_stats else {}
            history.append({
                'id': video.id,
                'original_filename': video.original_filename,
                'highlight_filename': video.highlight_filename,
                'sport_type': video.sport_type,
                'sensitivity': video.sensitivity,
                'duration': video.duration,
                'highlight_count': video.highlight_count,
                'analysis_stats': stats,
                'created_at': video.created_at.isoformat()
            })
        
        return jsonify({'history': history})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/upload', methods=['POST'])
def upload_video():
    """Handle video upload"""
    if 'video' not in request.files:
        return jsonify({'error': 'No video file provided'}), 400
    
    file = request.files['video']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and generator.allowed_file(file.filename):
        filename = f"{uuid.uuid4()}_{file.filename}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        return jsonify({
            'message': 'Video uploaded successfully',
            'filename': filename,
            'filepath': filepath
        })
    
    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/api/generate-highlights', methods=['POST'])
def generate_highlights():
    """Generate highlights from uploaded video"""
    data = request.get_json()
    
    if not data or 'filename' not in data:
        return jsonify({'error': 'No filename provided'}), 400
    
    filename = data['filename']
    sport_type = data.get('sport_type', 'general')
    sensitivity = data.get('sensitivity', 'medium')
    max_duration = data.get('max_duration', 30)
    
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    
    if not os.path.exists(filepath):
        return jsonify({'error': 'Video file not found'}), 404
    
    try:
        results = generator.generate_highlights(filepath, sport_type, sensitivity, max_duration)
        
        # Save to user history - Skip this part since login is not required
        # We'll just return the results without saving to user history
        if 'error' not in results:
            highlight_filename = None
            if results.get('highlight_video_path'):
                highlight_filename = os.path.basename(results['highlight_video_path'])
            
            # Skip saving to database since we don't have current_user
            # This avoids the error when no user is logged in
        
        return jsonify(results)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stream-highlights/<path:filename>', methods=['GET'])
def stream_highlights(filename):
    """Stream compiled highlight video for playback"""
    try:
        # Remove 'outputs/' prefix if present
        if filename.startswith('outputs/'):
            filename = filename[8:]  # Remove 'outputs/' prefix
        
        # Always look in the outputs folder
        file_path = os.path.join(OUTPUT_FOLDER, filename)
        
        print(f"Looking for file: {file_path}")
        print(f"File exists: {os.path.exists(file_path)}")
        
        if os.path.exists(file_path):
            return send_file(file_path, mimetype='video/mp4')
        else:
            print(f"File not found: {file_path}")
            # List files in outputs directory for debugging
            try:
                files = os.listdir(OUTPUT_FOLDER)
                print(f"Files in outputs directory: {files}")
            except:
                print("Could not list outputs directory")
            return jsonify({'error': f'Highlight video not found: {file_path}'}), 404
    except Exception as e:
        print(f"Streaming error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/download-highlights/<path:filename>', methods=['GET'])
def download_highlights(filename):
    """Download compiled highlight video"""
    try:
        # Remove 'outputs/' prefix if present
        if filename.startswith('outputs/'):
            filename = filename[8:]  # Remove 'outputs/' prefix
        
        file_path = os.path.join(OUTPUT_FOLDER, filename)
        
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True, download_name=f'highlights_{filename}')
        else:
            print(f"File not found: {file_path}")
            return jsonify({'error': f'Highlight video not found: {file_path}'}), 404
    except Exception as e:
        print(f"Download error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    with app.app_context():
        # This will create the database tables if they don't exist
        db.create_all()
    
    # Use waitress.serve() for production deployment (Windows friendly)
    print("--- Starting production server with Waitress ---")
    # Setting host='0.0.0.0' makes it externally accessible on your network
    # For production, you typically set debug=False, but leaving it True for now to catch any initial errors
    serve(app, host='0.0.0.0', port=5000)