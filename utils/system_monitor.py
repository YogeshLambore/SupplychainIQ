import psutil
import platform
import os

def get_system_stats():
    """Returns basic CPU and RAM stats."""
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        ram = psutil.virtual_memory()
        ram_total_gb = ram.total / (1024**3)
        ram_used_gb = ram.used / (1024**3)
        ram_percent = ram.percent
        
        # Try to detect GPU (basic fallback, real implementation would use pynvml or torch)
        vram_status = "N/A"
        gpu_detected = False
        try:
            import torch
            if torch.cuda.is_available():
                gpu_detected = True
                # Simple approximation for demo if pynvml is not used
                vram_status = f"{torch.cuda.memory_allocated(0)/(1024**3):.1f} / {torch.cuda.get_device_properties(0).total_memory/(1024**3):.1f} GB"
        except ImportError:
            pass
            
        return {
            "os": platform.system(),
            "cpu_percent": cpu_percent,
            "ram_used_gb": ram_used_gb,
            "ram_total_gb": ram_total_gb,
            "ram_percent": ram_percent,
            "gpu_detected": gpu_detected,
            "vram_status": vram_status,
            "is_docker": os.path.exists('/.dockerenv')
        }
    except Exception as e:
        return {
            "error": str(e)
        }
