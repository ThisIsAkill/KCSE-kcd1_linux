#pragma once
#include <cstdint>
#include <windows.h>
#include <spdlog/spdlog.h>

namespace VtableHook {

namespace detail {

// A real vtable lives in a read-only (or read+exec) mapped page, never on the
// heap or stack. Rejecting anything else catches the case where the object
// pointer (usually resolved through a REL::ID address-library offset) is
// stale for the running game build: interfuscated CryEngine vtables shuffle
// per-build, so an offset RE'd against one build can land on garbage for
// another. Without this check, indexing that garbage and writing through it
// silently corrupts whatever unrelated memory happens to be there.
inline bool IsPlausibleVtable(const void* p) {
    if (!p) return false;
    MEMORY_BASIC_INFORMATION mbi{};
    if (!VirtualQuery(p, &mbi, sizeof(mbi))) return false;
    if (mbi.State != MEM_COMMIT) return false;
    switch (mbi.Protect & 0xFF) {
    case PAGE_READONLY:
    case PAGE_EXECUTE:
    case PAGE_EXECUTE_READ:
        return true;
    default:
        return false;
    }
}

inline bool ValidateSlot(void* pObject, uint32_t vtableByteOffset, uintptr_t** outVtable) {
    if (!pObject) return false;
    MEMORY_BASIC_INFORMATION mbi{};
    if (!VirtualQuery(pObject, &mbi, sizeof(mbi)) || mbi.State != MEM_COMMIT)
        return false;

    auto vtable = *reinterpret_cast<uintptr_t**>(pObject);
    if (!IsPlausibleVtable(vtable)) return false;
    if (!IsPlausibleVtable(reinterpret_cast<const uint8_t*>(vtable) + vtableByteOffset))
        return false;

    *outVtable = vtable;
    return true;
}

}  // namespace detail

// Returns nullptr (and logs) instead of patching when pObject doesn't look
// like a real object with a real vtable at vtableByteOffset -- see
// IsPlausibleVtable. Callers must treat a nullptr return as "hook not
// installed", not as "original function is null".
template<typename Fn>
Fn Swap(void* pObject, uint32_t vtableByteOffset, Fn newFunc) {
    uintptr_t* vtable = nullptr;
    if (!detail::ValidateSlot(pObject, vtableByteOffset, &vtable)) {
        spdlog::error("VtableHook::Swap: object at {} has no plausible vtable at +{:#x}; "
                       "refusing to hook (offset is likely stale for this game build)",
                       pObject, vtableByteOffset);
        return nullptr;
    }

    auto& slot = vtable[vtableByteOffset / 8];

    DWORD oldProt;
    VirtualProtect(&slot, sizeof(slot), PAGE_EXECUTE_READWRITE, &oldProt);
    auto original = reinterpret_cast<Fn>(slot);
    slot = reinterpret_cast<uintptr_t>(newFunc);
    VirtualProtect(&slot, sizeof(slot), oldProt, &oldProt);

    return original;
}

template<typename Fn>
void Restore(void* pObject, uint32_t vtableByteOffset, Fn originalFunc) {
    uintptr_t* vtable = nullptr;
    if (!detail::ValidateSlot(pObject, vtableByteOffset, &vtable))
        return;

    auto& slot = vtable[vtableByteOffset / 8];

    DWORD oldProt;
    VirtualProtect(&slot, sizeof(slot), PAGE_EXECUTE_READWRITE, &oldProt);
    slot = reinterpret_cast<uintptr_t>(originalFunc);
    VirtualProtect(&slot, sizeof(slot), oldProt, &oldProt);
}

}  // namespace VtableHook
