


cd ~/projects
git clone https://github.com/ultralytics/yolov5.git
cd yolov5
pip install -r requirements.txt

python export.py --weights model.pt --include onnx --img 640 --batch 1

