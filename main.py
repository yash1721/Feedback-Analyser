from flask import Flask,request,jsonify
import cv2
import json
import requests
import numpy as np
import pytesseract

app = Flask(__name__)

def get_grayscale(image):
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

def remove_noise(image):
    return cv2.medianBlur(image,5)

def thresholding(image):
    return cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

def noise_removal(image):
   kernel = np.ones((1,1),np.uint8)
   image = cv2.dilate(image, kernel, iterations = 1) # very thin letter
   kernel = np.ones((1,1),np.uint8)
   image = cv2.erode(image, kernel, iterations = 1)  #very thick letter
   image = cv2.morphologyEx(image, cv2.MORPH_OPEN, kernel)
   return image

def get_Text(url):
   response = requests.get(url)
   text = "Failed Image Retrival"

   if response.status_code == 200:
      image_array = np.asarray(bytearray(response.content), dtype=np.uint8)
      img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

      img = get_grayscale(img)
      img = thresholding(img)
      img = noise_removal(img)
      custom_config = r'-l eng+hin --oem 3 --psm 6'
      text = 'NO TEXT TO BE APPEARED'
      try:
         text = pytesseract.image_to_string(img,config=custom_config, timeout=5)
      except RuntimeError as timeout_error:
         print("")
   return text

@app.route("/", methods =['GET', 'POST'])
def handle_request():
   URI = str(request.args.get('uri'));
   text = get_Text(URI)
   dataset = {'text' : text, 'Url' : URI}
   jsondata = json.dumps(dataset)
   return jsondata

if __name__ == "__main__":
   app.run(debug=True)