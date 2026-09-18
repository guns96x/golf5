# Integrity Algorithms

## Principles

Each integrity profile must declare:

- Covered regions and their order
- Excluded fields and padding behavior
- Word width, byte order, seed and final transformation
- Checksum storage locations and encoding
- Nested/dependent checks
- Signature coverage, algorithm, trust material and version constraints where applicable
- Whether correction occurs offline or inside the flashing tool

## Additive Checksum (32-bit)

For a proven additive 32-bit scheme:

$$\left(\sum_i w_i + c\right) \bmod 2^{32} = K$$

Correction field:

$$c = \left(K - \sum_i w_i\right) \bmod 2^{32}$$

> [!IMPORTANT]
> `K = 0xD01FE500` belongs only in a profile whose actual algorithm and fixtures establish that relationship. Finding the constant in a binary is **insufficient** evidence.

## CRC Profiles

A CRC profile needs at minimum:

```
width, polynomial, init, refin, refout, xorout,
covered_ranges, stored_byte_order, check_vector
```

"CRC16" or "CRC32" alone is ambiguous. Common variants:

| Name | Width | Polynomial | Init | RefIn | RefOut | XorOut |
|---|---|---|---|---|---|---|
| CRC-32 (ISO 3309) | 32 | 0x04C11DB7 | 0xFFFFFFFF | true | true | 0xFFFFFFFF |
| CRC-16/CCITT | 16 | 0x1021 | 0xFFFF | false | false | 0x0000 |
| CRC-16/IBM | 16 | 0x8005 | 0x0000 | true | true | 0x0000 |

Always verify against a known-good test vector before trusting a CRC implementation.

## Cryptographic Signatures

Cryptographic signatures authenticate signed content using a verification key. Recomputing a checksum **cannot** regenerate a valid RSA/ECDSA signature.

Reference: [NIST Digital Signature Standard (FIPS 186-5)](https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.186-5.pdf)

### Key Distinctions

The skill must distinguish:

| Mechanism | Nature |
|---|---|
| Programming-session access | Tool-level unlocking (SecurityAccess, seed-key) |
| Hardware read/write protection | Flash sector protection, OTP fuses |
| Executable patches | Code modifications that alter verification behavior |
| Authenticated firmware | Properly signed images with anti-rollback |

A patched verification routine must be reported as a **code/security change**, never as "signature repaired." Unknown OTP or protection settings are not ordinary calibration-edit targets.

## EDC16 Bosch Checksum — Verified Profile

### Applicable Target
- ECU: Bosch EDC16U34
- HW: 03G906021QJ
- SW: 391847
- Vehicle: VW Golf 5 1.9 TDI BLS

### Algorithm
- Type: Additive 32-bit big-endian word sum
- Invariant: $K = \text{0xD01FE500}$
- Coverage: Calibration area (512 KB block)
- Word size: 32-bit (4 bytes), big-endian
- Correction field: Last 4 bytes of covered region
- Byte order: Big-endian (Motorola MSB_FIRST)

### Implementation

```python
def fix_edc16_checksum(data: bytearray, start: int, size: int) -> bytearray:
    """
    Fix EDC16 additive checksum for calibration block.
    
    Args:
        data: Full firmware image as mutable bytearray
        start: Start offset of calibration area
        size: Size of calibration area in bytes (must be multiple of 4)
    
    Returns:
        Modified data with corrected checksum
    """
    INVARIANT = 0xD01FE500
    
    # Zero the correction field (last 4 bytes of covered region)
    correction_offset = start + size - 4
    data[correction_offset:correction_offset + 4] = b'\x00\x00\x00\x00'
    
    # Sum all 32-bit BE words in covered region
    word_sum = 0
    for i in range(start, start + size, 4):
        word = int.from_bytes(data[i:i+4], byteorder='big')
        word_sum = (word_sum + word) & 0xFFFFFFFF
    
    # Calculate correction
    correction = (INVARIANT - word_sum) & 0xFFFFFFFF
    data[correction_offset:correction_offset + 4] = correction.to_bytes(4, byteorder='big')
    
    return data
```

> [!WARNING]
> This profile is verified for SW 391847 only. Other EDC16 variants may use different invariants, coverage ranges, or word sizes. Verify with a known-good image before applying to a new SW version.

## Verification Requirements

Integrity implementations need:

1. **Known-good vectors**: Verified original images with correct checksums
2. **Deliberately corrupted fixtures**: Images with introduced errors to verify detection
3. **Boundary cases**: Partial coverage, empty regions, maximum values

An unknown required check must **not** return success. Return `UNKNOWN` and block flash readiness.

## Multiple Integrity Layers

Some ECUs have nested integrity:

```
Layer 1: Block checksums (calibration area)
Layer 2: Global CRC (entire image)
Layer 3: RSA signature (newer ECUs with TPROT)
```

Each layer must be addressed in order. Fixing a block checksum does not repair a broken CRC or invalidated signature.
