import argparse
import cv2
import time
from Model import PyTorchModel
from Model import TFModel
from typing import List, Dict, Tuple
from Label import Label
import webcolors
import json
import math
from google_drive import DriveConnection
import time
import torch
from torch.autograd import Variable
from threading import Thread

#Ground Sample Distance for this video (find online based on the drones specs)
GSD = .86
make_prediction = True
current_frame = None

def predict_and_display(frame, model, mp4_file):
    global make_prediction, current_frame
    #run model predictions
    labels = model.predict(frame)

    #display bounding boxes with labels
    display_bounding_boxes(frame, labels)

    # #display lines between sharks and other sharks or sharks and people, with distances labeled
    # if frame_has_shark(labels):
    #     shark_distances = get_distances_from_sharks(labels)
    #     display_distances(frame, shark_distances)

    #display this frame
    frame = cv2.resize(frame, dsize=(1024, 540), interpolation=cv2.INTER_CUBIC)
    current_frame = frame
    make_prediction = True


def run_model(mp4_file, model):
    global make_prediction, current_frame
    vidcap = cv2.VideoCapture(mp4_file)
    success, frame = vidcap.read()
    current_frame = frame
    count = 0
    while success:


        cv2.imshow(mp4_file,current_frame)
        time.sleep(.2)
        
        if make_prediction:
            make_prediction = False
            thread = Thread(target=predict_and_display, args=(frame, model, mp4_file))
            thread.start()
            
        #need this for the video stream to work continuously, basically says press 'q' to quit
        if cv2.waitKey(25) & 0xFF == ord('q'):
            break

        success, frame = vidcap.read()
        
def display_bounding_boxes(frame, labels):
    for label in labels:
        #if label.score > 0.8:
        label_name = label.group.lower()
        upperLeft = (label.x_min, label.y_min)
        lowerRight = (label.x_max, label.y_max)
        print(label_name + " at " + str(upperLeft) + " " + str(lowerRight))
        cv2.rectangle(frame, upperLeft, lowerRight, webcolors.name_to_rgb(label.color), thickness=3)

def display_distances(frame, shark_distances):
    color_of_line = classes["shark"]["color"]
    for shark_label in shark_distances:
        shark_coords = shark_label.get_midpoint()
        for other in shark_distances[shark_label]:
            other_coords = other.get_midpoint()
            cv2.line(frame, shark_coords, other_coords, webcolors.name_to_rgb(color_of_line), 3)
            text_location = midpoint_of_line(shark_coords, other_coords)
            distance = distance_between_objects(shark_label, other) * GSD
            display_label(frame, text_location, str(int(distance)))
            


def display_label(img, label_location, label_text):
    cv2.putText(img, label_text, label_location, cv2.FONT_HERSHEY_SIMPLEX, 1, webcolors.name_to_rgb(classes["shark"]["color"]), 2)


#for now, just use distance between midpoint of bounding boxes
def distance_between_objects(obj1, obj2) -> float:
    mid_x1, mid_y1 = obj1.get_midpoint()
    mid_x2, mid_y2 = obj2.get_midpoint()
    return math.sqrt(((mid_x2 - mid_x1)**2) + ((mid_y2 - mid_y1)**2))

def frame_has_shark(labels: List[Label]) -> bool:
    for label in labels:
        if label.group.lower() == 'shark':
            return True
    return False

#return the midpont of the line between two objects so we know where put the lines label
def midpoint_of_line(p1: Tuple[int, int], p2: Tuple[int, int]) -> Tuple[int, int]:
    return (int)((p2[0]-p1[0])/2, (p2[1]-p1[1])/2)

# if a shark is detected in the frame, get the distances from the shark to other sharks and
# humans in the frame
def get_distances_from_sharks(labels: List[Label]) -> Dict[Label, List[Label]]:
    shark_distances = dict()
    for label in labels:
        if label.group.lower() == 'shark':
            others: List[Label] = list()
            for other in labels:
                if (not other.id == label.id) and (other.group.lower() == 'person' or other.group.lower() == 'shark'):
                    others.add(other)
            shark_distances[label] = others
    return shark_distances

    

#using a bounding ellipse would be more accurate to find distance between objects (on average)
#as opposed to a bounding box.
def get_bounding_ellipse_from_box(x_min, x_max, y_min, y_max):
    pass

#TODO: find a way to implement this
def distance_between_ellipses():
    pass




if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run PyTorch or TensorFlow model on an mp4 video.')
    parser.add_argument('mp4', help="Path to the video.")
    parser.add_argument('model', help="PyTorch or TensorFlow model file (specify --drive flag for Google Drive path).")
    parser.add_argument('--drive', help="File is a Google Drive file.", action="store_true")
    args = parser.parse_args()

    if args.drive:
        print("Retrieving model from Google Drive.")
        drive = DriveConnection()
        file_stream = None
        #try:
        MIME_type = "text/x-python"
        file_stream = drive.getFileByName(args.model, MIME_type)
        #except:
        #print("could not find the Google Drive file for MIME type {}".format(MIME_type))
        if file_stream:
            model = PyTorchModel(file_stream)
    else:
        print("Retrieving local model.")
        model = PyTorchModel(args.model)
    run_model(args.mp4, model)