# 🏆 Automated Sports Highlights Generator

An AI-powered system that automatically generates sports highlights using computer vision and audio analysis techniques.

## 🚀 Features

- **Computer Vision Analysis**: Motion detection and object tracking
- **Audio Intelligence**: Volume spike detection and frequency analysis  
- **Multi-Sport Support**: Soccer, Basketball, Tennis, and General Sports
- **Real-time Processing**: Fast highlight generation with progress tracking
- **Modern UI**: Beautiful, responsive web interface
- **Customizable Settings**: Adjustable sensitivity and duration limits

## 🛠️ Technology Stack

### Backend
- **Python 3.8+**
- **Flask**: Web framework
- **OpenCV**: Computer vision processing
- **Librosa**: Audio analysis
- **MoviePy**: Video processing
- **NumPy/SciPy**: Numerical computations
- **Scikit-learn**: Machine learning utilities

### Frontend
- **HTML5/CSS3**: Modern responsive design
- **JavaScript**: Interactive functionality
- **Tailwind CSS**: Utility-first styling
- **Vanilla JS**: No framework dependencies

## 📦 Installation

1. **Clone or download the project**
   ```bash
   # If using git
   git clone <repository-url>
   cd sports-highlights-generator
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**
   ```bash
   python run.py
   ```

4. **Open your browser**
   - Navigate to `http://localhost:5000` for the API
   - Open `code1.js` in your browser for the frontend

## 🎯 How It Works

### 1. Computer Vision Analysis
- **Motion Detection**: Analyzes frame differences to identify high-action moments
- **Object Tracking**: Uses color-based detection to track balls and key objects
- **Movement Analysis**: Calculates velocity and trajectory patterns

### 2. Audio Analysis
- **Volume Spike Detection**: Identifies crowd reactions and commentary excitement
- **Frequency Analysis**: Detects high-frequency content indicating excitement
- **Activity Detection**: Analyzes zero-crossing rates for noise patterns

### 3. Highlight Scoring
- **Multi-modal Fusion**: Combines video and audio scores
- **Temporal Analysis**: Analyzes patterns over time windows
- **Ranking System**: Sorts segments by highlight potential

## 🎮 Usage

1. **Upload Video**: Drag and drop or select a sports video file
2. **Configure Settings**: Choose sport type, duration, and sensitivity
3. **Generate Highlights**: Click "Generate Highlights" to start AI analysis
4. **Review Results**: Browse detected highlights with scores and timestamps
5. **Preview Segments**: Click "Preview" to watch specific highlight moments

## ⚙️ Configuration

### Sport Types
- **Soccer/Football**: Optimized for ball tracking and goal detection
- **Basketball**: Focuses on fast-paced action and scoring plays
- **Tennis**: Emphasizes ball movement and court coverage
- **General Sports**: Universal settings for any sport

### Sensitivity Levels
- **Low**: Only detects very obvious highlights (high threshold)
- **Medium**: Balanced detection (recommended)
- **High**: Captures more subtle moments (low threshold)

### Duration Settings
- **10-60 seconds**: Maximum total highlight duration
- **5-second segments**: Default analysis window size

## 🔧 API Endpoints

### Upload Video
```http
POST /api/upload
Content-Type: multipart/form-data

Body: video file
```

### Generate Highlights
```http
POST /api/generate-highlights
Content-Type: application/json

{
  "filename": "video.mp4",
  "sport_type": "soccer",
  "sensitivity": "medium",
  "max_duration": 30
}
```

### Health Check
```http
GET /api/health
```

## 📊 Algorithm Details

### Motion Score Calculation
```python
motion_score = (changed_pixels / total_pixels) * 100
```

### Audio Event Detection
```python
audio_score = volume_weight * volume_spike + 
              frequency_weight * high_freq + 
              activity_weight * high_activity
```

### Combined Highlight Score
```python
highlight_score = 0.4 * motion_score + 
                  0.3 * movement_score + 
                  0.3 * audio_score
```

## 🎯 Supported Video Formats

- **MP4** (recommended)
- **AVI**
- **MOV**
- **MKV**
- **WebM**

## 📈 Performance Tips

1. **Video Quality**: Higher resolution videos provide better analysis
2. **Audio Quality**: Clear audio improves highlight detection accuracy
3. **Video Length**: Shorter videos (5-15 minutes) process faster
4. **File Size**: Keep videos under 500MB for optimal performance

## 🐛 Troubleshooting

### Common Issues

1. **"No highlights found"**
   - Try increasing sensitivity
   - Check if video has clear audio
   - Ensure video contains action sequences

2. **Slow processing**
   - Reduce video resolution
   - Use shorter video clips
   - Close other applications

3. **Audio analysis errors**
   - Ensure video has audio track
   - Check audio format compatibility

### Error Messages

- **"Failed to upload video"**: Check file format and size
- **"Video file not found"**: Ensure file was uploaded successfully
- **"Audio analysis error"**: Video may lack audio track

## 🔮 Future Enhancements

- **Deep Learning Models**: Integration with pre-trained action recognition models
- **Real-time Processing**: Live video stream analysis
- **Export Features**: Video compilation and sharing
- **Cloud Integration**: Scalable processing with cloud services
- **Mobile Support**: Responsive mobile interface

## 📝 Project Structure

```
sports-highlights-generator/
├── app.py                 # Flask backend server
├── code1.js              # Frontend HTML/CSS/JS
├── requirements.txt       # Python dependencies
├── run.py                # Startup script
├── README.md             # This file
├── uploads/              # Uploaded video files
└── outputs/              # Generated highlights
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is open source and available under the MIT License.

## 🙏 Acknowledgments

- OpenCV community for computer vision tools
- Librosa team for audio processing
- Flask developers for the web framework
- Tailwind CSS for the styling framework

---

**Built with ❤️ for sports enthusiasts and AI researchers**
