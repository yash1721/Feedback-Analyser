import cv2
import numpy as np


class ImagePreprocessor:
    def preprocess_for_ocr(self, image: np.ndarray) -> np.ndarray:
        gray = self.to_grayscale(image)
        thresholded = self.threshold(gray)
        return self.remove_noise(thresholded)

    def to_grayscale(self, image: np.ndarray) -> np.ndarray:
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    def threshold(self, image: np.ndarray) -> np.ndarray:
        return cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

    def remove_noise(self, image: np.ndarray) -> np.ndarray:
        kernel = np.ones((1, 1), np.uint8)
        image = cv2.dilate(image, kernel, iterations=1)
        image = cv2.erode(image, kernel, iterations=1)
        return cv2.morphologyEx(image, cv2.MORPH_OPEN, kernel)

