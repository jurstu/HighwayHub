
import cv2
from alpr import ALPR

# Open the video file
cap = cv2.VideoCapture("/home/jur/alpr.mp4")

alpr = ALPR()

# Check if the video was opened successfully
if not cap.isOpened():
    print("Error: Could not open video file.")
else:
    print("Video file opened successfully!")
 
# Get video properties (e.g., frame count and frame width)
frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))  # Get total number of frames in the video
fps = cap.get(cv2.CAP_PROP_FPS)  # Get frames per second (FPS)
print(f"Total frames: {frame_count}, FPS: {fps}")
 
# Read and display each frame of the video
while True:
    ret, frame = cap.read()
    if not ret:
        print("End of video or error occurred.")
        break

    frame=cv2.resize(frame, [1280,720])

    lp = alpr.predict(frame)
    print(lp)
    # Display the frame
    cv2.imshow("Video Frame", frame)
 
    # Wait for 1ms for key press to continue or exit if 'q' is pressed
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
 
# Release the video capture object and close any OpenCV windows
cap.release()
cv2.destroyAllWindows()