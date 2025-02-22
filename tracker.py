import cv2
import time
import torch
import json

from ultralytics import YOLO

# Check if GPU is available
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Using device: {device}")
print(torch.cuda.get_device_name(0))

# Class to represent a line on the video frame
class Line:
    def __init__(self, line_id, x_position=None, y_position=None, orientation='vertical', color=(0, 0, 255), thickness=2):
        """
        Initialize a Line object.
        Parameters:
        - line_id (int): Unique ID for the line.
        - x_position (int): X position of the line. If None, defaults to the middle of the frame.
        - y_position (int): Y position of the line. If None, defaults to the bottom of the frame.
        - orientation (str): Orientation of the line ('vertical' or 'horizontal').
        - color (tuple): RGB color of the line.
        - thickness (int): Thickness of the line.
        """
        self.line_id = line_id
        self.x_position = x_position
        self.y_position = y_position
        self.orientation = orientation
        self.color = color
        self.thickness = thickness
        self.flash_start_time = None
        self.counters = {}
        self.counted_ids = set()

    def draw(self, frame):
        """
        Draw the line on the frame.
        Parameters:
        - frame (numpy.ndarray): The video frame to draw the line on.
        """
        height, width, _ = frame.shape
        x_position = self.x_position if self.x_position is not None else width // 2
        y_position = self.y_position if self.y_position is not None else height
        line_color = (0, 255, 0) if self.flash_start_time and time.time() - self.flash_start_time < 1 else self.color
        if self.orientation == 'vertical':
            cv2.line(frame, (x_position, 0), (x_position, y_position), line_color, self.thickness)
        # elif self.orientation == 'horizontal':
        #     cv2.line(frame, (0, y_position), (width, y_position), line_color, self.thickness)

    def check_object_crossing(self, results, frame):
        """
        Check if any objects cross the line.
        Parameters:
        - results (list): List of detection results from the YOLO model.
        - frame (numpy.ndarray): The video frame to check for object crossing.
        Returns:
        - bool: True if any object crossed the line, False otherwise.
        """
        height, width, _ = frame.shape
        x_position = self.x_position if self.x_position is not None else width // 2
        y_position = self.y_position if self.y_position is not None else height
        crossed = False
        for result in results:
            boxes = result.boxes
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].int().tolist()
                center_x = (x1 + x2) // 2
                center_y = (y1 + y2) // 2
                class_id = int(box.cls[0])
                class_name = result.names[class_id]
                object_id = box.id[0] if box.id is not None else None
                if object_id is not None and object_id not in self.counted_ids:
                    if self.orientation == 'vertical' and center_x < x_position:
                        if class_name not in self.counters:
                            self.counters[class_name] = {}
                        if object_id not in self.counters[class_name]:
                            self.counters[class_name][object_id] = 0
                        self.counters[class_name][object_id] += 1
                        self.counted_ids.add(object_id)
                        self.flash_start_time = time.time()
                        crossed = True
                    elif self.orientation == 'horizontal' and center_y < y_position:
                        if class_name not in self.counters:
                            self.counters[class_name] = {}
                        if object_id not in self.counters[class_name]:
                            self.counters[class_name][object_id] = 0
                        self.counters[class_name][object_id] += 1
                        self.counted_ids.add(object_id)
                        self.flash_start_time = time.time()
                        crossed = True
        return crossed

    def display_counters(self, frame):
        """
        Display the counters on the frame.
        Parameters:
        - frame (numpy.ndarray): The video frame to display the counters on.
        """
        height, width, _ = frame.shape
        y_position = height - 30
        for class_name, counts in self.counters.items():
            for object_id, count in counts.items():
                cv2.putText(frame, f"{class_name} (ID: {object_id}): {count}", (10, y_position), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                y_position -= 30

# Class to process video frames using YOLO model
class YOLOVideoProcessor:
    def __init__(self, model_path, video_path):
        """
        Initialize the YOLOVideoProcessor object.
        Parameters:
        - model_path (str): Path to the YOLO model file.
        - video_path (str): Path to the video file.
        """
        self.model = YOLO(model_path).to(device)
        print(f"Model device: {next(self.model.parameters()).device}")  # Debug statement
        self.video_path = video_path
        self.cap = cv2.VideoCapture(video_path)
        self.start_time = time.time()
        self.frame_count = 0
        self.lines = self.create_dynamic_lines()
        self.regions = self.create_regions(self.lines)

    def create_dynamic_lines(self):
        """
        Create dynamic lines based on the video frame dimensions.
        Returns:
        - list: List of Line objects.
        """
        ret, frame = self.cap.read()
        if not ret:
            raise ValueError("Failed to read the first frame of the video.")
        height, width, _ = frame.shape
        x_step = width // 30  # Adjust step size for 30 vertical lines
        y_step = height // 10
        lines = []
        for i in range(1, 31):  # Adjust range for 30 vertical lines
            lines.append(Line(line_id=i, x_position=i * x_step, orientation='vertical'))
        for i in range(1, 10):
            lines.append(Line(line_id=i + 30, y_position=i * y_step, orientation='horizontal'))
        return lines

    def create_regions(self, lines):
        """
        Create regions based on the intersections of the lines.
        Parameters:
        - lines (list of Line objects): List of Line objects.
        Returns:
        - dict: Dictionary of regions with keys as region names and values as (x1, y1, x2, y2) coordinates.
        """
        vertical_lines = sorted([line.x_position for line in lines if line.orientation == 'vertical'])
        horizontal_lines = sorted([line.y_position for line in lines if line.orientation == 'horizontal'])
        regions = {}
        for i in range(len(vertical_lines) - 1):
            for j in range(len(horizontal_lines) - 1):
                x1 = vertical_lines[i]
                y1 = horizontal_lines[j]
                x2 = vertical_lines[i + 1]
                y2 = horizontal_lines[j + 1]
                region_name = f"Region_{i}_{j}"
                regions[region_name] = (x1, y1, x2, y2)
        return regions

    def process_frame(self, frame):
        """
        Process a single video frame.
        Parameters:
        - frame (numpy.ndarray): The video frame to process.
        Returns:
        - list: List of detection results from the YOLO model.
        """
        for line in self.lines:
            line.draw(frame)
        results = self.model.track(frame, persist=True)
        return results

    def check_object_region(self, results, frame):
        """
        Check which region each detected object falls into.
        Parameters:
        - results (list): List of detection results from the YOLO model.
        - frame (numpy.ndarray): The video frame to check for object regions.
        """
        for result in results:
            boxes = result.boxes
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].int().tolist()
                center_x = (x1 + x2) // 2
                center_y = (y1 + y2) // 2
                class_id = int(box.cls[0])
                class_name = result.names[class_id]
                object_id = box.id[0] if box.id is not None else None
                region_name = self.get_region(center_x, center_y)
                if region_name:
                    cv2.putText(frame, f"{class_name} (ID: {object_id}) in {region_name}", (center_x, center_y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                    

    def get_object_position(self, results):
        positions = []
        for result in results:
            boxes = result.boxes
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].int().tolist()
                class_id = int(box.cls[0])
                class_name = result.names[class_id]
                object_id = box.id[0] if box.id is not None else None
                positions.append({
                    'id': int(object_id) if object_id is not None else None,
                    'class_name': class_name,
                    'x1': x1,
                    'y1': y1,
                    'x2': y2,
                    'y2': y2
                })
        return json.dumps(positions, indent=4)




    def get_region(self, x, y):
        """
        Get the region name for the given x and y coordinates.
        Parameters:
        - x (int): X coordinate.
        - y (int): Y coordinate.
        Returns:
        - str: Region name.
        """
        for region_name, (x1, y1, x2, y2) in self.regions.items():
            if x1 <= x <= x2 and y1 <= y <= y2:
                return region_name
        return None

    def check_object_lines(self, results, frame):
        """
        Check which lines each detected object crosses.
        Parameters:
        - results (list): List of detection results from the YOLO model.
        - frame (numpy.ndarray): The video frame to check for object crossing lines.
        """
        for result in results:
            boxes = result.boxes
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].int().tolist()
                center_x = (x1 + x2) // 2
                center_y = (y1 + y2) // 2
                class_id = int(box.cls[0])
                class_name = result.names[class_id]
                object_id = box.id[0] if box.id is not None else None
                closest_line = None
                min_distance = float('inf')
                for line in self.lines:
                    if line.orientation == 'vertical':
                        distance = abs(center_x - line.x_position)
                    elif line.orientation == 'horizontal':
                        distance = abs(center_y - line.y_position)
                    if distance < min_distance:
                        min_distance = distance
                        closest_line = line
                if closest_line:
                    if closest_line.orientation == 'vertical' and center_x < closest_line.x_position:
                        print(f"Object {class_name} (ID: {object_id}) crossed line: V{closest_line.line_id}")
                    elif closest_line.orientation == 'horizontal' and center_y < closest_line.y_position:
                        print(f"Object {class_name} (ID: {object_id}) crossed line: H{closest_line.line_id}")

    def run(self):
        """
        Run the video processing loop.
        """
        while self.cap.isOpened():
            success, frame = self.cap.read()
            if success:
                results = self.process_frame(frame)
                annotated_frame = results[0].plot()
                for line in self.lines:
                    line.check_object_crossing(results, frame)
                    # line.display_counters(annotated_frame)
                self.check_object_region(results, annotated_frame)
                self.check_object_lines(results, annotated_frame)
                print(self.get_object_position(results))
                self.frame_count += 1
                elapsed_time = time.time() - self.start_time
                fps = self.frame_count / elapsed_time
                cv2.putText(annotated_frame, f"FPS: {fps:.2f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.imshow('Video', annotated_frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            else:
                break
        self.cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    model_path = "shuffle_detect.pt"
    video_path = "./Gameplay_1.mp4"
    video_processor = YOLOVideoProcessor(model_path, video_path)
    video_processor.run()