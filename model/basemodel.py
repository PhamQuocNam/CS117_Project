import cv2
import numpy as np
import re
from ultralytics import YOLO
import os
from fast_plate_ocr import ONNXPlateRecognizer

class Number_Plate_Recognizer():
    def __init__(self, config):
        try:
            self.detector = YOLO(config.yolo_weights_file)
        except Exception as e:
            raise Exception(f'Your YOLO weights file is not available!!! Error: {str(e)}')
        self.reader = ONNXPlateRecognizer("global-plates-mobile-vit-v2-model")
        
    def extract_number_plate_images(self, image, result):
        plate_images = []

        if result[0].boxes is not None:
            bboxes = result[0].boxes
            for idx, bbox in enumerate(bboxes):
                xyxy = bbox.xyxy
                xmin = int(xyxy[0][0]) -5
                ymin = int(xyxy[0][1]) -5
                xmax = int(xyxy[0][2]) +5
                ymax = int(xyxy[0][3]) +5
                # Crop the plate image
                plate_image = image[ymin:ymax, xmin:xmax]
                plate_images.append(plate_image)

        return plate_images
    
    def ocr_preprocessing(self, license_plate_image):
        image = cv2.resize(license_plate_image,(640,640))
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        gray = np.array(gray)

        return gray       
    
    
    def plt_img_and_anot(self, img_files, label_files):
        images = []
        for img, label in zip(img_files, label_files):
            if isinstance(img, str): 
                img = cv2.imread(img)
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            else:  
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
            else:  
                cv2.putText(img, str(label), (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
                
            images.append(img)
        return images
    
    def visualize_results(self, plate_images, plate_numbers):
        result_images = []
        for i, (plate_img, plate_text) in enumerate(zip(plate_images, plate_numbers)):
            annotated_img = plate_img.copy()
            if len(annotated_img.shape) == 2:  # If grayscale, convert to BGR
                annotated_img = cv2.cvtColor(annotated_img, cv2.COLOR_GRAY2BGR)
            
            h, w = annotated_img.shape[:2]
            text_img = np.zeros((h + 50, w, 3), dtype=np.uint8)
            text_img[:h, :w] = annotated_img
            
            y_offset = h + 20
            for line in plate_text.strip().split('\n'):
                if line.strip():
                    cv2.putText(text_img, line.strip(), (5, y_offset), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    y_offset += 25
            
            result_images.append(text_img)
        
        return result_images
            
        
    def predict(self, input_image):
        result = self.detector(input_image)
        
        plate_images = self.extract_number_plate_images(input_image, result)
        plate_numbers = []
        
        for plate_image in plate_images:
            preprocessed_image = self.ocr_preprocessing(plate_image)
            
            ocr_results = self.reader.run(preprocessed_image)
            for res in ocr_results:
                plate_numbers.append(re.sub("_","",res))
        
        plate_numbers = [number[:4] + "\n"+ number[4:] for number in plate_numbers]
        return self.visualize_results( plate_images, plate_numbers)
    
    def get_plate_texts(self, input_image):
        result = self.detector(input_image)
        plate_images = self.extract_number_plate_images(input_image, result)
        plate_numbers = []
        
        for plate_image in plate_images:
            preprocessed_image = self.ocr_preprocessing(plate_image)
            ocr_results = self.reader.run(preprocessed_image)
            for res in ocr_results:
                plate_numbers.append(re.sub("_","",res))
            
        plate_numbers = [number[:4] + "\n"+ number[4:]  for number in plate_numbers ]
        return plate_numbers