# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.

# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

import glob
import os
import torch
import argparse
import numpy as np

from PIL import Image
from cotracker.utils.visualizer import Visualizer, read_video_from_path
from cotracker.predictor import CoTrackerPredictor

# Unfortunately MPS acceleration does not support all the features we require,
# but we may be able to enable it in the future

DEFAULT_DEVICE = (
    # "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
    "cuda"
    if torch.cuda.is_available()
    else "cpu"
)

# if DEFAULT_DEVICE == "mps":
#     os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--video_path",
        default="./assets/apple.mp4",
        help="path to a video",
    )
    parser.add_argument(
        "--mask_path",
        default="./assets/apple_mask.png",
        help="path to a segmentation mask",
    )
    parser.add_argument(
        "--checkpoint",
        default="./checkpoints/cotracker2.pth",
        # default=None,
        help="CoTracker model parameters",
    )
    parser.add_argument("--grid_size", type=int, default=10, help="Regular grid size")
    parser.add_argument(
        "--grid_query_frame",
        type=int,
        default=0,
        help="Compute dense and grid tracks starting from this frame",
    )

    parser.add_argument(
        "--backward_tracking",
        action="store_true",
        help="Compute tracks in both directions, not only forward",
    )

    args = parser.parse_args()
    if args.checkpoint is not None:
        model = CoTrackerPredictor(checkpoint=args.checkpoint)
    else:
        model = torch.hub.load("facebookresearch/co-tracker", "cotracker2")
    model = model.to(DEFAULT_DEVICE)


    video_path_list = glob.glob("assets/*.mp4")
    # video_path_list = glob.glob("data/vid/*.mp4")

    # sort
    # video_path_list.sort()
    for video_path in video_path_list:
        args.video_path = video_path

        # load the input video frame by frame
        video = read_video_from_path(args.video_path)
        # (t, h, w, c) -> (t, c, h, w)
        video = torch.from_numpy(video).permute(0, 3, 1, 2)[None].float()
        # segm_mask = np.array(Image.open(os.path.join(args.mask_path)))
        # segm_mask = torch.from_numpy(segm_mask)[None, None]

        video = video.to(DEFAULT_DEVICE)
        video = video[:, :200]
        with torch.no_grad():
            pred_tracks, pred_visibility = model(
                video,
                grid_size=args.grid_size,  # 10
                grid_query_frame=args.grid_query_frame,  # 0
                backward_tracking=args.backward_tracking,  # False
                # segm_mask=segm_mask,
            )
        print("computed")

        # save a video with predicted tracks
        seq_name = os.path.splitext(args.video_path.split("/")[-1])[0]
        vis = Visualizer(save_dir="./saved_videos", pad_value=120, linewidth=3)
        vis.visualize(
            video,
            pred_tracks,  # (b, f, num_points, 2)
            pred_visibility,  # (b, f, num_points)
            query_frame=0 if args.backward_tracking else args.grid_query_frame,
            filename=seq_name,
        )
