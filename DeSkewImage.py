"""Deprecated compatibility wrapper for image deskewing."""

from app.domain.ingestion.deskew import ImageDeskewer


def getSkewAngle(cvImage) -> float:
    contours = ImageDeskewer()._find_text_contours(cvImage)
    if not contours:
        return 0.0
    return ImageDeskewer()._skew_angle(contours[0])


def rotateImage(cvImage, angle: float):
    return ImageDeskewer().rotate(cvImage, angle)


def deskew(cvImage):
    return ImageDeskewer().deskew(cvImage)

