#ifndef SM64_POLICY_BRIDGE_H
#define SM64_POLICY_BRIDGE_H

#include <stdbool.h>
#include <stdint.h>

struct inputStruct {
    int16_t stickX;
    int16_t stickY;
    bool buttonInput[3];
};

struct gameStateStruct;
extern bool gPolicyCapturePixels;
extern bool gPolicyConfigured;
extern bool gPolicyProgression;
extern bool gPolicyStart;
void sm64_policy_set_start(bool pressed);
extern int gPolicyPort;
extern bool gPolicySeeded;
extern uint32_t gPolicySeed;
void sm64_policy_set_seed(uint32_t seed);
uint32_t sm64_policy_rng_seed(uint32_t stream);
int sm64_policy_seed_version(void);

int sm64_policy_api_version(void);
void sm64_policy_configure(int port);
void sm64_policy_set_progression(bool enabled);
void sm64_policy_read_ui(int* values);
int sm64_policy_progress(int field);
void sm64_policy_read_progress(int* values);
struct gameStateStruct** sm64_policy_step(struct inputStruct* inputs, int frames, bool capture);
struct gameStateStruct* sm64_policy_render(void);
void sm64_policy_spawn(float x, float y, float z, int yaw);
void sm64_policy_free_image(struct gameStateStruct* image);

#endif
