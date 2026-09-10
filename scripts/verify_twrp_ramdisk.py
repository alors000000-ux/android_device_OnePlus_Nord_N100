#!/usr/bin/env python3
"""Check the recovery ramdisk's BE2013 Qualcomm/FBE runtime payload."""

from __future__ import annotations

import argparse
import gzip
import struct
from pathlib import Path


REQUIRED = (
    "init.recovery.qcom.rc",
    "init.recovery.qcom_decrypt.rc",
    "init.recovery.qcom_decrypt.fbe.rc",
    "init.recovery.usb.rc",
    "system/etc/twrp.flags",
    "system/bin/prepdecrypt.sh",
    "system/bin/qseecomd",
    "system/bin/android.hardware.keymaster@4.0-service-qti",
    "system/bin/android.hardware.gatekeeper@1.0-service-qti",
    "system/bin/bootctl",
    "system/bin/fastbootd",
    "system/bin/resetprop",
    "system/lib64/libandroidicu.so",
    "vendor/lib64/hw/android.hardware.gatekeeper@1.0-impl-qti.so",
    "vendor/lib64/libQSEEComAPI.so",
)


def align(value: int, page_size: int) -> int:
    return (value + page_size - 1) // page_size * page_size


def parse_newc(data: bytes) -> set[str]:
    names: set[str] = set()
    offset = 0
    while offset + 110 <= len(data):
        header = data[offset : offset + 110]
        if header[:6] not in (b"070701", b"070702"):
            raise ValueError(f"invalid cpio header at offset {offset}")
        name_size = int(header[94:102], 16)
        file_size = int(header[54:62], 16)
        name_start = offset + 110
        name_end = name_start + name_size
        data_start = align(name_end, 4)
        data_end = data_start + file_size
        name = data[name_start : name_end - 1].decode("utf-8", "replace")
        if name == "TRAILER!!!":
            return names
        names.add(name)
        offset = align(data_end, 4)
    raise ValueError("cpio trailer is missing")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("boot_image", type=Path)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()

    image = args.boot_image.read_bytes()
    if image[:8] != b"ANDROID!":
        raise SystemExit("ERROR: ramdisk check received a non-Android image")
    page_size = struct.unpack_from("<I", image, 36)[0]
    kernel_size = struct.unpack_from("<I", image, 8)[0]
    ramdisk_size = struct.unpack_from("<I", image, 16)[0]
    ramdisk_start = page_size + align(kernel_size, page_size)
    ramdisk = image[ramdisk_start : ramdisk_start + ramdisk_size]
    if not ramdisk.startswith(b"\x1f\x8b"):
        raise SystemExit("ERROR: recovery ramdisk is not gzip-compressed")
    try:
        names = parse_newc(gzip.decompress(ramdisk))
    except (OSError, ValueError) as exc:
        raise SystemExit(f"ERROR: cannot parse recovery ramdisk: {exc}") from exc

    missing = [name for name in REQUIRED if name not in names]
    if missing:
        raise SystemExit("ERROR: recovery ramdisk is missing: " + ", ".join(missing))
    args.report.write_text(
        "\n".join(
            [
                "status=PASS",
                f"ramdisk_compressed_size={ramdisk_size}",
                f"ramdisk_entries={len(names)}",
                "qcom_fbe_payload=present",
            ]
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
