#pragma once

#if defined(__GNUC__) && !defined(_MSC_VER)
// ── CryEngine 3.x compatibility shims for GCC/MinGW ─────────────────────────
// CryEngine was written for MSVC; these stubs let its public headers compile
// under modern GCC cross-targeting Windows (MinGW-w64).  None of them affect
// runtime behaviour — KCSE never instantiates CryEngine containers or aligned
// types directly.

// FLT_MIN, FLT_EPSILON, DBL_MIN used in Cry_Math.h / Cry_Vector3.h
#include <cfloat>
#include <utility>
#include <memory>
#include <unordered_map>

// std__hash_map / std__hash_multimap: StlUtils.h only special-cases MSVC,
// Linux/Apple GCC, and Clang; on plain GCC/MinGW it falls through to the
// nonexistent std::hash_map.  Pre-define these before StlUtils.h's own
// '#ifndef std__hash_map' so it keeps our (valid) definitions instead.
#define std__hash_map std::unordered_map
#define std__hash_multimap std::unordered_multimap

// stdext::hash_map / hash_compare — MSVC extensions used unconditionally by
// StlUtils.h's hash_compare<pair<...>> partial specialisation whenever
// _MSC_VER isn't defined >= 1930 (which includes plain GCC, since an
// undefined macro is 0 in #if expressions).  Stub the primary templates so
// that specialisation and the 'using stdext::hash_map' declarations compile.
// Must be declared before platform.h below, which transitively pulls in
// StlUtils.h.
namespace stdext {
    template<class Key, class Traits = void>
    struct hash_compare {};

    template<class Key, class T,
             class Tr = hash_compare<Key>,
             class A  = std::allocator<std::pair<const Key, T>>>
    struct hash_map {};

    template<class Key, class T,
             class Tr = hash_compare<Key>,
             class A  = std::allocator<std::pair<const Key, T>>>
    struct hash_multimap {};

    template<class Key,
             class Tr = hash_compare<Key>,
             class A  = std::allocator<Key>>
    struct hash_set {};

    template<class Key,
             class Tr = hash_compare<Key>,
             class A  = std::allocator<Key>>
    struct hash_multiset {};
}  // namespace stdext

// DEFINE_ALIGNED_DATA: MSVC allows __declspec(align) inside typedef;
// GCC does not.  Win64specific.h / Win32specific.h (pulled in by
// platform.h) unconditionally #define this using __declspec, clobbering
// any definition made before they're included.  So force platform.h to
// run first, then override the macro afterwards; platform.h's own header
// guard makes CryEngine headers' later '#include <platform.h>' a no-op.
#include <platform.h>

#undef DEFINE_ALIGNED_DATA
#undef DEFINE_ALIGNED_DATA_STATIC
#undef DEFINE_ALIGNED_DATA_CONST
#define DEFINE_ALIGNED_DATA(type, name, alignment) \
    type __attribute__((aligned(alignment))) name
#define DEFINE_ALIGNED_DATA_STATIC(type, name, alignment) \
    static type __attribute__((aligned(alignment))) name
#define DEFINE_ALIGNED_DATA_CONST(type, name, alignment) \
    const type __attribute__((aligned(alignment))) name

#endif  // __GNUC__ && !_MSC_VER

#include <Cry_Math.h>
