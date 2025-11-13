#!/usr/bin/env python3
"""
Test script to verify Sports Highlights Generator installation
"""

def test_imports():
    """Test if all required packages can be imported"""
    print("🧪 Testing package imports...")
    
    try:
        import flask
        print("✅ Flask imported successfully")
    except ImportError:
        print("❌ Flask not found - run: pip install flask")
        return False
    
    try:
        import cv2
        print("✅ OpenCV imported successfully")
    except ImportError:
        print("❌ OpenCV not found - run: pip install opencv-python")
        return False
    
    try:
        import numpy as np
        print("✅ NumPy imported successfully")
    except ImportError:
        print("❌ NumPy not found - run: pip install numpy")
        return False
    
    try:
        import librosa
        print("✅ Librosa imported successfully")
    except ImportError:
        print("❌ Librosa not found - run: pip install librosa")
        return False
    
    try:
        import moviepy.editor as mp
        print("✅ MoviePy imported successfully")
    except ImportError:
        print("❌ MoviePy not found - run: pip install moviepy")
        return False
    
    try:
        import scipy
        print("✅ SciPy imported successfully")
    except ImportError:
        print("❌ SciPy not found - run: pip install scipy")
        return False
    
    try:
        import sklearn
        print("✅ Scikit-learn imported successfully")
    except ImportError:
        print("❌ Scikit-learn not found - run: pip install scikit-learn")
        return False
    
    return True

def test_opencv_functionality():
    """Test basic OpenCV functionality"""
    print("\n🔍 Testing OpenCV functionality...")
    
    try:
        import cv2
        import numpy as np
        
        # Create a test image
        test_image = np.zeros((100, 100, 3), dtype=np.uint8)
        
        # Test basic operations
        gray = cv2.cvtColor(test_image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        print("✅ OpenCV basic operations working")
        return True
    except Exception as e:
        print(f"❌ OpenCV test failed: {e}")
        return False

def test_librosa_functionality():
    """Test basic Librosa functionality"""
    print("\n🔊 Testing Librosa functionality...")
    
    try:
        import librosa
        import numpy as np
        
        # Create test audio signal
        sr = 22050
        duration = 1.0
        t = np.linspace(0, duration, int(sr * duration))
        y = np.sin(2 * np.pi * 440 * t)  # 440 Hz sine wave
        
        # Test basic operations
        rms = librosa.feature.rms(y=y)
        spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
        
        print("✅ Librosa basic operations working")
        return True
    except Exception as e:
        print(f"❌ Librosa test failed: {e}")
        return False

def test_flask_app():
    """Test if Flask app can be imported"""
    print("\n🌐 Testing Flask app...")
    
    try:
        from app import app, generator
        print("✅ Flask app imported successfully")
        print("✅ SportsHighlightGenerator class loaded")
        return True
    except Exception as e:
        print(f"❌ Flask app test failed: {e}")
        return False

def main():
    print("🏆 Sports Highlights Generator - Installation Test")
    print("=" * 55)
    
    all_tests_passed = True
    
    # Test imports
    if not test_imports():
        all_tests_passed = False
    
    # Test OpenCV
    if not test_opencv_functionality():
        all_tests_passed = False
    
    # Test Librosa
    if not test_librosa_functionality():
        all_tests_passed = False
    
    # Test Flask app
    if not test_flask_app():
        all_tests_passed = False
    
    print("\n" + "=" * 55)
    if all_tests_passed:
        print("🎉 All tests passed! Your installation is ready.")
        print("🚀 Run 'python run.py' to start the server")
    else:
        print("❌ Some tests failed. Please check the error messages above.")
        print("💡 Run 'pip install -r requirements.txt' to install missing packages")
    
    return all_tests_passed

if __name__ == "__main__":
    main()
