/* Read-only policy observations. No engine updates, Lua hooks, or RNG calls. */
#include "policy_state.h"
#include "policy_bridge.h"
#include "behavior_table.h"
#include "object_constants.h"
#include "object_fields.h"
#include "game/area.h"
#include "game/camera.h"
#include "game/display.h"
#include "game/level_update.h"
#include "game/object_list_processor.h"
#include "game/save_file.h"
#include "engine/math_util.h"
#include "engine/surface_collision.h"
#include <math.h>
#include <stddef.h>
#include <string.h>

static uint32_t sObjectGenerations[OBJECT_POOL_CAPACITY];

static int object_slot(struct Object* object) {
    uintptr_t ptr = (uintptr_t)object, base = (uintptr_t)gObjectPool;
    if (ptr < base || ptr >= base + sizeof(struct Object) * OBJECT_POOL_CAPACITY) { return -1; }
    if ((ptr - base) % sizeof(struct Object)) { return -1; }
    return (ptr - base) / sizeof(struct Object);
}

void sm64_policy_object_allocated(struct Object* object) {
    int slot = object_slot(object);
    if (gPolicyConfigured && slot >= 0) { sObjectGenerations[slot]++; }
}

static uint32_t object_id(struct Object* object) {
    int slot = object_slot(object);
    if (slot < 0 || !(object->activeFlags & ACTIVE_FLAG_ACTIVE)) { return 0; }
    return (sObjectGenerations[slot] << 10) | (slot + 1);
}

uint32_t sm64_policy_state_size(int record) {
    switch (record) {
        case 0: return sizeof(struct PolicyState);
        case 1: return sizeof(struct PolicyMario);
        case 2: return sizeof(struct PolicyCamera);
        case 3: return sizeof(struct PolicyProgress);
        case 4: return sizeof(struct PolicyObject);
        case 5: return sizeof(struct PolicyRay);
        case 6: return sizeof(struct PolicySurface);
        default: return 0;
    }
}

const char* sm64_policy_behavior_name(uint32_t id) { return get_behavior_name_from_id(id); }

static void read_surface(struct PolicySurface* output, struct Surface* surface) {
    if (!surface) { return; }
    output->valid = 1;
    output->type = surface->type;
    output->flags = surface->flags;
    output->room = surface->room;
    output->object_id = object_id(surface->object);
    output->normal[0] = surface->normal.x;
    output->normal[1] = surface->normal.y;
    output->normal[2] = surface->normal.z;
    for (int i = 0; i < 3; i++) {
        output->vertices[i] = surface->vertex1[i];
        output->vertices[i + 3] = surface->vertex2[i];
        output->vertices[i + 6] = surface->vertex3[i];
    }
}

static void read_mario(struct PolicyMario* output, struct MarioState* mario) {
    for (int i = 0; i < 3; i++) {
        output->face_angle[i] = mario->faceAngle[i];
        output->angle_velocity[i] = mario->angleVel[i];
    }
    output->action = mario->action;
    output->previous_action = mario->prevAction;
    output->action_arg = mario->actionArg;
    output->flags = mario->flags;
    output->input = mario->input;
    output->action_state = mario->actionState;
    output->action_timer = mario->actionTimer;
    output->invincibility_timer = mario->invincTimer;
    output->cap_timer = mario->capTimer;
    output->wall_kick_timer = mario->wallKickTimer;
    output->double_jump_timer = mario->doubleJumpTimer;
    output->frames_since_a = mario->framesSinceA;
    output->frames_since_b = mario->framesSinceB;
    output->health_raw = mario->health;
    output->lives = mario->numLives;
    output->room = mario->currentRoom;
    output->forward_velocity = mario->forwardVel;
    output->floor_height = mario->floorHeight;
    output->ceiling_height = mario->ceilHeight;
    output->water_level = mario->waterLevel;
    output->quicksand_depth = mario->quicksandDepth;
    output->held_object_id = object_id(mario->heldObj);
    output->ridden_object_id = object_id(mario->riddenObj);
    output->platform_id = object_id(mario->marioObj ? mario->marioObj->platform : NULL);
    output->interacted_object_id = object_id(mario->interactObj);
    read_surface(&output->floor, mario->floor);
    read_surface(&output->ceiling, mario->ceil);
    read_surface(&output->wall, mario->wall);
}

static void read_object(struct PolicyObject* output, struct Object* object, float distance) {
    output->id = object_id(object);
    output->behavior_id = get_id_from_behavior(object->behavior);
    output->behavior_params = object->oBehParams;
    output->interaction_type = object->oInteractType;
    output->interaction_subtype = object->oInteractionSubtype;
    output->active_flags = object->activeFlags;
    output->action = object->oAction;
    output->sub_action = object->oSubAction;
    output->timer = object->oTimer;
    output->health = object->oHealth;
    output->damage_or_coin_value = object->oDamageOrCoinValue;
    output->move_flags = object->oMoveFlags;
    output->intangible_timer = object->oIntangibleTimer;
    output->room = object->oRoom;
    output->face_angle[0] = (int16_t)object->oFaceAnglePitch;
    output->face_angle[1] = (int16_t)object->oFaceAngleYaw;
    output->face_angle[2] = (int16_t)object->oFaceAngleRoll;
    vec3f_set(output->position, object->oPosX, object->oPosY, object->oPosZ);
    vec3f_set(output->velocity, object->oVelX, object->oVelY, object->oVelZ);
    output->hitbox_radius = object->hitboxRadius;
    output->hitbox_height = object->hitboxHeight;
    output->hitbox_down_offset = object->hitboxDownOffset;
    output->hurtbox_radius = object->hurtboxRadius;
    output->hurtbox_height = object->hurtboxHeight;
    output->distance = distance;
}

