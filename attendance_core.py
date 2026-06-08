import os
import cv2
import numpy as np
import face_recognition

class AttendanceCore:
    def __init__(self, known_faces_dir="known_faces"):
        self.known_faces_dir = known_faces_dir
        self.known_encodings = []
        self.known_rolls = []
        self.present_rolls = set()
        
        # Initial load of registered faces
        self.load_known_faces()

    def load_known_faces(self):
        """Loads all student photos from the known_faces directory and computes their 128D encodings."""
        self.known_encodings = []
        self.known_rolls = []
        
        if not os.path.exists(self.known_faces_dir):
            os.makedirs(self.known_faces_dir)
            return

        print(f"Loading reference faces from '{self.known_faces_dir}'...")
        for filename in os.listdir(self.known_faces_dir):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                roll = os.path.splitext(filename)[0]
                filepath = os.path.join(self.known_faces_dir, filename)
                try:
                    # Load image and compute its face encodings
                    image = face_recognition.load_image_file(filepath)
                    encodings = face_recognition.face_encodings(image)
                    if encodings:
                        self.known_encodings.append(encodings[0])
                        self.known_rolls.append(roll)
                        print(f"✔ Successfully loaded face for roll number: {roll}")
                    else:
                        print(f"⚠ Warning: No face detected in image '{filename}'")
                except Exception as e:
                    print(f"❌ Error loading '{filename}': {e}")
        print(f"Total reference faces loaded: {len(self.known_encodings)}")

    def process_frame(self, frame):
        """
        Processes a single BGR OpenCV camera frame:
        1. Downscales frame for rapid CPU computation.
        2. Detects and recognizes faces.
        3. Logs present student roll numbers.
        4. Draws visual bounding boxes and labels onto the original frame.
        """
        if frame is None:
            return None

        # Resize frame to 1/2 size for faster face recognition processing (CPU optimization)
        scale_factor = 2
        small_frame = cv2.resize(frame, (0, 0), fx=1.0/scale_factor, fy=1.0/scale_factor)
        
        # Convert BGR (OpenCV) to RGB (face_recognition expects RGB)
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

        # Find all face locations and encodings in the current frame
        face_locations = face_recognition.face_locations(rgb_small_frame, model="hog")
        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

        for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
            # Default to Unknown
            name = "Unknown"
            
            if self.known_encodings:
                # Compare face encodings
                matches = face_recognition.compare_faces(self.known_encodings, face_encoding, tolerance=0.6)
                
                # Check distances to find the best matching known face
                face_distances = face_recognition.face_distance(self.known_encodings, face_encoding)
                if len(face_distances) > 0:
                    best_match_index = np.argmin(face_distances)
                    if matches[best_match_index]:
                        name = self.known_rolls[best_match_index]
                        self.present_rolls.add(name)

            # Scale back up face coordinates to match the original frame size
            top *= scale_factor
            right *= scale_factor
            bottom *= scale_factor
            left *= scale_factor

            # Choose bounding box color: Green for recognized, Red for unknown
            color = (46, 204, 113) if name != "Unknown" else (231, 76, 60) # OpenCV is BGR: Green (113,204,46) / Red (60,76,231)

            # Draw box around face
            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
            
            # Draw label background box
            cv2.rectangle(frame, (left, bottom - 30), (right, bottom), color, cv2.FILLED)
            
            # Put label text (student roll number or Unknown)
            font = cv2.FONT_HERSHEY_DUPLEX
            cv2.putText(frame, name, (left + 6, bottom - 6), font, 0.7, (255, 255, 255), 1)

        return frame

    def get_present_rolls(self):
        """Returns list of student roll numbers detected present in this session."""
        return sorted(list(self.present_rolls))

    def finish(self):
        """Resets the present students set for a new attendance session."""
        self.present_rolls.clear()
        print("Attendance session reset. Ready for next session.")
