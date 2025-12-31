"""Built-in default configurations and presets."""

PREVIEW_SETTINGS = {
    'video': {
        'resolution': (640, 360),
        'framerate': 15,
        'crf': 35,
        'preset': 'ultrafast',
    },
    'audio': {
        'sample_rate': 22050,
        'bitrate': '64k',
    },
}

MASTERING_PRESETS = {
    'streaming': {
        'target_lufs': -14.0,
        'true_peak': -1.0,
        'compressor': {
            'threshold': -18,
            'ratio': 3,
            'attack': 10,
            'release': 100,
        },
        'limiter': {
            'ceiling': -1.0,
        },
        'eq': {
            'low_shelf': {'freq': 80, 'gain': 1.5},
            'high_shelf': {'freq': 12000, 'gain': 0.5},
        },
    },
    'podcast': {
        'target_lufs': -16.0,
        'true_peak': -1.5,
        'compressor': {
            'threshold': -20,
            'ratio': 4,
            'attack': 5,
            'release': 50,
        },
        'de_esser': {
            'frequency': 6000,
            'threshold': -30,
        },
    },
    'broadcast': {
        'target_lufs': -23.0,
        'true_peak': -2.0,
        'compressor': {
            'threshold': -24,
            'ratio': 2,
            'attack': 20,
            'release': 200,
        },
    },
    'music': {
        'target_lufs': -14.0,
        'true_peak': -1.0,
        'compressor': {
            'threshold': -12,
            'ratio': 2,
            'attack': 30,
            'release': 150,
        },
        'limiter': {
            'ceiling': -0.3,
        },
    },
    'voice': {
        'target_lufs': -16.0,
        'true_peak': -1.0,
        'compressor': {
            'threshold': -18,
            'ratio': 3,
            'attack': 5,
            'release': 80,
        },
        'eq': {
            'low_shelf': {'freq': 100, 'gain': -2},  # Reduce low rumble
            'high_shelf': {'freq': 8000, 'gain': 2},  # Add clarity
        },
    },
}

SUPPORTED_FORMATS = {
    'video': {'.mp4', '.mkv', '.mov', '.avi', '.webm', '.m4v'},
    'audio': {'.wav', '.mp3', '.flac', '.aac', '.ogg', '.m4a', '.opus'},
    'image': {'.png', '.jpg', '.jpeg', '.webp', '.tiff', '.bmp', '.gif'},
}

DEFAULT_VIDEO_OUTPUT = {
    'resolution': '1920x1080',
    'framerate': 30,
    'codec': 'libx264',
    'crf': 18,
    'preset': 'medium',
    'pixel_format': 'yuv420p',
}

DEFAULT_AUDIO_OUTPUT = {
    'sample_rate': 48000,
    'channels': 2,
    'codec': 'pcm_s24le',
}