static void read_objects(struct PolicyState* output, struct MarioState* mario) {
    output->object_radius = POLICY_OBJECT_RADIUS;
    for (int i = 0; i < OBJECT_POOL_CAPACITY; i++) {
        struct Object* object = &gObjectPool[i];
        if (!(object->activeFlags & ACTIVE_FLAG_ACTIVE) || object == mario->marioObj) { continue; }
        if (object->header.gfx.activeAreaIndex != gCurrAreaIndex) { continue; }
        if (object->activeFlags & ACTIVE_FLAG_UNIMPORTANT) { continue; } // Particle/effect pool.
        float dx = object->oPosX - mario->pos[0], dy = object->oPosY - mario->pos[1];
        float dz = object->oPosZ - mario->pos[2];
        float distance = sqrtf(dx * dx + dy * dy + dz * dz);
        if (!isfinite(distance) || distance > POLICY_OBJECT_RADIUS) { continue; }
        output->objects_in_radius++;
        int index = output->object_count;
        // Keep the nearest 64, with stable pool order for distance ties.
        if (index == POLICY_MAX_OBJECTS) {
            if (distance >= output->objects[index - 1].distance) { continue; }
            index--;
        } else {
            output->object_count++;
        }
        while (index > 0 && distance < output->objects[index - 1].distance) {
            output->objects[index] = output->objects[index - 1];
            index--;
        }
        read_object(&output->objects[index], object, distance);
    }
}

static void read_ray(struct PolicyRay* output, float x, float y, float z, float dx, float dy, float dz) {
    struct Surface* surface = NULL;
    Vec3f direction = {dx, dy, dz};
    vec3f_set(output->origin, x, y, z);
    output->length = sqrtf(dx * dx + dy * dy + dz * dz);
    for (int i = 0; i < 3; i++) { output->direction[i] = direction[i] / output->length; }
    find_surface_on_ray(output->origin, direction, &surface, output->position);
    float hx = output->position[0] - x, hy = output->position[1] - y, hz = output->position[2] - z;
    output->distance = sqrtf(hx * hx + hy * hy + hz * hz);
    read_surface(&output->surface, surface);
}

int sm64_policy_read_state(struct PolicyState* output, uint32_t size) {
    if (!output || size != sizeof(*output) || !gMarioStates[0].marioObj) { return 0; }
    memset(output, 0, sizeof(*output));
    struct MarioState* mario = &gMarioStates[0];
    output->version = POLICY_STATE_VERSION;
    output->engine_frame = gGlobalTimer;
    read_mario(&output->mario, mario);
    if (gCamera) {
        output->camera.valid = 1;
        output->camera.mode = gCamera->mode;
        output->camera.cutscene = gCamera->cutscene;
        output->camera.yaw = gCamera->yaw;
        output->camera.roll = gLakituState.roll;
        vec3f_copy(output->camera.position, gLakituState.pos);
        vec3f_copy(output->camera.focus, gLakituState.focus);
        output->camera.fov = gFOVState.fov;
    }
    struct PolicyProgress* progress = &output->progress;
    progress->level = gCurrLevelNum;
    progress->area = gCurrAreaIndex;
    progress->act = gCurrActNum;
    progress->course = gCurrCourseNum;
    progress->save_file = gCurrSaveFileNum;
    progress->stars = mario->numStars;
    progress->coins = mario->numCoins;
    progress->lives = mario->numLives;
    progress->last_completed_course = gLastCompletedCourseNum;
    progress->last_completed_star = gLastCompletedStarNum;
    progress->credits_active = gCurrCreditsEntry != NULL;
    progress->save_flags = save_file_get_flags();
    for (int course = 0; course < POLICY_COURSES; course++) {
        progress->star_masks[course] = save_file_get_star_flags(gCurrSaveFileNum - 1, course - 1);
        if (course > 0 && save_file_is_cannon_unlocked(gCurrSaveFileNum - 1, course)) {
            progress->cannon_mask |= 1u << course;
        }
    }
    read_objects(output, mario);
    // Ray queries don't invoke game updates. Restore the engine's filter flag.
    int checking_camera = gCheckingSurfaceCollisionsForCamera;
    gCheckingSurfaceCollisionsForCamera = 0;
    float x = mario->pos[0], y = mario->pos[1], z = mario->pos[2];
    for (int i = 0; i < 8; i++) {
        int16_t yaw = mario->faceAngle[1] + i * 0x2000;
        read_ray(&output->rays[i], x, y + 100, z, sins(yaw) * 1500, 0, coss(yaw) * 1500);
    }
    int index = 8;
    for (int dx = -1; dx <= 1; dx++) {
        for (int dz = -1; dz <= 1; dz++) {
            read_ray(&output->rays[index++], x + dx * 300, y + 200, z + dz * 300, 0, -4000, 0);
        }
    }
    read_ray(&output->rays[17], x, y + 100, z, 0, 2000, 0);
    gCheckingSurfaceCollisionsForCamera = checking_camera;
    return 1;
}
