"""ctypes layouts matching engine/src/pc/{policy_bridge.h,gfx/gfx_pc.h}."""

import ctypes as ct


class Input(ct.Structure):
    _fields_ = [("stick_x", ct.c_int16), ("stick_y", ct.c_int16), ("buttons", ct.c_bool * 3)]


class GameState(ct.Structure):
    # Order is defined by engine/src/pc/gfx/gfx_pc.h (width precedes height).
    _fields_ = [
        ("pixels", ct.POINTER(ct.c_ubyte)),
        ("width", ct.c_int),
        ("height", ct.c_int),
        ("health", ct.c_int),
        ("died", ct.c_int),
    ] + [
        (name, ct.c_float)
        for name in (
            "x",
            "y",
            "z",
            "vx",
            "vy",
            "vz",
            "height_above_ground",
            "partner_x",
            "partner_y",
            "partner_z",
            "partner_vx",
            "partner_vy",
            "partner_vz",
        )
    ]
