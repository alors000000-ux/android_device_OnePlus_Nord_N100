# Android-11 TWRP product for the OnePlus Nord N100 (BE2013).
#
# The legacy omni_ product is retained only for historical reference. This
# product is used by the GitHub Actions-only BE2013 build pipeline.

$(call inherit-product, $(SRC_TARGET_DIR)/product/core_64_bit.mk)
$(call inherit-product, $(SRC_TARGET_DIR)/product/full_base.mk)
$(call inherit-product, $(SRC_TARGET_DIR)/product/full_base_telephony.mk)

$(call inherit-product, device/oneplus/OnePlusN100/device.mk)
$(call inherit-product, vendor/twrp/config/common.mk)

PRODUCT_DEVICE := OnePlusN100
PRODUCT_NAME := twrp_OnePlusN100
PRODUCT_BRAND := OnePlus
PRODUCT_MODEL := OnePlus Nord N100
PRODUCT_MANUFACTURER := OnePlus
