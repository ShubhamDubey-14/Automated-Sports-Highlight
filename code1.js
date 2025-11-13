<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sports Highlights Generator</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        body {
            font-family: 'Inter', sans-serif;
        }
        
        .gradient-bg {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        
        .card-hover {
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        
        .card-hover:hover {
            transform: translateY(-4px);
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
        }
        
        .processing-spinner {
            animation: spin 1s linear infinite;
        }
        
        .pulse-dot {
            animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
        }
        
        .slide-in {
            animation: slideIn 0.5s ease-out;
        }
        
        @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: .5; }
        }
        
        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .upload-area {
            background: linear-gradient(145deg, #f8fafc, #e2e8f0);
            border: 2px dashed #cbd5e1;
            transition: all 0.3s ease;
        }
        
        .upload-area:hover {
            border-color: #3b82f6;
            background: linear-gradient(145deg, #eff6ff, #dbeafe);
            transform: scale(1.02);
        }
        
        .upload-area.drag-over {
            border-color: #1d4ed8;
            background: linear-gradient(145deg, #dbeafe, #bfdbfe);
        }
        
        .glass-effect {
            backdrop-filter: blur(10px);
            background: rgba(255, 255, 255, 0.85);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        
        .highlight-card {
            background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
            border: 1px solid #e2e8f0;
            transition: all 0.3s ease;
        }
        
        .highlight-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
            border-color: #3b82f6;
        }
        
        .score-badge {
            background: linear-gradient(135deg, #3b82f6, #1d4ed8);
            box-shadow: 0 4px 15px rgba(59, 130, 246, 0.3);
        }
        
        .trigger-tag {
            background: linear-gradient(135deg, #eff6ff, #dbeafe);
            border: 1px solid #bfdbfe;
            transition: all 0.2s ease;
        }
        
        .trigger-tag:hover {
            background: linear-gradient(135deg, #dbeafe, #bfdbfe);
        }
        
        .btn-primary {
            background: linear-gradient(135deg, #3b82f6, #1d4ed8);
            box-shadow: 0 4px 15px rgba(59, 130, 246, 0.3);
            transition: all 0.3s ease;
        }
        
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(59, 130, 246, 0.4);
        }
        
        .btn-success {
            background: linear-gradient(135deg, #10b981, #059669);
            box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3);
            transition: all 0.3s ease;
        }
        
        .btn-success:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(16, 185, 129, 0.4);
        }
        
        .progress-bar {
            background: linear-gradient(90deg, #3b82f6, #1d4ed8);
            animation: progressFlow 2s ease-in-out infinite;
        }
        
        @keyframes progressFlow {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.7; }
        }
        
        .icon-glow {
            filter: drop-shadow(0 0 8px rgba(59, 130, 246, 0.3));
        }
        
        .section-fade-in {
            animation: fadeInUp 0.6s ease-out;
        }
        
        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .video-container {
            background: linear-gradient(145deg, #000000, #1a1a1a);
            box-shadow: inset 0 0 50px rgba(0, 0, 0, 0.8);
        }
        
        .stats-card {
            background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
            border-left: 4px solid #3b82f6;
        }
    </style>
</head>
<body class="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100">
    <!-- Background Pattern -->
    <div class="absolute inset-0 bg-white bg-opacity-80" style="background-image: url('data:image/svg+xml,%3Csvg width=\'40\' height=\'40\' viewBox=\'0 0 40 40\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cg fill=\'%23f1f5f9\' fill-opacity=\'0.4\' fill-rule=\'evenodd\'%3E%3Cpath d=\'m0 40l40-40h-40z\'/%3E%3Cpath d=\'m40 40v-40h-40z\' fill=\'%23e2e8f0\' fill-opacity=\'0.2\'/%3E%3C/g%3E%3C/svg%3E');"></div>
    
    <div class="relative z-10 min-h-screen p-4">
        <div class="max-w-7xl mx-auto">
            <!-- Header -->
            <div class="text-center mb-12 section-fade-in">
                <div class="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-br from-blue-500 to-purple-600 rounded-2xl mb-6 shadow-2xl">
                    <span class="text-3xl">🏆</span>
                </div>
                <h1 class="text-5xl font-bold bg-gradient-to-r from-blue-600 via-purple-600 to-blue-800 bg-clip-text text-transparent mb-4">
                    Sports Highlights Generator
                </h1>
                <p class="text-xl text-gray-600 max-w-2xl mx-auto leading-relaxed">
                    Transform your sports footage into compelling highlights using advanced AI computer vision and audio analysis
                </p>
            </div>

            <div class="grid lg:grid-cols-12 gap-8">
                <!-- Upload & Settings Panel -->
                <div class="lg:col-span-4 space-y-8">
                    <!-- Upload Section -->
                    <div class="glass-effect rounded-2xl shadow-2xl p-8 card-hover">
                        <div class="flex items-center gap-3 mb-6">
                            <div class="w-10 h-10 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl flex items-center justify-center">
                                <span class="text-white text-lg">📤</span>
                            </div>
                            <h2 class="text-xl font-bold text-gray-800">Upload Video</h2>
                        </div>
                        
                        <div 
                            id="uploadArea"
                            class="upload-area rounded-xl p-8 text-center cursor-pointer"
                        >
                            <div class="text-6xl mb-4 icon-glow">🎥</div>
                            <p class="text-gray-700 mb-2 font-medium text-lg">Drop your sports video here</p>
                            <p class="text-sm text-gray-500 mb-4">or click to browse files</p>
                            <div class="text-xs text-gray-400 bg-gray-100 rounded-lg px-3 py-2 inline-block">
                                Supports MP4, MOV, AVI • Up to 500MB
                            </div>
                            <input
                                type="file"
                                id="videoInput"
                                accept="video/*"
                                class="hidden"
                            />
                        </div>

                        <div id="uploadedInfo" class="mt-6 p-4 bg-gradient-to-r from-green-50 to-emerald-50 rounded-xl border border-green-200 hidden slide-in">
                            <div class="flex items-center gap-3">
                                <div class="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
                                    <span class="text-green-600 text-lg">✅</span>
                                </div>
                                <div>
                                    <p class="font-semibold text-green-800" id="fileName"></p>
                                    <p class="text-sm text-green-600" id="fileSize"></p>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Settings Section -->
                    <div class="glass-effect rounded-2xl shadow-2xl p-8 card-hover">
                        <div class="flex items-center gap-3 mb-6">
                            <div class="w-10 h-10 bg-gradient-to-br from-purple-500 to-pink-600 rounded-xl flex items-center justify-center">
                                <span class="text-white text-lg">⚙️</span>
                            </div>
                            <h2 class="text-xl font-bold text-gray-800">AI Settings</h2>
                        </div>
                        
                        <div class="space-y-6">
                            <div>
                                <label class="block text-sm font-semibold text-gray-700 mb-3">
                                    Sport Type
                                </label>
                                <select id="sportSelect" class="w-full border-2 border-gray-200 rounded-xl px-4 py-3 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all">
                                    <option value="soccer">⚽ Soccer/Football</option>
                                    <option value="basketball">🏀 Basketball</option>
                                    <option value="tennis">🎾 Tennis</option>
                                    <option value="general">🏃‍♂️ General Sports</option>
                                </select>
                            </div>

                            <div>
                                <label class="block text-sm font-semibold text-gray-700 mb-3">
                                    Highlight Duration
                                </label>
                                <div class="relative">
                                    <input
                                        type="range"
                                        id="lengthSlider"
                                        min="10"
                                        max="60"
                                        value="30"
                                        class="w-full h-3 bg-gradient-to-r from-blue-200 to-purple-200 rounded-lg appearance-none cursor-pointer"
                                    />
                                    <div class="flex justify-between text-xs text-gray-500 mt-2">
                                        <span>10s</span>
                                        <span>60s</span>
                                    </div>
                                </div>
                                <div class="text-center mt-3">
                                    <span class="text-lg font-bold text-blue-600" id="lengthValue">30 seconds</span>
                                </div>
                            </div>

                            <div>
                                <label class="block text-sm font-semibold text-gray-700 mb-3">
                                    Detection Sensitivity
                                </label>
                                <div class="grid grid-cols-3 gap-2">
                                    <button class="sensitivity-btn px-4 py-3 text-sm font-medium rounded-xl border-2 border-gray-200 text-gray-600 hover:border-blue-300 hover:text-blue-600 transition-all" data-level="low">
                                        🟢 Low
                                    </button>
                                    <button class="sensitivity-btn px-4 py-3 text-sm font-medium rounded-xl bg-gradient-to-r from-blue-500 to-indigo-600 text-white border-2 border-blue-500" data-level="medium">
                                        🟡 Medium
                                    </button>
                                    <button class="sensitivity-btn px-4 py-3 text-sm font-medium rounded-xl border-2 border-gray-200 text-gray-600 hover:border-blue-300 hover:text-blue-600 transition-all" data-level="high">
                                        🔴 High
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Main Content Area -->
                <div class="lg:col-span-8 space-y-8">
                    <!-- Video Preview -->
                    <div id="videoPreview" class="glass-effect rounded-2xl shadow-2xl p-8 hidden section-fade-in">
                        <h2 class="text-2xl font-bold text-gray-800 mb-6 flex items-center gap-3">
                            <span class="text-2xl">🎬</span>
                            Video Preview
                        </h2>
                        <div class="video-container rounded-2xl aspect-video flex items-center justify-center overflow-hidden">
                            <video
                                id="previewVideo"
                                controls
                                class="w-full h-full rounded-2xl"
                            >
                                Your browser does not support the video tag.
                            </video>
                        </div>
                        
                        <div class="mt-8 flex gap-4">
                            <button
                                id="generateBtn"
                                class="btn-primary flex items-center gap-3 text-white px-8 py-4 rounded-xl font-semibold text-lg disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                <span class="text-xl">⚡</span>
                                Generate Highlights
                            </button>
                            <button class="flex items-center gap-3 bg-gray-100 text-gray-700 px-6 py-4 rounded-xl font-medium hover:bg-gray-200 transition-all">
                                <span class="text-lg">🔧</span>
                                Advanced Settings
                            </button>
                        </div>
                    </div>

                    <!-- Processing Status -->
                    <div id="processingStatus" class="glass-effect rounded-2xl shadow-2xl p-8 hidden section-fade-in">
                        <h2 class="text-2xl font-bold text-gray-800 mb-6 flex items-center gap-3">
                            <div class="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full processing-spinner"></div>
                            AI Analysis in Progress
                        </h2>
                        
                        <div class="space-y-6">
                            <div class="grid md:grid-cols-3 gap-4">
                                <div class="flex items-center gap-4 p-4 bg-blue-50 rounded-xl">
                                    <div class="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center">
                                        <span class="text-2xl">👁️</span>
                                    </div>
                                    <div>
                                        <h3 class="font-semibold text-blue-800">Computer Vision</h3>
                                        <p class="text-sm text-blue-600">Motion & Object Detection</p>
                                    </div>
                                </div>
                                <div class="flex items-center gap-4 p-4 bg-green-50 rounded-xl">
                                    <div class="w-12 h-12 bg-green-100 rounded-xl flex items-center justify-center">
                                        <span class="text-2xl">🔊</span>
                                    </div>
                                    <div>
                                        <h3 class="font-semibold text-green-800">Audio Analysis</h3>
                                        <p class="text-sm text-green-600">Volume & Frequency</p>
                                    </div>
                                </div>
                                <div class="flex items-center gap-4 p-4 bg-purple-50 rounded-xl">
                                    <div class="w-12 h-12 bg-purple-100 rounded-xl flex items-center justify-center">
                                        <span class="text-2xl">⏰</span>
                                    </div>
                                    <div>
                                        <h3 class="font-semibold text-purple-800">Pattern Recognition</h3>
                                        <p class="text-sm text-purple-600">Temporal Analysis</p>
                                    </div>
                                </div>
                            </div>
                            
                            <div class="bg-gradient-to-r from-gray-50 to-gray-100 rounded-xl p-6">
                                <div class="flex items-center gap-4 mb-3">
                                    <div class="pulse-dot w-3 h-3 bg-blue-500 rounded-full"></div>
                                    <span class="font-semibold text-gray-700">Current Stage:</span>
                                </div>
                                <p class="text-lg text-gray-800" id="processingStage">Initializing AI models...</p>
                                <div class="mt-4 h-2 bg-gray-200 rounded-full overflow-hidden">
                                    <div class="progress-bar h-full rounded-full" style="width: 0%"></div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Generated Highlights -->
                    <div id="highlightsSection" class="glass-effect rounded-2xl shadow-2xl p-8 hidden section-fade-in">
                        <div class="flex items-center justify-between mb-8">
                            <h2 class="text-2xl font-bold text-gray-800 flex items-center gap-3">
                                <span class="text-2xl">✨</span>
                                Generated Highlights (<span id="highlightCount" class="text-blue-600">0</span>)
                            </h2>
                            <button class="btn-success flex items-center gap-3 text-white px-6 py-3 rounded-xl font-semibold">
                                <span class="text-lg">💾</span>
                                Export All
                            </button>
                        </div>
                        
                        <div id="highlightsList" class="space-y-6">
                            <!-- Highlights will be inserted here -->
                        </div>

                        <div class="mt-8 stats-card rounded-xl p-6">
                            <h3 class="font-bold text-blue-900 mb-4 text-lg flex items-center gap-2">
                                <span>📊</span>
                                Analysis Summary
                            </h3>
                            <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                                <div class="text-center">
                                    <div class="text-3xl font-bold text-blue-600 mb-1">47</div>
                                    <div class="text-sm text-blue-700 font-medium">Motion Events</div>
                                </div>
                                <div class="text-center">
                                    <div class="text-3xl font-bold text-green-600 mb-1">23</div>
                                    <div class="text-sm text-green-700 font-medium">Audio Peaks</div>
                                </div>
                                <div class="text-center">
                                    <div class="text-3xl font-bold text-purple-600 mb-1">89%</div>
                                    <div class="text-sm text-purple-700 font-medium">Ball Tracking</div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Getting Started Guide -->
                    <div id="gettingStarted" class="glass-effect rounded-2xl shadow-2xl p-8 section-fade-in">
                        <h2 class="text-2xl font-bold text-gray-800 mb-6 flex items-center gap-3">
                            <span class="text-2xl">🚀</span>
                            How Our AI Works
                        </h2>
                        <div class="grid md:grid-cols-2 gap-6">
                            <div class="highlight-card rounded-xl p-6">
                                <div class="w-16 h-16 bg-gradient-to-br from-blue-100 to-blue-200 rounded-2xl flex items-center justify-center mb-4">
                                    <span class="text-3xl">👁️</span>
                                </div>
                                <h3 class="text-xl font-bold text-gray-800 mb-3">Computer Vision</h3>
                                <p class="text-gray-600 leading-relaxed">
                                    Advanced motion detection and object tracking algorithms identify high-action moments by analyzing player movements, ball trajectory, and scene dynamics in real-time.
                                </p>
                            </div>
                            <div class="highlight-card rounded-xl p-6">
                                <div class="w-16 h-16 bg-gradient-to-br from-green-100 to-green-200 rounded-2xl flex items-center justify-center mb-4">
                                    <span class="text-3xl">🔊</span>
                                </div>
                                <h3 class="text-xl font-bold text-gray-800 mb-3">Audio Intelligence</h3>
                                <p class="text-gray-600 leading-relaxed">
                                    Sophisticated audio analysis detects crowd reactions, commentary excitement, and volume spikes to identify emotionally significant moments that correlate with highlights.
                                </p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let uploadedVideo = null;
        let currentSensitivity = 'medium';
        let currentProgress = 0;

        // Upload functionality with drag and drop
        const uploadArea = document.getElementById('uploadArea');
        
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, preventDefaults, false);
        });

        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }

        ['dragenter', 'dragover'].forEach(eventName => {
            uploadArea.addEventListener(eventName, highlight, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, unhighlight, false);
        });

        function highlight(e) {
            uploadArea.classList.add('drag-over');
        }

        function unhighlight(e) {
            uploadArea.classList.remove('drag-over');
        }

        uploadArea.addEventListener('drop', handleDrop, false);

        function handleDrop(e) {
            const dt = e.dataTransfer;
            const files = dt.files;
            handleFiles(files);
        }

        uploadArea.addEventListener('click', () => {
            document.getElementById('videoInput').click();
        });

        document.getElementById('videoInput').addEventListener('change', (event) => {
            handleFiles(event.target.files);
        });

        function handleFiles(files) {
            const file = files[0];
            if (file && file.type.startsWith('video/')) {
                const videoURL = URL.createObjectURL(file);
                uploadedVideo = {
                    file: file,
                    url: videoURL,
                    name: file.name,
                    size: (file.size / (1024 * 1024)).toFixed(2) + ' MB'
                };

                // Update UI with animation
                document.getElementById('fileName').textContent = uploadedVideo.name;
                document.getElementById('fileSize').textContent = uploadedVideo.size;
                document.getElementById('uploadedInfo').classList.remove('hidden');
                document.getElementById('previewVideo').src = videoURL;
                document.getElementById('videoPreview').classList.remove('hidden');
                document.getElementById('gettingStarted').classList.add('hidden');
                document.getElementById('highlightsSection').classList.add('hidden');
                
                // Smooth scroll to preview
                setTimeout(() => {
                    document.getElementById('videoPreview').scrollIntoView({ 
                        behavior: 'smooth', 
                        block: 'center' 
                    });
                }, 300);
            }
        }

        // Settings functionality
        document.getElementById('lengthSlider').addEventListener('input', (e) => {
            document.getElementById('lengthValue').textContent = e.target.value + ' seconds';
        });

        document.querySelectorAll('.sensitivity-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('.sensitivity-btn').forEach(b => {
                    b.className = 'sensitivity-btn px-4 py-3 text-sm font-medium rounded-xl border-2 border-gray-200 text-gray-600 hover:border-blue-300 hover:text-blue-600 transition-all';
                });
                e.target.className = 'sensitivity-btn px-4 py-3 text-sm font-medium rounded-xl bg-gradient-to-r from-blue-500 to-indigo-600 text-white border-2 border-blue-500';
                currentSensitivity = e.target.dataset.level;
            });
        });

        // Generate highlights functionality
        document.getElementById('generateBtn').addEventListener('click', async () => {
            if (!uploadedVideo) return;

            document.getElementById('processingStatus').classList.remove('hidden');
            document.getElementById('generateBtn').disabled = true;
            document.getElementById('generateBtn').innerHTML = '<span class="text-xl">⚡</span> Processing...';

            const stages = [
                'Loading video and initializing AI models...',
                'Analyzing motion patterns and object detection...',
                'Processing audio signals and frequency analysis...',
                'Tracking ball movement and player actions...',
                'Calculating highlight scores and rankings...',
                'Generating final highlight compilation...'
            ];

            const progressBar = document.querySelector('.progress-bar');

            try {
                // Upload video to backend
                const formData = new FormData();
                formData.append('video', uploadedVideo.file);

                const uploadResponse = await fetch('http://localhost:5000/api/upload', {
                    method: 'POST',
                    body: formData
                });

                if (!uploadResponse.ok) {
                    throw new Error('Failed to upload video');
                }

                const uploadData = await uploadResponse.json();
                
                // Update progress
                document.getElementById('processingStage').textContent = stages[0];
                progressBar.style.width = '16%';
                await new Promise(resolve => setTimeout(resolve, 1000));

                // Generate highlights
                const generateResponse = await fetch('http://localhost:5000/api/generate-highlights', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        filename: uploadData.filename,
                        sport_type: document.getElementById('sportSelect').value,
                        sensitivity: currentSensitivity,
                        max_duration: parseInt(document.getElementById('lengthSlider').value)
                    })
                });

                if (!generateResponse.ok) {
                    throw new Error('Failed to generate highlights');
                }

                const results = await generateResponse.json();

                // Simulate processing stages
                for (let i = 1; i < stages.length; i++) {
                    document.getElementById('processingStage').textContent = stages[i];
                    const progress = ((i + 1) / stages.length) * 100;
                    progressBar.style.width = progress + '%';
                    await new Promise(resolve => setTimeout(resolve, 1500));
                }

                // Show results with animation
                document.getElementById('processingStatus').classList.add('hidden');
                showHighlights(results);
                
            } catch (error) {
                console.error('Error:', error);
                document.getElementById('processingStage').textContent = 'Error: ' + error.message;
                progressBar.style.width = '100%';
                progressBar.style.background = 'linear-gradient(90deg, #ef4444, #dc2626)';
                
                setTimeout(() => {
                    document.getElementById('processingStatus').classList.add('hidden');
                    alert('Error generating highlights: ' + error.message);
                }, 2000);
            }
            
            document.getElementById('generateBtn').disabled = false;
            document.getElementById('generateBtn').innerHTML = '<span class="text-xl">⚡</span> Generate Highlights';
        });

        function showHighlights(results) {
            const highlights = results.highlights || [];
            const stats = results.analysis_stats || {};

            const highlightsList = document.getElementById('highlightsList');
            highlightsList.innerHTML = '';

            if (highlights.length === 0) {
                highlightsList.innerHTML = `
                    <div class="text-center py-12">
                        <div class="text-6xl mb-4">🔍</div>
                        <h3 class="text-xl font-semibold text-gray-600 mb-2">No Highlights Found</h3>
                        <p class="text-gray-500">Try adjusting the sensitivity settings or upload a different video.</p>
                    </div>
                `;
            } else {
                highlights.forEach((highlight, index) => {
                    const highlightCard = document.createElement('div');
                    highlightCard.className = 'highlight-card rounded-xl p-6 card-hover';
                    highlightCard.style.animationDelay = `${index * 0.1}s`;
                    
                    const startTime = formatTime(highlight.start_time);
                    const duration = highlight.duration.toFixed(1) + 's';
                    const score = Math.round(highlight.score);
                    
                    highlightCard.innerHTML = `
                        <div class="flex items-start gap-6">
                            <div class="relative flex-shrink-0">
                                <div class="w-32 h-20 bg-gradient-to-br from-gray-800 to-gray-900 rounded-lg flex items-center justify-center shadow-lg">
                                    <span class="text-white text-2xl">▶️</span>
                                </div>
                                <div class="score-badge absolute -top-2 -right-2 text-white text-sm font-bold px-3 py-1 rounded-lg">
                                    ${score}
                                </div>
                            </div>
                            <div class="flex-1">
                                <div class="flex items-start justify-between mb-3">
                                    <div>
                                        <h3 class="text-xl font-bold text-gray-800 mb-1">Highlight ${index + 1}</h3>
                                        <p class="text-gray-600 mb-2">Score: ${score.toFixed(1)} | Motion: ${highlight.motion_score.toFixed(1)} | Audio: ${highlight.audio_score.toFixed(2)}</p>
                                        <p class="text-sm text-gray-500 flex items-center gap-2">
                                            <span class="font-medium">⏱️ ${startTime}</span>
                                            <span>•</span>
                                            <span class="font-medium">⏳ ${duration}</span>
                                        </p>
                                    </div>
                                    <button class="btn-primary text-white px-4 py-2 rounded-lg text-sm font-medium hover:scale-105 transition-transform" onclick="previewHighlight(${highlight.start_time}, ${highlight.end_time})">
                                        Preview
                                    </button>
                                </div>
                                <div class="flex flex-wrap gap-2">
                                    ${highlight.triggers.map(trigger => 
                                        `<span class="trigger-tag text-xs text-blue-700 px-3 py-1 rounded-full font-medium">${trigger}</span>`
                                    ).join('')}
                                </div>
                            </div>
                        </div>
                    `;
                    
                    highlightsList.appendChild(highlightCard);
                });
            }

            // Update stats
            document.querySelector('.stats-card .text-3xl.font-bold.text-blue-600').textContent = stats.motion_events || 0;
            document.querySelector('.stats-card .text-3xl.font-bold.text-green-600').textContent = stats.audio_peaks || 0;
            document.querySelector('.stats-card .text-3xl.font-bold.text-purple-600').textContent = Math.round(stats.ball_tracking_accuracy || 0) + '%';

            document.getElementById('highlightCount').textContent = highlights.length;
            document.getElementById('highlightsSection').classList.remove('hidden');
            
            // Smooth scroll to results
            setTimeout(() => {
                document.getElementById('highlightsSection').scrollIntoView({ 
                    behavior: 'smooth', 
                    block: 'start' 
                });
            }, 300);
        }

        function formatTime(seconds) {
            const mins = Math.floor(seconds / 60);
            const secs = Math.floor(seconds % 60);
            return `${mins}:${secs.toString().padStart(2, '0')}`;
        }

        function previewHighlight(startTime, endTime) {
            const video = document.getElementById('previewVideo');
            if (video) {
                video.currentTime = startTime;
                video.play();
                
                // Stop at end time
                const stopAtEnd = () => {
                    if (video.currentTime >= endTime) {
                        video.pause();
                        video.removeEventListener('timeupdate', stopAtEnd);
                    }
                };
                video.addEventListener('timeupdate', stopAtEnd);
            }
        }
    </script>
</body>
</html>