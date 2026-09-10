#!/usr/bin/env python3
"""Verify that a TWRP boot image preserves the target boot ABI inputs."""

from __future__ import annotations

import argparse
import hashlib
import struct
from pathlib import Path


TARGET_CMDLINE = (
    "androidboot.hardware=qcom androidboot.console=ttyMSM0 "
    "androidboot.memcg=1 lpm_levels.sleep_disabled=1 "
    "video=vfb:640x400,bpp=32,memsize=3072000 msm_rtb.filter=0x237 "
    "service_locator.enable=1 swiotlb=2048 loop.max_part=7 buildvariant=user"
)

# These values are read from the verified BE83BA stock boot header.  Keeping
# them exact prevents a recovery image built with a different mkbootimg layout
# from reaching the bootloader and then resetting before recovery starts.
TARGET_KERNEL_ADDR = 0x00008000
TARGET_RAMDISK_ADDR = 0x01000000
TARGET_SECOND_ADDR = 0x00000000
TARGET_TAGS_ADDR = 0x00000100
TARGET_HEADER_SIZE = 1660
TARGET_DTB_ADDR = 0x01F00000
TARGET_OS_VERSION = 0x16000164


def align(value: int, page_size: int) -> int:
    return (value + page_size - 1) // page_size * page_size


def abort(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("boot_image", type=Path)
    parser.add_argument("kernel", type=Path)
    parser.add_argument("dtb", type=Path)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()

    image = args.boot_image.read_bytes()
    if image[:8] != b"ANDROID!":
        abort("output lacks Android boot magic")
    kernel_size = struct.unpack_from("<I", image, 8)[0]
    kernel_addr = struct.unpack_from("<I", image, 12)[0]
    ramdisk_size = struct.unpack_from("<I", image, 16)[0]
    ramdisk_addr = struct.unpack_from("<I", image, 20)[0]
    second_size = struct.unpack_from("<I", image, 24)[0]
    second_addr = struct.unpack_from("<I", image, 28)[0]
    tags_addr = struct.unpack_from("<I", image, 32)[0]
    page_size = struct.unpack_from("<I", image, 36)[0]
    header_version = struct.unpack_from("<I", image, 40)[0]
    os_version = struct.unpack_from("<I", image, 44)[0]
    recovery_dtbo_size = struct.unpack_from("<I", image, 1632)[0]
    header_size = struct.unpack_from("<I", image, 1644)[0]
    dtb_size = struct.unpack_from("<I", image, 1648)[0]
    dtb_addr = struct.unpack_from("<Q", image, 1652)[0]
    command_line = image[64 : 64 + 1536].split(b"\0", 1)[0].decode("ascii")
    header_values = {
        "kernel_addr": kernel_addr == TARGET_KERNEL_ADDR,
        "ramdisk_addr": ramdisk_addr == TARGET_RAMDISK_ADDR,
        "second_addr": second_addr == TARGET_SECOND_ADDR,
        "tags_addr": tags_addr == TARGET_TAGS_ADDR,
        "page_size": page_size == 4096,
        "header_version": header_version == 2,
        "header_size": header_size == TARGET_HEADER_SIZE,
        "dtb_addr": dtb_addr == TARGET_DTB_ADDR,
        "os_version": os_version == TARGET_OS_VERSION,
    }
    bad_header = [name for name, passed in header_values.items() if not passed]
    if bad_header:
        abort("output boot header differs from verified stock: " + ", ".join(bad_header))
    if second_size or recovery_dtbo_size:
        abort("output unexpectedly embeds second stage or recovery DTBO")
    if len(image) > 100_663_296:
        abort("output exceeds verified boot partition size")
    if command_line != TARGET_CMDLINE:
        abort("output command line differs from verified target")

    kernel_start = page_size
    ramdisk_start = kernel_start + align(kernel_size, page_size)
    dtb_start = ramdisk_start + align(ramdisk_size, page_size)
    kernel = image[kernel_start : kernel_start + kernel_size]
    dtb = image[dtb_start : dtb_start + dtb_size]
    target_kernel = args.kernel.read_bytes()
    target_dtb = args.dtb.read_bytes()
    if kernel != target_kernel:
        abort("output kernel differs from verified target kernel")
    if dtb != target_dtb:
        abort("output DTB differs from verified target DTB")
    if not ramdisk_size:
        abort("output has no recovery ramdisk")

    args.report.write_text(
        "\n".join(
            [
                "status=PASS",
                "format=Android boot v2 / 4096-byte pages",
                f"boot_size={len(image)}",
                f"boot_sha256={sha256(image)}",
                f"kernel_addr=0x{kernel_addr:08x}",
                f"ramdisk_addr=0x{ramdisk_addr:08x}",
                f"tags_addr=0x{tags_addr:08x}",
                f"dtb_addr=0x{dtb_addr:016x}",
                f"header_size={header_size}",
                f"os_version=0x{os_version:08x}",
                f"kernel_sha256={sha256(kernel)}",
                f"dtb_sha256={sha256(dtb)}",
                f"ramdisk_size={ramdisk_size}",
                "dtbo=not-present; stock DTBO partition remains untouched",
            ]
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
