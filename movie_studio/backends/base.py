class RenderError(RuntimeError):
    pass


class Backend:
    """A renderer turns one Scene into one MP4 clip that has a video stream and an audio stream."""

    name = "base"
    supports_first_frame = False

    def __init__(self, cfg):
        self.cfg = cfg

    def render(self, scene, out_path, first_frame=None):
        """Write the clip to out_path (a Path) and return it. first_frame is a Path or None."""
        raise NotImplementedError
