import cv2
import numpy as np


class ImageDeskewer:
    def deskew(self, image: np.ndarray) -> np.ndarray:
        contours = self._find_text_contours(image)
        if not contours:
            return image
        return self.rotate(image, self._skew_angle(contours[0]))

    def rotate(self, image: np.ndarray, angle: float) -> np.ndarray:
        height, width = image.shape[:2]
        center = (width // 2, height // 2)
        matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        return cv2.warpAffine(
            image,
            matrix,
            (width, height),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE,
        )

    def _find_text_contours(self, image: np.ndarray) -> list[np.ndarray]:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (9, 9), 0)
        threshold = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (30, 5))
        dilated = cv2.dilate(threshold, kernel, iterations=2)
        contours, _ = cv2.findContours(dilated, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        return sorted(contours, key=cv2.contourArea, reverse=True)

    def _skew_angle(self, contour: np.ndarray) -> float:
        angle = cv2.minAreaRect(contour)[-1]
        if angle < -45:
            angle = 90 + angle
        return -1.0 * angle

