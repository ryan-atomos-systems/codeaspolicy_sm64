"""Pointer-free oracle ABI and translation to immutable Python records."""

import ctypes as ct

from .state import (
    CameraState,
    GeometryState,
    MarioState,
    NearbyObjects,
    ObjectState,
    ProgressState,
    RaySample,
    SurfaceState,
)

I, U, F = ct.c_int32, ct.c_uint32, ct.c_float
VEC = F * 3
MAX_OBJECTS, RAYS, COURSES = 64, 18, 26


def scalars(names, kind=I):
    return [(name, kind) for name in names.split()]


class Surface(ct.Structure):
    _fields_ = scalars("valid type flags room") + [
        ("object_id", U),
        ("normal", VEC),
        ("vertices", F * 9),
    ]


class Mario(ct.Structure):
    _fields_ = (
        [("face_angle", I * 3), ("angle_velocity", I * 3)]
        + scalars("action previous_action action_arg flags input", U)
        + scalars(
            "action_state action_timer invincibility_timer cap_timer wall_kick_timer double_jump_timer frames_since_a frames_since_b health_raw lives room"
        )
        + scalars("forward_velocity floor_height ceiling_height water_level quicksand_depth", F)
        + scalars("held_object_id ridden_object_id platform_id interacted_object_id", U)
        + [("floor", Surface), ("ceiling", Surface), ("wall", Surface)]
    )


class Camera(ct.Structure):
    _fields_ = scalars("valid mode cutscene yaw roll") + [
        ("position", VEC),
        ("focus", VEC),
        ("fov", F),
    ]


class Object(ct.Structure):
    _fields_ = (
        scalars("id behavior_id behavior_params interaction_type interaction_subtype", U)
        + scalars(
            "active_flags action sub_action timer health damage_or_coin_value move_flags intangible_timer room"
        )
        + [("face_angle", I * 3), ("position", VEC), ("velocity", VEC)]
        + scalars(
            "hitbox_radius hitbox_height hitbox_down_offset hurtbox_radius hurtbox_height distance",
            F,
        )
    )


class Ray(ct.Structure):
    _fields_ = [
        ("origin", VEC),
        ("direction", VEC),
        ("length", F),
        ("distance", F),
        ("position", VEC),
        ("surface", Surface),
    ]


class Progress(ct.Structure):
    _fields_ = scalars(
        "level area act course save_file stars coins lives last_completed_course last_completed_star credits_active"
    ) + [("save_flags", U), ("star_masks", U * COURSES), ("cannon_mask", U)]


class Oracle(ct.Structure):
    _fields_ = (
        scalars("version engine_frame", U)
        + [("mario", Mario), ("camera", Camera), ("progress", Progress)]
        + scalars("object_count objects_in_radius")
        + [("object_radius", F), ("objects", Object * MAX_OBJECTS), ("rays", Ray * RAYS)]
    )


# Actual engine interaction bits, not an exhaustive enemy taxonomy.
AFFORDANCES = (
    (1 << 1, "grabbable"),
    (1 << 2, "door"),
    (1 << 3, "damage"),
    (1 << 4, "coin"),
    (1 << 5, "cap"),
    (1 << 6, "pole"),
    (1 << 9, "breakable"),
    (1 << 11, "warp_door"),
    (1 << 12, "star_or_key"),
    (1 << 13, "warp"),
    (1 << 14, "cannon"),
    (1 << 15, "bounce_top"),
    (1 << 17, "bully"),
    (1 << 18, "flame"),
    (1 << 19, "shell"),
    (1 << 20, "bounce_top"),
    (1 << 23, "dialogue"),
    (1 << 29, "shock"),
)


def surface(value: Surface) -> SurfaceState | None:
    if not value.valid:
        return None
    vertices = tuple(value.vertices)
    return SurfaceState(
        value.type,
        value.flags,
        value.room,
        value.object_id or None,
        tuple(value.normal),
        (vertices[:3], vertices[3:6], vertices[6:]),
    )


