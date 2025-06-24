import os
from pathlib import Path
from typing import List, Optional

class Config:
    """Configuration class for Number Plate Recognition system"""
    
    # Model paths
    checkpoint_path: str = '/checkpoints'
    yolo_weights_file: str = 'checkpoints/best.pt'
    
    # Training parameters
    epochs: int = 20
    batch_size: int = -1  # -1 for auto batch size
    num_class: int = 1
    img_size: int = 640
    
    # OCR Configuration
    ocr_languages: List[str] = ['en', 'vi']
    ocr_confidence_threshold: float = 0.5
    
    # Detection parameters
    detection_confidence: float = 0.25
    detection_iou_threshold: float = 0.45
    max_detections: int = 1000
    
    # Image preprocessing
    gaussian_blur_kernel: tuple = (5, 5)
    gaussian_blur_sigma: int = 0
    
    # Parking lot map
    map_size=(40,40)
    initial_pos = (0,0)
    obstacles= [(1,2),(1,3),(2,4)]
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    allowed_extensions: List[str] = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']
    
    # Logging
    log_level: str = "INFO"
    log_file: Optional[str] = None
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize configuration
        
        Args:
            config_file: Optional path to configuration file
        """
        if config_file:
            self.load_from_file(config_file)
        
        # Validate paths and create directories if needed
        self.validate_and_setup()
    
    def validate_and_setup(self):
        """Validate configuration and create necessary directories"""
        
        # Create checkpoint directory if it doesn't exist
        checkpoint_dir = Path(self.checkpoint_path)
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        # Check if YOLO weights file exists
        if not os.path.exists(self.yolo_weights_file):
            print(f"Warning: YOLO weights file not found at {self.yolo_weights_file}")
            print("You may need to download or train the model first.")
        
        # Validate parameters
        if self.epochs <= 0:
            raise ValueError("epochs must be positive")
        
        if self.num_class <= 0:
            raise ValueError("num_class must be positive")
        
        if self.img_size <= 0:
            raise ValueError("img_size must be positive")
        
        if not (0.0 <= self.detection_confidence <= 1.0):
            raise ValueError("detection_confidence must be between 0.0 and 1.0")
        
        if not (0.0 <= self.detection_iou_threshold <= 1.0):
            raise ValueError("detection_iou_threshold must be between 0.0 and 1.0")
        
        if not (0.0 <= self.ocr_confidence_threshold <= 1.0):
            raise ValueError("ocr_confidence_threshold must be between 0.0 and 1.0")
    
    def load_from_file(self, config_file: str):
        """Load configuration from a file (JSON or Python file)"""
        config_path = Path(config_file)
        
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_file}")
        
        if config_path.suffix == '.json':
            import json
            with open(config_file, 'r') as f:
                config_data = json.load(f)
            
            # Update attributes from JSON
            for key, value in config_data.items():
                if hasattr(self, key):
                    setattr(self, key, value)
        
        elif config_path.suffix == '.py':
            # Import Python config file
            import importlib.util
            spec = importlib.util.spec_from_file_location("config", config_file)
            config_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(config_module)
            
            # Update attributes from Python module
            for attr_name in dir(config_module):
                if not attr_name.startswith('_') and hasattr(self, attr_name):
                    setattr(self, attr_name, getattr(config_module, attr_name))
    
    def save_to_file(self, config_file: str):
        """Save current configuration to a JSON file"""
        import json
        
        config_dict = {}
        for attr_name in dir(self):
            if not attr_name.startswith('_') and not callable(getattr(self, attr_name)):
                config_dict[attr_name] = getattr(self, attr_name)
        
        with open(config_file, 'w') as f:
            json.dump(config_dict, f, indent=2)
    
    def get_yolo_args(self) -> dict:
        """Get arguments for YOLO model initialization"""
        return {
            'conf': self.detection_confidence,
            'iou': self.detection_iou_threshold,
            'max_det': self.max_detections,
            'imgsz': self.img_size
        }
    
    def get_training_args(self) -> dict:
        """Get arguments for model training"""
        return {
            'epochs': self.epochs,
            'batch': self.batch_size,
            'imgsz': self.img_size,
            'data': f'{self.checkpoint_path}/data.yaml'  # Assuming you have a data.yaml file
        }
    
    def __str__(self) -> str:
        """String representation of configuration"""
        config_items = []
        for attr_name in sorted(dir(self)):
            if not attr_name.startswith('_') and not callable(getattr(self, attr_name)):
                value = getattr(self, attr_name)
                config_items.append(f"{attr_name}: {value}")
        
        return "Configuration:\n" + "\n".join(config_items)
    
    @classmethod
    def create_default_config_file(cls, config_file: str = "config.json"):
        """Create a default configuration file"""
        config = cls()
        config.save_to_file(config_file)
        print(f"Default configuration saved to {config_file}")

# Example usage and utility functions
class DevelopmentConfig(Config):
    """Development configuration with different defaults"""
    
    def __init__(self):
        super().__init__()
        self.log_level = "DEBUG"
        self.detection_confidence = 0.1  # Lower threshold for development
        self.epochs = 5  # Fewer epochs for quick testing

class ProductionConfig(Config):
    """Production configuration with optimized defaults"""
    
    def __init__(self):
        super().__init__()
        self.log_level = "WARNING"
        self.detection_confidence = 0.5  # Higher threshold for production
        self.batch_size = 16  # Fixed batch size for consistent performance
        self.max_file_size = 5 * 1024 * 1024  # Smaller file size limit

# Environment-based config loader
def get_config(environment: str = "default") -> Config:
    """
    Get configuration based on environment
    
    Args:
        environment: 'development', 'production', or 'default'
    
    Returns:
        Config instance
    """
    if environment.lower() == "development":
        return DevelopmentConfig()
    elif environment.lower() == "production":
        return ProductionConfig()
    else:
        return Config()

# Usage example
if __name__ == "__main__":
    # Create default config
    config = Config()
    print(config)
    
    # Create and save default config file
    Config.create_default_config_file("default_config.json")
    
    # Load config from environment variable
    env = os.getenv("ENVIRONMENT", "default")
    config = get_config(env)
    print(f"\nLoaded {env} configuration:")
    print(config)