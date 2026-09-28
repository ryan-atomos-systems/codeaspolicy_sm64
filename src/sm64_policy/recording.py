"""Lossless rollout frames with no video encoder or imaging dependency."""

import struct
import zlib
from pathlib import Path

from .storage import SCHEMA_VERSION, write_json


def encode_png(width: int, height: int, rgb: bytes) -> bytes:
    if len(rgb) != width * height * 3:
        raise ValueError("RGB buffer size does not match image dimensions")

    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
        )

    stride = width * 3
    scanlines = b"".join(b"\0" + rgb[y : y + stride] for y in range(0, len(rgb), stride))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(scanlines, 1))
        + chunk(b"IEND", b"")
    )


class FrameRecorder:
    def __init__(self, directory: Path, config, initial):
        self.directory = directory
        self.frames: list[dict] = []
        self.metadata = {
            "schema_version": SCHEMA_VERSION,
            "game_fps": 30,
            "frame_skip": config.frame_skip,
            "observation_mode": config.observation_mode
            if config.backend == "native"
            else "synthetic",
            "observation_timing": "after_recorded_action",
            "record_every": config.record_every,
            "initial_observation": initial.to_dict(),
            "frames": self.frames,
            "visual_playback": config.backend == "native" and config.record_every > 0,
        }

    def capture(self, backend, frame: int, *, render: bool = False) -> None:
        if hasattr(backend, "_pixels"):
            image = backend.render() if render else backend._pixels()
            pixels = (image.width, image.height, image.rgb)
        else:
            pixels = backend.pixels()
        if pixels is None:
            return
        folder = self.directory / "frames"
        folder.mkdir(exist_ok=True)
        name = f"frames/{frame:08d}.png"
        (self.directory / name).write_bytes(encode_png(*pixels))
        self.frames.append({"frame": frame, "path": name})

    def finish(self) -> None:
        write_json(self.directory / "rollout.json", self.metadata)
