import os
import tempfile
from typing import List, Tuple
from pydub import AudioSegment


def ensure_ffmpeg_installed():
    """
    Check if ffmpeg is installed and available
    """
    import subprocess
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except FileNotFoundError:
        raise RuntimeError(
            "ffmpeg not found. Please install ffmpeg to use this application. "
            "You can install it using: brew install ffmpeg (on macOS) or "
            "apt-get install ffmpeg (on Ubuntu/Debian)"
        )


def load_audio_file(file_path: str) -> AudioSegment:
    """
    Load an audio file using pydub
    """
    ensure_ffmpeg_installed()
    # Try to load the file with the specified format first
    try:
        return AudioSegment.from_file(file_path, format="m4a")
    except Exception as e:
        # If that fails, let pydub try to determine the format automatically
        return AudioSegment.from_file(file_path)


def split_audio_file(audio: AudioSegment, chunk_duration_ms: int = 3 * 60 * 1000) -> List[Tuple[int, int, str]]:
    """
    Split an audio file into chunks of specified duration
    Returns a list of tuples (start_time_ms, end_time_ms, chunk_file_path)
    """
    chunks = []
    length_ms = len(audio)
    
    for i in range(0, length_ms, chunk_duration_ms):
        start_time = i
        end_time = min(i + chunk_duration_ms, length_ms)
        
        # Extract chunk
        chunk = audio[start_time:end_time]
        
        # Optimize audio for OpenAI API
        # 1. Convert to mono (1 channel) if it's stereo
        if chunk.channels > 1:
            chunk = chunk.set_channels(1)
            
        # 2. Downsample to 16kHz (OpenAI recommends this for Whisper)
        chunk = chunk.set_frame_rate(16000)
        
        # 3. Save as MP3 with lower bitrate to reduce file size
        # MP3 is more compressed than WAV but still well-supported
        chunk_path = tempfile.mktemp(suffix=".mp3")
        chunk.export(
            chunk_path, 
            format="mp3",
            bitrate="32k",  # Lower bitrate for smaller file size
            parameters=["-q:a", "2"]  # Higher quality setting (0-9, lower is better)
        )
        
        chunks.append((start_time, end_time, chunk_path))
    
    return chunks


def cleanup_temp_files(file_paths: List[str]):
    """
    Clean up temporary files
    """
    for path in file_paths:
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception as e:
                print(f"Error removing temporary file {path}: {e}")
