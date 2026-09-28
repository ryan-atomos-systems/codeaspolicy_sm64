#ifndef SM64_POLICY_STATE_H
#define SM64_POLICY_STATE_H

#include <stdint.h>

/* Pointer-free ABI: only 32-bit scalars, fixed arrays, and nested records.
 * Keep native_state.py synchronized; the reader checks every record size. */
#define POLICY_STATE_VERSION 1
#define POLICY_MAX_OBJECTS 64
#define POLICY_RAYS 18
#define POLICY_COURSES 26
#define POLICY_OBJECT_RADIUS 6000.0f

struct Object;
struct PolicySurface {
    int32_t valid, type, flags, room;
    uint32_t object_id;
    float normal[3], vertices[9];
};
struct PolicyMario {
    int32_t face_angle[3], angle_velocity[3];
    uint32_t action, previous_action, action_arg, flags, input;
    int32_t action_state, action_timer, invincibility_timer, cap_timer;
    int32_t wall_kick_timer, double_jump_timer, frames_since_a, frames_since_b;
    int32_t health_raw, lives, room;
    float forward_velocity, floor_height, ceiling_height, water_level, quicksand_depth;
    uint32_t held_object_id, ridden_object_id, platform_id, interacted_object_id;
    struct PolicySurface floor, ceiling, wall;
};
struct PolicyCamera {
    int32_t valid, mode, cutscene, yaw, roll;
    float position[3], focus[3], fov;
};
struct PolicyObject {
    uint32_t id, behavior_id, behavior_params, interaction_type, interaction_subtype;
    int32_t active_flags, action, sub_action, timer, health, damage_or_coin_value;
    int32_t move_flags, intangible_timer, room, face_angle[3];
    float position[3], velocity[3], hitbox_radius, hitbox_height, hitbox_down_offset;
    float hurtbox_radius, hurtbox_height, distance;
};
struct PolicyRay {
    float origin[3], direction[3], length, distance, position[3];
    struct PolicySurface surface;
};
struct PolicyProgress {
    int32_t level, area, act, course, save_file, stars, coins, lives;
    int32_t last_completed_course, last_completed_star, credits_active;
    uint32_t save_flags, star_masks[POLICY_COURSES], cannon_mask;
};
struct PolicyState {
    uint32_t version, engine_frame;
    struct PolicyMario mario;
    struct PolicyCamera camera;
    struct PolicyProgress progress;
    int32_t object_count, objects_in_radius;
    float object_radius;
    struct PolicyObject objects[POLICY_MAX_OBJECTS];
    struct PolicyRay rays[POLICY_RAYS];
};

void sm64_policy_object_allocated(struct Object* object);
uint32_t sm64_policy_state_size(int record);
int sm64_policy_read_state(struct PolicyState* state, uint32_t size);
const char* sm64_policy_behavior_name(uint32_t id);

#endif
