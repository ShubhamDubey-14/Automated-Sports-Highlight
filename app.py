from flask import Flask, request, jsonify, send_file, session
from flask_cors import CORS
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
import os
import cv2
import numpy as np
import librosa
try:
    import moviepy.editor as mp
except ImportError:
    import moviepy as mp
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
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 * 1024  # 16 GB max upload limit

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
        """Extract frames from video at specified FPS using optimized seeking"""
        cap = cv2.VideoCapture(video_path)
        frames = []
        timestamps = []
        
        fps_original = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # Guard against invalid FPS values from the video metadata
        try:
            if not fps_original or fps_original <= 0 or np.isnan(fps_original):
                fps_original = float(fps)
        except Exception:
            fps_original = float(fps)
            
        # Ensure we never compute a zero frame interval
        frame_interval = max(1, int(round(fps_original / float(fps))))
        
        if total_frames > 0:
            for idx in range(0, total_frames, frame_interval):
                cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                ret, frame = cap.read()
                if not ret:
                    break
                frames.append(frame)
                timestamps.append(idx / fps_original)
        else:
            # Fallback to sequential read if total_frames is unavailable
            frame_count = 0
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
        if not frames:
            print("DEBUG: Motion input frames is empty")
            return []
            
        # First frame has no previous frame, pad with 0.0 to align length
        motion_scores.append(0.0)
        
        for i in range(1, len(frames)):
            # Convert to grayscale
            gray1 = cv2.cvtColor(frames[i-1], cv2.COLOR_BGR2GRAY)
            gray2 = cv2.cvtColor(frames[i], cv2.COLOR_BGR2GRAY)
            
            # Calculate frame difference
            diff = cv2.absdiff(gray1, gray2)
            
            # Calculate motion score as percentage of changed pixels
            motion_score = np.sum(diff > 30) / (diff.shape[0] * diff.shape[1]) * 100
            motion_scores.append(motion_score)
        
        print(f"DEBUG: Motion frames input length: {len(frames)}")
        print(f"DEBUG: Motion scores output length: {len(motion_scores)}")
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
        
        if not ball_positions:
            print("DEBUG: Ball positions input is empty")
            return [], []
            
        # First frame has no previous frame, pad with 0.0 to align length
        movement_scores.append(0.0)
        
        # Calculate movement scores
        for i in range(1, len(ball_positions)):
            if ball_positions[i] and ball_positions[i-1]:
                dx = ball_positions[i][0] - ball_positions[i-1][0]
                dy = ball_positions[i][1] - ball_positions[i-1][1]
                movement = np.sqrt(dx*dx + dy*dy)
                movement_scores.append(movement)
            else:
                movement_scores.append(0.0)
        
        print(f"DEBUG: Ball positions length: {len(ball_positions)}")
        print(f"DEBUG: Movement scores length: {len(movement_scores)}")
        return ball_positions, movement_scores
    
    def analyze_audio(self, video_path):
        """Analyze audio for volume spikes and frequency patterns"""
        try:
            # Extract audio from video
            video = mp.VideoFileClip(video_path)
            audio = video.audio
            
            if audio is None:
                return [], [], [], []
            
            # Save audio temporarily
            temp_audio_path = tempfile.mktemp(suffix='.wav')
            try:
                audio.write_audiofile(temp_audio_path, verbose=False, logger=None)
            except TypeError:
                audio.write_audiofile(temp_audio_path, logger=None)
            
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
            print("DEBUG: Input rms array is empty")
            return []
        
        # Normalize RMS values safely
        rms_min = np.min(rms)
        rms_max = np.max(rms)
        rms_diff = rms_max - rms_min
        if rms_diff == 0:
            rms_normalized = np.zeros_like(rms)
        else:
            rms_normalized = (rms - rms_min) / rms_diff
        
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
        print(f"DEBUG: Input times length: {len(times)}, rms length: {len(rms)}")
        print(f"DEBUG: Audio events output length: {len(audio_events)}")
        return audio_events
    
    def calculate_highlight_scores(self, motion_scores, movement_scores, audio_events, timestamps, sensitivity='medium', sport_type='general', times=None, rms=None, spectral_centroid=None):
        """Calculate combined highlight scores for each time segment with sport-specific event rules"""
        highlight_segments = []
        
        # Normalize RMS values safely to [0, 1] range so that audio thresholds work consistently
        rms_normalized = None
        if rms is not None and len(rms) > 0:
            rms_min = np.min(rms)
            rms_max = np.max(rms)
            rms_diff = rms_max - rms_min
            if rms_diff == 0:
                rms_normalized = np.zeros_like(rms)
            else:
                rms_normalized = (rms - rms_min) / rms_diff

        # Create time segments (5-second windows)
        segment_duration = 5.0
        max_time = max(timestamps) if timestamps else 0
        
        for start_time in np.arange(0, max_time, segment_duration):
            end_time = min(start_time + segment_duration, max_time)
            if end_time <= start_time:
                continue
            
            # Find motion and ball movement scores in this segment
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
            
            # Find raw audio values in this segment for fine-tuned event classification
            segment_rms = []
            segment_centroid = []
            if times is not None and rms_normalized is not None and len(rms_normalized) > 0:
                for idx, t in enumerate(times):
                    if start_time <= t < end_time:
                        if idx < len(rms_normalized):
                            segment_rms.append(rms_normalized[idx])
                        if spectral_centroid is not None and idx < len(spectral_centroid):
                            segment_centroid.append(spectral_centroid[idx])
            
            # Calculate segment score using basic mathematical means
            motion_score = np.mean(segment_motion) if segment_motion else 0.0
            movement_score = np.mean(segment_movement) if segment_movement else 0.0
            audio_score = np.mean(segment_audio) if segment_audio else 0.0
            
            # Weighted combination
            total_score = (motion_score * 0.4 + movement_score * 0.3 + audio_score * 0.3)
            
            # Apply cricket heuristics if sport_type is cricket
            cricket_triggers = []
            if sport_type == 'cricket':
                classification = self._classify_cricket_events(segment_motion, segment_movement, segment_audio, segment_rms, segment_centroid)
                total_score += classification['boost']
                cricket_triggers = classification['triggers']
            
            segment_triggers = self._get_triggers(motion_score, movement_score, audio_score)
            if cricket_triggers:
                segment_triggers.extend(cricket_triggers)
                segment_triggers = list(set(segment_triggers)) # Keep triggers unique
            
            highlight_segments.append({
                'start_time': start_time,
                'end_time': end_time,
                'duration': end_time - start_time,
                'score': total_score,
                'motion_score': motion_score,
                'movement_score': movement_score,
                'audio_score': audio_score,
                'triggers': segment_triggers
            })
        
        # Apply global cricket temporal fine-tuning post-processor pass
        if sport_type == 'cricket':
            self._fine_tune_cricket_highlights(highlight_segments, rms_normalized, times, spectral_centroid)
        
        # Sort by score descending
        highlight_segments.sort(key=lambda x: x['score'], reverse=True)
        
        # Determine dynamic threshold based on sensitivity
        if sensitivity == 'low':
            threshold = 40.0
        elif sensitivity == 'high':
            threshold = 15.0
        else:  # 'medium'
            threshold = 20.0
            
        # Filter segments based on high-threshold
        high_threshold_segments = [s for s in highlight_segments if s['score'] > threshold]
        
        if high_threshold_segments:
            final_highlights = high_threshold_segments
        else:
            # Fallback calculation using basic mathematical means
            print(f"DEBUG: No highlights found exceeding threshold {threshold} for sensitivity {sensitivity}. Calculating baseline fallback...")
            all_scores = [s['score'] for s in highlight_segments]
            mean_score = np.mean(all_scores) if all_scores else 0.0
            fallback_threshold = max(5.0, min(mean_score, threshold / 2.0))
            
            final_highlights = [s for s in highlight_segments if s['score'] >= fallback_threshold]
            
            # Second-level fallback: any score > 0
            if not final_highlights:
                final_highlights = [s for s in highlight_segments if s['score'] > 0]
            
            # Absolute baseline fallback: return first few segments of the video (even if score is 0)
            if not final_highlights:
                print("DEBUG: All highlight scores are 0. Retaining first 5 segments as fallback.")
                final_highlights = highlight_segments[:5]
                
        print(f"DEBUG: Total generated highlight segments count: {len(final_highlights)}")
        return final_highlights[:10]  # Top 10 highlights

    def _classify_cricket_events(self, segment_motion, segment_movement, segment_audio, segment_rms, segment_centroid):
        """
        Intelligent heuristic classification to identify key cricket events:
        Wickets, Stumpings, Catches, Boundaries (Four/Six), and Dot Balls.
        Returns a dict: {'boost': float, 'triggers': list}
        """
        boost = 0.0
        triggers = []
        
        max_motion = np.max(segment_motion) if segment_motion else 0.0
        max_movement = np.max(segment_movement) if segment_movement else 0.0
        mean_audio = np.mean(segment_audio) if segment_audio else 0.0
        max_rms = np.max(segment_rms) if segment_rms else 0.0
        mean_centroid = np.mean(segment_centroid) if segment_centroid else 0.0
        
        # 1. Wicket / Catch / Stumping Appeal detection
        # Characteristics: High pitch appeal scream (high spectral centroid) + volume spike + motion
        # Lowered thresholds (centroid: 1700 Hz, volume: 0.78 normalized) and increased boost to 85 points to prioritize wickets.
        is_high_frequency = mean_centroid > 1700 if segment_centroid else False
        is_loud = max_rms > 0.78 or mean_audio > 0.4
        is_high_action = max_motion > 12.0
        
        if is_loud and is_high_frequency:
            if is_high_action:
                # Bowler / players celebrating: very high probability of wicket / catch / stumping result!
                boost += 85.0
                triggers.append("Wicket / Dismissal Celebration")
            else:
                # Bowled or appeal without immediate running celebration
                boost += 65.0
                triggers.append("Wicket / Catch Appeal")
                
        # 2. Boundary (Four / Six) detection
        # Characteristics: High ball movement tracking score (traveling fast/far) followed by crowd cheer
        is_fast_ball = max_movement > 30.0
        is_cheer = mean_audio > 0.3
        if is_fast_ball and is_cheer:
            boost += 45.0
            triggers.append("Boundary (Four/Six)")
            
        # 3. Stumping / Run Out Appeal detection
        # Characteristics: Ball is near stumps/keeper (moderate movement) followed by instant volume peak
        if 15.0 < max_movement <= 35.0 and max_rms > 0.6:
            boost += 35.0
            triggers.append("Stumping / Run Out Appeal")
            
        # 4. Crucial Dot Ball / Delivery detection
        # Characteristics: Ball movement tracked (delivery occurs) but absolute audio silence / player reset
        if max_movement > 22.0 and max_rms < 0.25:
            # Bowler delivered a good dot ball, crowd is quiet, batsman beaten
            boost += 30.0
            triggers.append("Crucial Dot Ball")
            
        return {'boost': boost, 'triggers': triggers}
    
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

    def _fine_tune_cricket_highlights(self, segments, rms, times, spectral_centroid):
        """
        Runs a global temporal pass over all 5-second segments to detect cricket sequences:
        - Wickets (looking for the run-up segment preceding a wicket cheer).
        - Sixes/Four boundaries (ball release -> hit -> crowd roar sequence).
        - Milestones/Achievements (prolonged cheers lasting 10-20 seconds).
        - Crucial dot balls (delivery play followed by quietness).
        """
        if segments is None or len(segments) == 0:
            return
            
        print("DEBUG: Running cricket global temporal fine-tuning post-processor pass...")
        
        for i, seg in enumerate(segments):
            start = seg['start_time']
            end = seg['end_time']
            
            # Find raw audio values in this segment
            seg_rms = []
            seg_centroid = []
            if times is not None and rms is not None and len(rms) > 0:
                for idx, t in enumerate(times):
                    if start <= t < end:
                        if idx < len(rms):
                            seg_rms.append(rms[idx])
                        if spectral_centroid is not None and idx < len(spectral_centroid):
                            seg_centroid.append(spectral_centroid[idx])
            
            max_rms = np.max(seg_rms) if seg_rms else 0.0
            mean_rms = np.mean(seg_rms) if seg_rms else 0.0
            mean_centroid = np.mean(seg_centroid) if seg_centroid else 0.0
            max_movement = seg['movement_score']
            max_motion = seg['motion_score']
            mean_audio = seg['audio_score']
            
            # Direct baseline audio boost to ensure crowd roars compete with raw ball tracking values
            if max_rms > 0.70:
                seg['score'] += 100.0

            # 1. Detect Wicket Cheer
            is_wicket_cheer = (max_rms > 0.78 and mean_centroid > 1800 and max_motion > 15.0)
            if is_wicket_cheer:
                seg['score'] += 120.0  # Huge boost for the celebration segment
                seg['triggers'].append("Wicket / Dismissal Celebration")
                
                # Human brain logic: The ball delivery and run-up happen in the PREVIOUS segment!
                # If the celebration is in segment i, let's boost the previous segment (i-1)
                # to make sure the delivery run-up is selected and merged!
                if i > 0:
                    segments[i-1]['score'] += 90.0
                    segments[i-1]['triggers'].append("Wicket Delivery Play")
                    
            # 2. Detect Six / Four Boundary Cheer
            is_cheer = max_rms > 0.65 and mean_rms > 0.30
            if is_cheer:
                seg['score'] += 75.0
                seg['triggers'].append("Boundary (Four/Six)")
                if i > 0:
                    segments[i-1]['score'] += 80.0
                    segments[i-1]['triggers'].append("Boundary Play Build-up")
            
            # 3. Detect Milestone Achievements (Prolonged applause / cheering)
            # If the current, previous, and next segments are all loud
            prev_rms = 0.0
            next_rms = 0.0
            if times is not None and rms is not None and len(rms) > 0:
                if i > 0:
                    p_start = segments[i-1]['start_time']
                    p_end = segments[i-1]['end_time']
                    p_rms_list = [rms[idx] for idx, t in enumerate(times) if p_start <= t < p_end and idx < len(rms)]
                    prev_rms = np.max(p_rms_list) if p_rms_list else 0.0
                if i < len(segments)-1:
                    n_start = segments[i+1]['start_time']
                    n_end = segments[i+1]['end_time']
                    n_rms_list = [rms[idx] for idx, t in enumerate(times) if n_start <= t < n_end and idx < len(rms)]
                    next_rms = np.max(n_rms_list) if n_rms_list else 0.0
            
            if max_rms > 0.78 and prev_rms > 0.55 and next_rms > 0.55:
                seg['score'] += 95.0
                seg['triggers'].append("Milestone Achievement Celebration")
                
            # 4. Crucial Dot Ball / Good Delivery
            # Ball was bowled, but crowd remains quiet
            if max_movement > 22.0 and max_rms < 0.38:
                seg['score'] += 35.0
                seg['triggers'].append("Crucial Dot Ball")
                
        # Clean up and ensure triggers are unique for all segments
        for seg in segments:
            seg['triggers'] = list(set(seg['triggers']))
    
    def compile_highlight_video(self, video_path, highlights, output_path, sport_type='general'):
        """Compile highlights into a single video - Using MoviePy directly"""
        # Skip FFmpeg attempt and go straight to MoviePy which is already installed
        print(f"Using MoviePy for video compilation for sport type: {sport_type}...")
        return self.compile_highlight_video_moviepy(video_path, highlights, output_path, sport_type)
    
    def compile_highlight_video_moviepy(self, video_path, highlights, output_path, sport_type='general'):
        """Optimized MoviePy compilation for faster processing with sport-specific padding and overlap merging"""
        try:
            try:
                from moviepy.editor import VideoFileClip, concatenate_videoclips
            except ImportError:
                from moviepy import VideoFileClip, concatenate_videoclips
            
            print("Using optimized MoviePy processing...")
            # Preserve original video resolution for high quality highlights
            original_video = VideoFileClip(video_path, audio=True)
            video_duration = original_video.duration

            # Define sport-specific margins (shift start back, extend end forward)
            start_offset = 15.0
            end_offset = 8.0
            
            if sport_type == 'cricket':
                start_offset = 15.0  # capture bowler run-up and delivery release
                end_offset = 8.0    # capture follow-through and immediate result
            elif sport_type == 'soccer':
                start_offset = 15.0  # build-up play and pass
                end_offset = 8.0
            elif sport_type == 'basketball':
                start_offset = 15.0
                end_offset = 8.0
            elif sport_type == 'tennis':
                start_offset = 15.0
                end_offset = 8.0

            # Create list of raw padding windows for each highlight based on event triggers
            raw_windows = []
            for highlight in highlights:
                event_time = highlight['start_time']
                
                # Determine event-specific pre-event padding based on triggers
                triggers = highlight.get('triggers', [])
                has_wicket = any("Wicket" in t or "Stumping" in t or "Dismissal" in t for t in triggers)
                has_boundary = any("Boundary" in t for t in triggers)
                
                if has_wicket:
                    pre_padding = 27.0
                elif has_boundary:
                    pre_padding = 20.0
                else:
                    pre_padding = 15.0
                    
                post_padding = 8.0
                
                # Apply padding (event duration is 5s)
                start_time = max(0.0, event_time - pre_padding)
                end_time = min(video_duration, event_time + 5.0 + post_padding)
                
                raw_windows.append({
                    'event_time': event_time,
                    'start_time': start_time,
                    'end_time': end_time,
                    'highlight': highlight
                })
                
            # Sort windows by event_time
            raw_windows.sort(key=lambda x: x['event_time'])
            
            # Group events that occur very close to each other (<= 10.0 seconds) into a single play/segment
            grouped_segments = []
            if raw_windows:
                i = 0
                while i < len(raw_windows):
                    current = raw_windows[i]
                    j = i + 1
                    merged_start = current['start_time']
                    merged_end = current['end_time']
                    merged_events = [current]
                    
                    while j < len(raw_windows):
                        next_win = raw_windows[j]
                        event_gap = next_win['event_time'] - merged_events[-1]['event_time']
                        
                        if event_gap <= 10.0:
                            # Part of the same play/delivery, merge them
                            merged_end = max(merged_end, next_win['end_time'])
                            merged_events.append(next_win)
                            j += 1
                        else:
                            # Unrelated play, do not merge
                            break
                            
                    grouped_segments.append({
                        'events': merged_events,
                        'start_time': merged_start,
                        'end_time': merged_end
                    })
                    i = j
                    
            # Resolve boundary overlaps between consecutive unrelated segments by splitting the difference
            for idx in range(len(grouped_segments) - 1):
                curr_seg = grouped_segments[idx]
                next_seg = grouped_segments[idx + 1]
                
                if curr_seg['end_time'] > next_seg['start_time']:
                    # Calculate midpoint between the event peaks
                    last_event_time = curr_seg['events'][-1]['event_time']
                    first_event_time = next_seg['events'][0]['event_time']
                    midpoint = (last_event_time + first_event_time) / 2.0
                    
                    # Force transition boundary cut at the midpoint to prevent overlaps or double plays
                    curr_seg['end_time'] = midpoint
                    next_seg['start_time'] = midpoint
                    
            # Extract final start and end times for compilation
            merged_segments = [(seg['start_time'], seg['end_time']) for seg in grouped_segments]

            print(f"DEBUG: Merged {len(highlights)} segments into {len(merged_segments)} continuous highlight clips.")
            
            # Extract highlight clips with optimized settings
            highlight_clips = []
            for start_time, end_time in merged_segments:
                if hasattr(original_video, 'subclip'):
                    clip = original_video.subclip(start_time, end_time)
                else:
                    clip = original_video.subclipped(start_time, end_time)
                highlight_clips.append(clip)
            
            if highlight_clips:
                final_video = concatenate_videoclips(highlight_clips)
                try:
                    final_video.write_videofile(
                        output_path,
                        codec='libx264',
                        audio_codec='aac',
                        preset='ultrafast',  # Fastest encoding
                        verbose=False,  # Hide detailed progress for speed
                        threads=8,     # Use more threads for faster processing
                        ffmpeg_params=["-crf", "20", "-tune", "fastdecode", "-movflags", "+faststart"]  # Crisp quality
                    )
                except TypeError:
                    final_video.write_videofile(
                        output_path,
                        codec='libx264',
                        audio_codec='aac',
                        preset='fastest' if hasattr(final_video, 'preset') else 'ultrafast',
                        logger=None,
                        threads=8,     # Use more threads for faster processing
                        ffmpeg_params=["-crf", "20", "-tune", "fastdecode", "-movflags", "+faststart"]  # Crisp quality
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
            highlights = self.calculate_highlight_scores(motion_scores, movement_scores, audio_events, timestamps, sensitivity, sport_type, times, rms, spectral_centroid)
            
            # Remove total duration constraints to include all key plays
            filtered_highlights = highlights
            total_duration = sum(h['duration'] for h in highlights) if highlights else 0
            
            # Sort both custom and best lists chronologically by start_time
            filtered_highlights.sort(key=lambda x: x['start_time'])
            highlights.sort(key=lambda x: x['start_time'])

            # Generate compiled highlight video for Custom selection (slider-limited)
            custom_video_path = None
            if filtered_highlights:
                custom_video_path = os.path.join(OUTPUT_FOLDER, f"highlights_{uuid.uuid4().hex}.mp4")
                compilation_success = self.compile_highlight_video(video_path, filtered_highlights, custom_video_path, sport_type)
                if not compilation_success:
                    custom_video_path = None
            
            # Generate compiled highlight video containing ALL key moments (ignoring duration slider)
            best_video_path = None
            if highlights:
                best_video_path = os.path.join(OUTPUT_FOLDER, f"best_highlights_{uuid.uuid4().hex}.mp4")
                import shutil
                if custom_video_path and os.path.exists(custom_video_path) and filtered_highlights == highlights:
                    try:
                        shutil.copy2(custom_video_path, best_video_path)
                        compilation_success = True
                    except Exception as copy_err:
                        print(f"Warning: could not copy highlight video: {copy_err}")
                        compilation_success = self.compile_highlight_video(video_path, highlights, best_video_path, sport_type)
                else:
                    compilation_success = self.compile_highlight_video(video_path, highlights, best_video_path, sport_type)
                
                if not compilation_success:
                    best_video_path = None
            
            best_duration = sum(h['duration'] for h in highlights) if highlights else 0
            
            return {
                'highlights': filtered_highlights,
                'total_highlights': len(filtered_highlights),
                'total_duration': total_duration,
                'highlight_video_path': custom_video_path,
                'best_highlight_video_path': best_video_path,
                'best_highlights_count': len(highlights),
                'best_total_duration': best_duration,
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

def convert_numpy(obj):
    if isinstance(obj, np.generic):
        return obj.item()
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: convert_numpy(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy(v) for v in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_numpy(v) for v in obj)
    return obj

@app.route('/api/generate-highlights', methods=['POST'])
def generate_highlights():
    """Generate highlights from uploaded video"""
    try:
        data = request.get_json(force=True, silent=True)
        
        if not data or 'filename' not in data:
            return jsonify({'error': 'No filename provided'}), 400
        
        filename = data['filename']
        sport_type = data.get('sport_type', 'general')
        sensitivity = data.get('sensitivity', 'medium')
        max_duration = data.get('max_duration', 3600)
        
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        if not os.path.exists(filepath):
            return jsonify({'error': f'Video file not found: {filename}'}), 404
        
        results = generator.generate_highlights(filepath, sport_type, sensitivity, max_duration)
        
        # Return converted results with numpy types mapped to native python types
        return jsonify(convert_numpy(results))
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/stream-highlights/<path:filename>', methods=['GET'])
def stream_highlights(filename):
    """Stream compiled highlight video for playback"""
    try:
        # Extract the base filename to prevent directory traversal and handle all slash patterns
        filename = os.path.basename(filename)
        
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
        # Extract the base filename to prevent directory traversal and handle all slash patterns
        filename = os.path.basename(filename)
        
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
    
    port = int(os.environ.get("PORT", 5050))
    print(f"--- Starting production server on port {port} with Waitress ---")
    # Setting host='0.0.0.0' makes it externally accessible on your network
    # max_request_body_size allows uploading large video files up to 16 GB
    serve(app, host='0.0.0.0', port=port, channel_timeout=1200, max_request_body_size=17179869184)