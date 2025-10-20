import cv2
import numpy as np

# Import Hailo modules (you may need to adjust based on version)
from hailo import device, network, config

def main():
    # Load the device
    dev = device.Device.create()
    print("Device:", dev)
    
    # Load a compiled model (HEF file)
    hef_path = "/usr/share/hailo_models/yolov5n_seg_h8.hef"
    net = network.Network.create(dev, hef_path)
    print("Network loaded:", net)
    
    # Configure input/output
    in_stream = net.get_input_stream()
    out_stream = net.get_output_stream()
    
    # e.g. using camera
    cap = cv2.VideoCapture(0)  # may require proper camera setup
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Pre-process (resize etc)
        img = cv2.resize(frame, (net.input_width, net.input_height))
        img = img.astype(np.float32)
        img = img / 255.0  # if model expects normalized
        
        # Run inference
        in_stream.write(img.tobytes())
        results = out_stream.read()
        
        # Post-process results (depends on model)
        # e.g., decode bounding boxes, class ids etc
        print(results)
        
        # Display
        #cv2.imshow("Frame", frame)
        #if cv2.waitKey(1) & 0xFF == ord('q'):
        #    break

    cap.release()
    #cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
