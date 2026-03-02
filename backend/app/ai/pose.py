import io
import os
import urllib.request
from PIL import Image
import numpy as np

def _load_image(image_bytes):
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    return np.array(img)

def extract_keypoints(image_bytes):
    try:
        import mediapipe as mp  # type: ignore
    except ModuleNotFoundError:
        return None, "mediapipe_missing"
    mp_pose = None
    try:
        mp_pose = mp.solutions.pose  # type: ignore
    except Exception:
        # Try Tasks API
        try:
            from mediapipe.tasks import python as mp_python  # type: ignore
            from mediapipe.tasks.python import vision as mp_vision  # type: ignore
        except Exception as e:
            return None, f"mediapipe_error:{e}"
        img_np = _load_image(image_bytes)
        h, w = img_np.shape[:2]
        model_dir = os.path.join(os.path.dirname(__file__), "models")
        model_path = os.path.join(model_dir, "pose_landmarker_full.task")
        if not os.path.exists(model_path):
            try:
                os.makedirs(model_dir, exist_ok=True)
                url = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/latest/pose_landmarker_full.task"
                urllib.request.urlretrieve(url, model_path)
            except Exception as e:
                return None, f"mediapipe_error:download_model_failed:{e}"
        try:
            BaseOptions = mp_python.BaseOptions  # type: ignore
            PoseLandmarker = mp_vision.PoseLandmarker  # type: ignore
            PoseLandmarkerOptions = mp_vision.PoseLandmarkerOptions  # type: ignore
            VisionRunningMode = mp_vision.RunningMode  # type: ignore
            options = PoseLandmarkerOptions(base_options=BaseOptions(model_asset_path=model_path), running_mode=VisionRunningMode.IMAGE)
            with PoseLandmarker.create_from_options(options) as landmarker:
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_np)  # type: ignore
                result = landmarker.detect(mp_image)
                if not result.pose_landmarks or len(result.pose_landmarks) == 0:
                    return None, "no_pose"
                lms = result.pose_landmarks[0]
                def get_xy_idx(i):
                    p = lms[i]
                    return int(p.x * w), int(p.y * h)
                points = {
                    "left_shoulder": get_xy_idx(11),
                    "right_shoulder": get_xy_idx(12),
                    "left_hip": get_xy_idx(23),
                    "right_hip": get_xy_idx(24),
                    "left_ankle": get_xy_idx(27),
                    "right_ankle": get_xy_idx(28),
                    "nose": get_xy_idx(0)
                }
                return points, None
        except Exception as e:
            return None, f"mediapipe_error:tasks_infer_failed:{e}"
    img_np = _load_image(image_bytes)
    h, w = img_np.shape[:2]
    # First pass: default complexity for speed
    with mp_pose.Pose(static_image_mode=True, model_complexity=1, enable_segmentation=False, min_detection_confidence=0.5) as pose:
        results = pose.process(img_np)
        if not results.pose_landmarks:
            # Second pass: try higher complexity to be more robust
            with mp_pose.Pose(static_image_mode=True, model_complexity=2, enable_segmentation=False, min_detection_confidence=0.3) as pose2:
                results = pose2.process(img_np)
                if not results.pose_landmarks:
                    return None, "no_pose"
        lm = results.pose_landmarks.landmark
        idx = mp_pose.PoseLandmark
        def get_xy(i):
            p = lm[i]
            return int(p.x * w), int(p.y * h)
        points = {
            "left_shoulder": get_xy(idx.LEFT_SHOULDER),
            "right_shoulder": get_xy(idx.RIGHT_SHOULDER),
            "left_hip": get_xy(idx.LEFT_HIP),
            "right_hip": get_xy(idx.RIGHT_HIP),
            "left_ankle": get_xy(idx.LEFT_ANKLE),
            "right_ankle": get_xy(idx.RIGHT_ANKLE),
            "nose": get_xy(idx.NOSE)
        }
        return points, None