class OracleReader:
    def __init__(self, library):
        self.library = library
        library.sm64_policy_state_size.argtypes = [I]
        library.sm64_policy_state_size.restype = U
        for index, record in enumerate((Oracle, Mario, Camera, Progress, Object, Ray, Surface)):
            if library.sm64_policy_state_size(index) != ct.sizeof(record):
                raise RuntimeError(f"Native oracle ABI size mismatch: {record.__name__}")
        library.sm64_policy_read_state.argtypes = [ct.POINTER(Oracle), U]
        library.sm64_policy_read_state.restype = I
        library.sm64_policy_behavior_name.argtypes = [U]
        library.sm64_policy_behavior_name.restype = ct.c_char_p
        self.buffer = Oracle()
        self.names: dict[int, str | None] = {}

    def read(self, position, velocity, width, height) -> dict:
        value = self.buffer
        if not self.library.sm64_policy_read_state(ct.byref(value), ct.sizeof(value)):
            raise RuntimeError("Native oracle read failed")
        if value.version != 1 or not 0 <= value.object_count <= MAX_OBJECTS:
            raise RuntimeError("Invalid native oracle record")
        m = value.mario
        floor, ceiling, wall = surface(m.floor), surface(m.ceiling), surface(m.wall)
        mario = MarioState(
            position=position,
            velocity=velocity,
            face_angle=tuple(m.face_angle),
            angular_velocity=tuple(m.angle_velocity),
            forward_velocity=m.forward_velocity,
            action=m.action,
            previous_action=m.previous_action,
            action_arg=m.action_arg,
            action_state=m.action_state,
            action_timer=m.action_timer,
            flags=m.flags,
            input_flags=m.input,
            health_raw=m.health_raw,
            lives=m.lives,
            room=m.room,
            invincibility_timer=m.invincibility_timer,
            cap_timer=m.cap_timer,
            wall_kick_timer=m.wall_kick_timer,
            double_jump_timer=m.double_jump_timer,
            frames_since_a=m.frames_since_a,
            frames_since_b=m.frames_since_b,
            airborne=bool(m.action & (1 << 11)),
            swimming=bool(m.action & (1 << 13)),
            on_pole=bool(m.action & (1 << 20)),
            hanging=bool(m.action & (1 << 21)),
            near_floor=floor is not None and abs(position[1] - m.floor_height) <= 4,
            floor_height=m.floor_height if floor else None,
            ceiling_height=m.ceiling_height if ceiling else None,
            water_level=m.water_level,
            quicksand_depth=m.quicksand_depth,
            floor=floor,
            ceiling=ceiling,
            wall=wall,
            held_object_id=m.held_object_id or None,
            ridden_object_id=m.ridden_object_id or None,
            platform_id=m.platform_id or None,
            interacted_object_id=m.interacted_object_id or None,
        )
        c = value.camera
        camera = (
            CameraState(
                tuple(c.position),
                tuple(c.focus),
                c.roll,
                c.yaw,
                c.mode,
                c.cutscene,
                c.fov,
                (width, height),
            )
            if c.valid
            else None
        )
        objects = []
        for obj in value.objects[: value.object_count]:
            if obj.behavior_id not in self.names:
                name = self.library.sm64_policy_behavior_name(obj.behavior_id)
                self.names[obj.behavior_id] = name.decode("utf-8", "replace") if name else None
            objects.append(
                ObjectState(
                    id=obj.id,
                    behavior_id=obj.behavior_id,
                    behavior_name=self.names[obj.behavior_id],
                    behavior_params=obj.behavior_params,
                    interaction_type=obj.interaction_type,
                    interaction_subtype=obj.interaction_subtype,
                    affordances=tuple(
                        dict.fromkeys(
                            name for mask, name in AFFORDANCES if obj.interaction_type & mask
                        )
                    ),
                    active_flags=obj.active_flags,
                    action=obj.action,
                    sub_action=obj.sub_action,
                    timer=obj.timer,
                    health=obj.health,
                    damage_or_coin_value=obj.damage_or_coin_value,
                    move_flags=obj.move_flags,
                    intangible_timer=obj.intangible_timer,
                    room=obj.room,
                    face_angle=tuple(obj.face_angle),
                    position=tuple(obj.position),
                    relative_position=tuple(obj.position[i] - position[i] for i in range(3)),
                    velocity=tuple(obj.velocity),
                    hitbox_radius=obj.hitbox_radius,
                    hitbox_height=obj.hitbox_height,
                    hitbox_down_offset=obj.hitbox_down_offset,
                    hurtbox_radius=obj.hurtbox_radius,
                    hurtbox_height=obj.hurtbox_height,
                    distance=obj.distance,
                )
            )
        geometry = GeometryState(
            tuple(
                RaySample(
                    "radial" if i < 8 else "ground" if i < 17 else "ceiling",
                    tuple(ray.origin),
                    tuple(ray.direction),
                    ray.length,
                    ray.distance if ray.surface.valid else None,
                    tuple(ray.position) if ray.surface.valid else None,
                    surface(ray.surface),
                )
                for i, ray in enumerate(value.rays)
            )
        )
        p = value.progress
        progress = ProgressState(
            p.level,
            p.area,
            p.act,
            p.course,
            p.save_file,
            p.stars,
            p.coins,
            p.lives,
            p.save_flags,
            tuple(p.star_masks),
            p.cannon_mask,
            p.last_completed_course,
            p.last_completed_star,
            bool(p.credits_active),
        )
        return {
            "engine_frame": value.engine_frame,
            "mario": mario,
            "camera": camera,
            "geometry": geometry,
            "objects": NearbyObjects(
                value.object_radius,
                MAX_OBJECTS,
                value.objects_in_radius,
                value.objects_in_radius > value.object_count,
                tuple(objects),
            ),
            "progress": progress,
        }
