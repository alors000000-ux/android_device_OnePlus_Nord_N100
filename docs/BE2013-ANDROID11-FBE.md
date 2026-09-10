# OnePlus Nord N100 BE2013: Android-11 FBE recovery profile

This branch targets only the following stock software identity:

| Field | Required value |
|---|---|
| Model | OnePlus Nord N100 `BE2013` |
| Device / platform | `OnePlusN100` / `bengal` (SM4250) |
| OxygenOS | `11.0.5.BE83BA` |
| Build | `BE2013_7_220331` / `2203311222` |
| Boot format | Android boot header v2, 4 KiB pages |
| Boot partition | 100,663,296 bytes; A/B (`boot_a`, `boot_b`) |
| Encryption | Android 11 FBE, `fileencryption=ice`, `wrappedkey`, metadata key directory `/metadata/vold/metadata_encryption` |

## What changed from the 2021 generated tree

The original tree had old prebuilt kernel/DTB/DTBO files and an abbreviated
recovery fstab. It did not describe the target's metadata partition,
wrapped-key FBE configuration, UFS controller path, dynamic `system_ext`
partition, or recovery-as-boot layout. It also declared no crypto build flags.

This branch instead uses a pinned Android-11 TeamWin base and includes FBE,
metadata-decryption and Qualcomm FBE support. Its fstab is derived from the
target firmware's live vendor fstab. The recovery init starts Qualcomm QSEE,
Keymaster and Gatekeeper as soon as the recovery vendor symlink is ready, so
the FBE path is ready before TWRP requests the key rather than entering the
legacy retry loop. A newer public billie2 TWRP tree was used as a configuration
reference only; its old prebuilt firmware files are not used.

The workflow extracts `Image.gz` and `dtb.img` only from a private, hash-pinned
stock boot image. The prebuilt kernel and DTB left by the old public fork are
not used. DTBO stays in its existing dedicated partition.

## Build and validation

Build only through the manual GitHub Actions workflow. It requires the
repository secret `TWRP_TARGET_EVIDENCE_DEPLOY_KEY`: a read-only deploy key for
the private evidence repository. The workflow refuses to build if the exact
stock boot SHA-256 or its v2 layout differs.

Before artifact upload it verifies that the generated image:

1. has boot-header v2 and 4 KiB pages;
2. fits the known 100,663,296-byte boot partition;
3. contains the exact target kernel and DTB;
4. has the exact verified kernel command line; and
5. contains neither an embedded recovery DTBO nor a second stage.

This is structural validation, not a replacement for a hardware boot test.

## First test is temporary

Even though the device reports an unlocked bootloader, first test a successful
CI artifact with a temporary boot; do not flash it immediately:

```text
fastboot boot twrp-3.x-BE2013-11.0.5-BE83BA.img
```

Once TWRP reaches the main UI, capture `/tmp/recovery.log` before doing any
persistent change. A persistent boot-partition flash replaces the current
Magisk-modified boot ramdisk, so keep the original boot image and a recovery
path available.
