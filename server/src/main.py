import asyncio
import json
from typing import Union

import cv2
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from serverTracker import YOLOVideoProcessor

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins="*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

model_path = "shuffle_detect.pt"
video_path = "./Gameplay_1.mp4"
video_processor = YOLOVideoProcessor(model_path, video_path)
#video_processor.run()

@app.get("/reset")
def reset():
    video_processor.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    

# @app.get("/")
# def get_video():
#     success, frame = video_processor.cap.read()
#     if success:
#         results = video_processor.process_frame(frame)
#         video_processor.object_positions = video_processor.get_object_position(results)
#         print(video_processor.object_positions)
#     return JSONResponse(content=video_processor.object_positions)



async def video_stream():
    while True:
        success, frame = video_processor.cap.read()
        if not success:
            break
        results = video_processor.process_frame(frame)
        video_processor.object_positions = video_processor.get_object_position(results)
        yield f"data: {video_processor.object_positions.replace("\n", "")}\n\n"
        await asyncio.sleep(0.002)

@app.get("/")
async def stream_video():
    return StreamingResponse(video_stream(), media_type="text/event-stream")