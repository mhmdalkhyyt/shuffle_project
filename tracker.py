import cv2
import time
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from ultralytics import YOLO
import torch

# Check if GPU is available
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Using device: {device}")
print(torch.cuda.get_device_name(0))

# Class to represent a line on the video frame
class Line:
    def __init__(self, x_position=None, y_position=None, color=(0, 0, 255), thickness=2):
        """
        Initialize a Line object.

        Parameters:
        - x_position (int): X position of the line. If None, defaults to the middle of the frame.
        - y_position (int): Y position of the line. If None, defaults to the bottom of the frame.
        - color (tuple): RGB color of the line.
        - thickness (int): Thickness of the line.
        """
        self.x_position = x_position
        self.y_position = y_position
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
        cv2.line(frame, (x_position, 0), (x_position, y_position), line_color, self.thickness)

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
        crossed = False
        for result in results:
            boxes = result.boxes
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].int().tolist()
                center_x = (x1 + x2) // 2
                class_id = int(box.cls[0])
                class_name = result.names[class_id]
                object_id = box.id[0] if box.id is not None else None
                if object_id is not None and center_x < x_position and object_id not in self.counted_ids:
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
    def __init__(self, model_path, video_path, line_positions=None):
        """
        Initialize the YOLOVideoProcessor object.

        Parameters:
        - model_path (str): Path to the YOLO model file.
        - video_path (str): Path to the video file.
        - line_positions (list of tuples): List of (x, y) positions for the lines.
        """
        self.model = YOLO(model_path).to(device)
        print(f"Model device: {next(self.model.parameters()).device}")  # Debug statement
        self.video_path = video_path
        self.cap = cv2.VideoCapture(video_path)
        self.start_time = time.time()
        self.frame_count = 0
        self.lines = [Line(x_position=x, y_position=y) for x, y in line_positions] if line_positions else [Line()]
        self.class_names = self.model.names

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

    def run(self):
        """
        Run the video processing loop.

        Returns:
        - numpy.ndarray: The annotated video frame.
        """
        while self.cap.isOpened():
            success, frame = self.cap.read()
            if success:
                results = self.process_frame(frame)
                annotated_frame = results[0].plot()
                for line in self.lines:
                    line.check_object_crossing(results, frame)
                    line.display_counters(annotated_frame)
                self.frame_count += 1
                elapsed_time = time.time() - self.start_time
                fps = self.frame_count / elapsed_time
                cv2.putText(annotated_frame, f"FPS: {fps:.2f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                return annotated_frame
            else:
                break
        self.cap.release()

# Class to create a Tkinter GUI for video processing
class VideoApp:
    def __init__(self, model_path, video_path, line_positions=None):
        """
        Initialize the VideoApp object.

        Parameters:
        - model_path (str): Path to the YOLO model file.
        - video_path (str): Path to the video file.
        - line_positions (list of tuples): List of (x, y) positions for the lines.
        """
        self.root = tk.Tk()
        self.root.title("Shuffleboard Object Detection and Tracking")
        self.model_path = model_path
        self.video_path = video_path
        self.line_positions = line_positions
        self.video_processor = YOLOVideoProcessor(model_path, video_path, line_positions)
        self.canvas = tk.Canvas(self.root)
        self.canvas.pack(side=tk.RIGHT)
        self.text_box = tk.Text(self.root, height=30, width=30)
        self.text_box.pack(side=tk.LEFT)
        self.class_var = tk.StringVar()
        self.class_dropdown = ttk.Combobox(self.root, textvariable=self.class_var, values=self.video_processor.class_names)
        self.class_dropdown.pack(side=tk.LEFT)
        self.x_entry = tk.Entry(self.root)
        self.x_entry.pack(side=tk.LEFT)
        self.submit_button = tk.Button(self.root, text="Submit Line", command=self.submit_line)
        self.submit_button.pack(side=tk.LEFT)
        self.pause_button = tk.Button(self.root, text="Pause/Resume", command=self.toggle_pause)
        self.pause_button.pack(side=tk.LEFT)
        self.clear_button = tk.Button(self.root, text="Clear Lines", command=self.clear_lines)
        self.clear_button.pack(side=tk.LEFT)
        self.paused = False
        self.update()

    def update(self):
        """
        Update the video frame in the Tkinter GUI.
        """
        if not self.paused:
            frame = self.video_processor.run()
            if frame is not None:
                frame_height, frame_width, _ = frame.shape
                self.canvas.config(width=frame_width, height=frame_height)
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame)
                imgtk = ImageTk.PhotoImage(image=img)
                self.canvas.imgtk = imgtk
                self.canvas.create_image(0, 0, anchor=tk.NW, image=imgtk)
                self.text_box.delete(1.0, tk.END)
                for line in self.video_processor.lines:
                    for class_name, counts in line.counters.items():
                        for object_id, count in counts.items():
                            self.text_box.insert(tk.END, f"{class_name} (ID: {object_id}): {count}\n")
                self.root.after(10, self.update)

    def submit_line(self):
        """
        Submit a new line position.
        """
        try:
            x_position = int(self.x_entry.get())
            self.video_processor.lines.append(Line(x_position=x_position))
        except ValueError:
            print("Invalid X position")

    def clear_lines(self):
        """
        Clear all lines.
        """
        self.video_processor.lines = []

    def toggle_pause(self):
        """
        Toggle the pause/resume state.
        """
        self.paused = not self.paused

    def run(self):
        """
        Run the Tkinter main loop.
        """
        self.root.mainloop()

if __name__ == "__main__":
    model_path = "shuffle_detect.pt"
    video_path = "./Gameplay_1.mp4"
    line_positions = [(100, 400), (300, 400)]
    app = VideoApp(model_path, video_path, line_positions)
    app.run()