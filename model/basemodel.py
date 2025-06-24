import cv2
import numpy as np
import easyocr
import re
from ultralytics import YOLO
import os

class Number_Plate_Recognizer():
    def __init__(self, config):
        try:
            self.detector = YOLO(config.yolo_weights_file)
        except Exception as e:
            raise Exception(f'Your YOLO weights file is not available!!! Error: {str(e)}')
        self.reader = easyocr.Reader(config.ocr_languages)
        
    
    def extract_number_plate_images(self, image, result):
        plate_images = []

        if result[0].boxes is not None:
            bboxes = result[0].boxes
            for idx, bbox in enumerate(bboxes):
                xyxy = bbox.xyxy
                xmin = int(xyxy[0][0])
                ymin = int(xyxy[0][1])
                xmax = int(xyxy[0][2])
                ymax = int(xyxy[0][3])
                # Crop the plate image
                plate_image = image[ymin:ymax, xmin:xmax]
                plate_images.append(plate_image)

        return plate_images
    
    def ocr_preprocessing(self, license_plate_image):
        if isinstance(license_plate_image, np.ndarray):
            image = license_plate_image
        else:
            image = np.array(license_plate_image)
        
        # Handle different image formats
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
            
        blur = cv2.GaussianBlur(gray, (5, 5), 5)
        return blur           
    
    
    def plt_img_and_anot(self, img_files, label_files):
        # This method seems to be for visualization of training data
        # It expects file paths, not the actual images and text
        images = []
        for img, label in zip(img_files, label_files):
            if isinstance(img, str):  # If it's a file path
                img = cv2.imread(img)
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            else:  # If it's already an image array
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                
            height = img.shape[0]
            width = img.shape[1]
            
            if isinstance(label, str) and label.endswith('.txt'):  # If it's a label file path
                with open(label, 'r') as f:
                    lines = f.readlines()
                    for line in lines:
                        bbox = line.split(' ')[1:]
                        x_center = float(bbox[0]) * width
                        y_center = float(bbox[1]) * height
                        w = float(bbox[2]) * width
                        h = float(bbox[3]) * height

                        x1 = x_center - w/2
                        y1 = y_center - h/2
                        x2 = x_center + w/2
                        y2 = y_center + h/2
                        cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), (255, 0, 0), 2)
            else:  # If it's text to overlay
                # Add text overlay on the image
                cv2.putText(img, str(label), (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
                
            images.append(img)
        return images
    
    def visualize_results(self, plate_images, plate_numbers):
        # New method for visualizing detection results
        result_images = []
        for i, (plate_img, plate_text) in enumerate(zip(plate_images, plate_numbers)):
            # Create a copy of the plate image for annotation
            annotated_img = plate_img.copy()
            if len(annotated_img.shape) == 2:  # If grayscale, convert to BGR
                annotated_img = cv2.cvtColor(annotated_img, cv2.COLOR_GRAY2BGR)
            
            # Add text below the plate image
            h, w = annotated_img.shape[:2]
            text_img = np.zeros((h + 50, w, 3), dtype=np.uint8)
            text_img[:h, :w] = annotated_img
            
            # Add recognized text
            y_offset = h + 20
            for line in plate_text.strip().split('\n'):
                if line.strip():
                    cv2.putText(text_img, line.strip(), (5, y_offset), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    y_offset += 25
            
            result_images.append(text_img)
        
        return result_images
            
        
    def predict(self, input_image):
        # Fixed the main prediction method
        result = self.detector(input_image)
        
        plate_images = self.extract_number_plate_images(input_image, result)
        plate_numbers = []
        
        for plate_image in plate_images:
            preprocessed_image = self.ocr_preprocessing(plate_image)
            
            # Fixed: Use self.reader instead of self.recognizer and removed duplicate call
            ocr_results = self.reader.readtext(preprocessed_image)
            
            full_text = ''
            for detection in ocr_results:
                # EasyOCR returns (bbox, text, confidence)
                text = detection[1]
                cleaned_text = re.sub(r'[^A-Z0-9\-]', '', text.upper())
                if cleaned_text:  # Only add non-empty text
                    full_text += cleaned_text + '\n'
            
            plate_numbers.append(full_text.strip())

        # Return visualization of results instead of calling plt_img_and_anot incorrectly
        return self.visualize_results( plate_images, plate_numbers)
    
    def get_plate_texts(self, input_image):
        # Method to get just the text results without visualization
        result = self.detector(input_image)
        plate_images = self.extract_number_plate_images(input_image, result)
        plate_numbers = []
        
        for plate_image in plate_images:
            preprocessed_image = self.ocr_preprocessing(plate_image)
            ocr_results = self.reader.readtext(preprocessed_image)
            
            full_text = ''
            for detection in ocr_results:
                text = detection[1]
                cleaned_text = re.sub(r'[^A-Z0-9\-]', '', text.upper())
                if cleaned_text:
                    full_text += cleaned_text + ' '
            
            plate_numbers.append(full_text.strip())
        return plate_numbers