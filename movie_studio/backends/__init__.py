from .base import Backend, RenderError  # noqa: F401


def get_backend(cfg):
    name = cfg["video"]["backend"]
    if name == "mock":
        from .mock import MockBackend
        return MockBackend(cfg)
    if name == "comfyui":
        from .comfyui import ComfyUIBackend
        return ComfyUIBackend(cfg)
    raise RenderError(f"unknown video backend {name!r} (choose mock or comfyui)")
