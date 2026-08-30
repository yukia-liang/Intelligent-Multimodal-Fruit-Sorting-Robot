from ultralytics import YOLOWorld
# Load a pretrained YOLOv8s-worldv2 model
model = YOLOWorld('./yolov8s-worldv2.pt')
# Train the model on the COCO8 example dataset for 100 epochs
results = model.train(data='./data_s/data.yaml', epochs=100,  imgsz=640, rect=True)