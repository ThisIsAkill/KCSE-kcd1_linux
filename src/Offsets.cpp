#include "Offsets/Offsets.h"

// Only the getter KCSE's own loader needs. Offsets.cpp in libKCD1 implements many
// more of these, but pulls in framework/WuidRegistries.h and the RE'd game modules,
// which KCSE's core loader has no use for.
Offsets::IGameFramework* Offsets::GetCCryAction()
{
    // 0x3785D88: global holding the IGameFramework* (CCryAction)
    static REL::Relocation<IGameFramework**> p{ REL::ID(882) };
    return *p;
}
