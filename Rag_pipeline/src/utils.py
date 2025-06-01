import torch

class HardwareUtils:
    @staticmethod
    def get_device() -> str:
        """Lấy thiết bị phần cứng cho việc tính toán embedding"""
        if torch.cuda.is_available():
            return "cuda"
        if torch.backends.mps.is_available():
            return "mps"
        return "cpu"