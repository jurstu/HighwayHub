# what needs to be done in order for hailo to be used for plate detection

<del>
1. convert keremberke model to .hef format
2. modify minimal.py up until this part:

``` python
from inference_result_handler import inference_result_handler  # <-- your working handler
``` 
is sourced from 

</del>

rewrite this file https://github.com/hailo-ai/Hailo-Application-Code-Examples/tree/main/runtime/hailo-8/python/object_detection/object_detection.py