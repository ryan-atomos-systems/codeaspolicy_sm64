/* Versioned, additive ABI for the process-isolated Python policy runtime.
 * Keep CPU scene traversal: it updates animation and can affect gameplay.
 * Only GPU submission/readback is optional. See docs/PERFORMANCE.md.
 */
#include "policy_bridge.h"
#include "game/mario.h"
#include "game/level_update.h"
#include "game/area.h"
#include "game/ingame_menu.h"
#include "game/object_list_processor.h"
#include "engine/math_util.h"
#include "engine/surface_collision.h"
#include "gfx/gfx_pc.h"
#include "sm64.h"
#include <stdlib.h>

extern void produce_interpolation_frames_and_delay(void);
extern void force_make_frame(int playerIndex);
extern struct gameStateStruct* gGameStateStructs[];

bool gPolicyCapturePixels = true;
bool gPolicyConfigured = false;
bool gPolicyStart = false;
void sm64_policy_set_start(bool pressed) { gPolicyStart = pressed; }

bool gPolicyProgression = false;
int gPolicyPort = 7777;
bool gPolicySeeded = false;
uint32_t gPolicySeed = 0;

int sm64_policy_seed_version(void) { return 1; }

uint32_t sm64_policy_rng_seed(uint32_t stream) {
    if (!gPolicySeeded) { return stream; }
    uint32_t value = gPolicySeed ^ stream ^ 0x9e3779b9u;
    value = (value ^ (value >> 16)) * 0x85ebca6bu;
    value = (value ^ (value >> 13)) * 0xc2b2ae35u;
    return value ^ (value >> 16);
}

void sm64_policy_set_seed(uint32_t seed) {
    /* Called once before startup in a fresh process, never during an episode. */
    extern void random_seed16(u16 seed);
    gPolicySeeded = true;
    gPolicySeed = seed;
    random_seed16((u16)sm64_policy_rng_seed(0));
    srand(sm64_policy_rng_seed(1));
}

extern struct gameStateStruct** step_pixels(struct inputStruct* inputs, int frames);

int sm64_policy_api_version(void) { return 3; }

void sm64_policy_set_progression(bool enabled) { gPolicyProgression = enabled; }

void sm64_policy_read_ui(int* values) {
    extern s16 gDialogID, gMenuMode;
    extern s8 gDialogBoxState, sSelectedActIndex;
    values[0] = gDialogID;
    values[1] = gDialogBoxState;
    values[2] = gDialogResponse;
    values[3] = gMenuMode;
    values[4] = gWarpTransition.isActive;
    values[5] = sCurrPlayMode;
    values[6] = sSelectedActIndex + 1;
}

void sm64_policy_configure(int port) {
    if (port >= 1024 && port <= 65535) {
        gPolicyPort = port;
        gPolicyConfigured = true;
    }
}

int sm64_policy_progress(int field) {
    switch (field) {
        case 0: return gMarioStates[0].numStars;
        case 1: return gMarioStates[0].numCoins;
        case 2: return gCurrLevelNum;
        case 3: return gCurrAreaIndex;
        case 4: return gCurrActNum;
        case 5: return gMarioStates[0].action;
        default: return -1;
    }
}

void sm64_policy_read_progress(int* values) {
    for (int i = 0; i < 6; ++i) { values[i] = sm64_policy_progress(i); }
}

struct gameStateStruct** sm64_policy_step(struct inputStruct* inputs, int frames, bool capture) {
    if (frames < 1 || frames > 120) { return 0; }
    gPolicyCapturePixels = capture;
    struct gameStateStruct** states = step_pixels(inputs, frames);
    gPolicyCapturePixels = true;
    return states;
}

struct gameStateStruct* sm64_policy_render(void) {
    /* Submit the display list already built by the last simulation step.
     * No physics, Lua hooks, RNG updates, or scene traversal here. */
    produce_interpolation_frames_and_delay();
    produce_interpolation_frames_and_delay();
    struct gameStateStruct* image = gfx_get_pixels();
    return image;
}

void sm64_policy_free_image(struct gameStateStruct* image) {
    if (image) { free(image->pixels); free(image); }
}

void sm64_policy_spawn(float x, float y, float z, int yaw) {
    struct MarioState* mario = &gMarioStates[0];
    vec3f_set(mario->pos, x, y, z);
    vec3f_set(mario->vel, 0, 0, 0);
    mario->forwardVel = 0;
    mario->faceAngle[1] = (s16)yaw;
    mario->floorHeight = find_floor(x, y + 50, z, &mario->floor);
    set_mario_action(mario, ACT_IDLE, 0);
    vec3f_copy(mario->marioObj->header.gfx.pos, mario->pos);
    struct gameStateStruct* state = gGameStateStructs[0];
    if (state) {
        state->posX = x; state->posY = y; state->posZ = z;
        state->velX = 0; state->velY = 0; state->velZ = 0;
        state->heightAboveGround = y - mario->floorHeight;
    }
    force_make_frame(0);
}
