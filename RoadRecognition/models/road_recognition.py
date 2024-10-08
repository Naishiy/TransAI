from .exceptions import CameraNotFoundException
from .models import Capture

import numpy as np
import cv2


class RoadRecognition:

    @classmethod
    def recognite(cls, frame: cv2.typing.MatLike) -> cv2.typing.MatLike:
        return frame

    @classmethod
    def execute_frame(cls, success: bool, frame: cv2.typing.MatLike) -> bool:
        if not success:
            return False
        cv2.imshow('Video', frame)

    @classmethod
    def prepare_capture(cls, camera_index: int) -> cv2.VideoCapture:
        camera_capture: Capture = Capture(camera_index)
        if not camera_capture.isOpened():
            raise CameraNotFoundException
        return camera_capture

    @classmethod
    def frame_processor(cls, image):
        grayscale = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        kernel_size = 5
        blur = cv2.GaussianBlur(grayscale, (kernel_size, kernel_size), 0)
        low_t = 50
        high_t = 150
        edges = cv2.Canny(blur, low_t, high_t)
        region = cls.__region_selection(edges)
        hough = cls.__hough_transform(region)
        result = cls.__draw_lane_lines(image, cls.__lane_lines(image, hough))
        return result

    @classmethod
    def __region_selection(cls, image):
        """
        Determine and cut the region of interest in the input image.
        Parameters:
            image: we pass here the output from canny where we have
            identified edges in the frame
        """
        mask = np.zeros_like(image)
        if len(image.shape) > 2:
            channel_count = image.shape[2]
            ignore_mask_color = (255,) * channel_count
        else:
            ignore_mask_color = 255
        rows, cols = image.shape[:2]
        bottom_left = [cols * 0.1, rows * 0.95]
        top_left = [cols * 0.4, rows * 0.6]
        bottom_right = [cols * 0.9, rows * 0.95]
        top_right = [cols * 0.6, rows * 0.6]
        vertices = np.array([[bottom_left, top_left, top_right, bottom_right]], dtype=np.int32)
        cv2.fillPoly(mask, vertices, ignore_mask_color)
        masked_image = cv2.bitwise_and(image, mask)
        return masked_image

    @classmethod
    def __hough_transform(cls, image):
        """
        Determine and cut the region of interest in the input image.
        Parameter:
            image: grayscale image which should be an output from the edge detector
        """
        rho = 1
        theta = np.pi / 180
        threshold = 20
        min_line_length = 20
        max_line_gap = 500
        return cv2.HoughLinesP(image, rho=rho, theta=theta, threshold=threshold,
                               minLineLength=min_line_length, maxLineGap=max_line_gap)

    @classmethod
    def __lane_lines(cls, image, lines):
        """
        Create full lenght lines from pixel points.
            Parameters:
                image: The input test image.
                lines: The output lines from Hough Transform.
        """
        left_lane, right_lane = cls.__average_slope_intercept(lines)
        y1 = image.shape[0]
        y2 = y1 * 0.6
        left_line = cls.__pixel_points(y1, y2, left_lane)
        right_line = cls.__pixel_points(y1, y2, right_lane)
        return left_line, right_line

    @classmethod
    def __average_slope_intercept(cls, lines):
        """
        Find the slope and intercept of the left and right lanes of each image.
        Parameters:
            lines: output from Hough Transform
        """
        left_lines = []  # (slope, intercept)
        left_weights = []  # (length,)
        right_lines = []  # (slope, intercept)
        right_weights = []  # (length,)

        for line in lines:
            for x1, y1, x2, y2 in line:
                if x1 == x2:
                    continue
                slope = (y2 - y1) / (x2 - x1)
                intercept = y1 - (slope * x1)
                length = np.sqrt(((y2 - y1) ** 2) + ((x2 - x1) ** 2))
                if slope < 0:
                    left_lines.append((slope, intercept))
                    left_weights.append(length)
                else:
                    right_lines.append((slope, intercept))
                    right_weights.append(length)
        #
        left_lane = np.dot(left_weights, left_lines) / np.sum(left_weights) if len(left_weights) > 0 else None
        right_lane = np.dot(right_weights, right_lines) / np.sum(right_weights) if len(right_weights) > 0 else None
        return left_lane, right_lane

    @classmethod
    def __pixel_points(cls, y1, y2, line):
        """
        Converts the slope and intercept of each line into pixel points.
            Parameters:
                y1: y-value of the line's starting point.
                y2: y-value of the line's end point.
                line: The slope and intercept of the line.
        """
        if line is None:
            return None
        slope, intercept = line
        x1 = int((y1 - intercept) / slope)
        x2 = int((y2 - intercept) / slope)
        y1 = int(y1)
        y2 = int(y2)
        return (x1, y1), (x2, y2)

    @classmethod
    def __draw_lane_lines(cls, image, lines, color=None, thickness=12):
        """
        Draw lines onto the input image.
            Parameters:
                image: The input test image (video frame in our case).
                lines: The output lines from Hough Transform.
                color (Default = red): Line color.
                thickness (Default = 12): Line thickness.
        """
        if color is None:
            color = [255, 0, 0]
        line_image = np.zeros_like(image)
        for line in lines:
            if line is not None:
                cv2.line(line_image, *line, color, thickness)
        return cv2.addWeighted(image, 1.0, line_image, 1.0, 0.0)
