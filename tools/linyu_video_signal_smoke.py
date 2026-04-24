#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Linyu 视频信令最小联调脚本（仅信令层）。

用途：
- 验证后端能接收并处理 `type=video` 的邀请与后续信令。
- 不依赖真实 WebRTC 媒体流，适合先排查信令链路。

说明：
- 该脚本通过 Linyu 的 HTTP 接口发送 invite/offer/candidate/hangup。
- 需要你提供：x-token、AI账号 user_id、目标用户 user_id。
"""

from __future__ import annotations

import argparse
import json
import time
from typing import Dict

import requests


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Linyu video 信令 smoke")
    parser.add_argument("--linyu-base", required=True, help="如 http://127.0.0.1:9200")
    parser.add_argument("--token", required=True, help="x-token")
    parser.add_argument("--from-id", required=True, help="发起方用户ID")
    parser.add_argument("--to-id", required=True, help="目标用户ID（AI账号）")
    parser.add_argument("--call-id", default="smoke-call-001", help="通话ID")
    return parser.parse_args()


def post(base: str, token: str, path: str, payload: Dict):
    url = base.rstrip("/") + path
    headers = {"x-token": token, "Content-Type": "application/json"}
    resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=10)
    print(f"POST {path} -> {resp.status_code} {resp.text[:200]}")
    return resp


def main() -> None:
    args = parse_args()

    invite = {
        "toId": args.to_id,
        "fromId": args.from_id,
        "callId": args.call_id,
        "audioOnly": True,
    }
    post(args.linyu_base, args.token, "/v1/api/video/invite", invite)
    time.sleep(1)

    fake_offer = {
        "toId": args.to_id,
        "fromId": args.from_id,
        "callId": args.call_id,
        "sdpType": "offer",
        "sdp": "v=0\r\no=- 0 0 IN IP4 127.0.0.1\r\ns=-\r\nt=0 0\r\n",
        "audioOnly": True,
    }
    post(args.linyu_base, args.token, "/v1/api/video/offer", fake_offer)
    time.sleep(1)

    fake_candidate = {
        "toId": args.to_id,
        "fromId": args.from_id,
        "callId": args.call_id,
        "candidate": "candidate:0 1 UDP 2122252543 127.0.0.1 5000 typ host",
        "sdpMid": "0",
        "sdpMLineIndex": 0,
        "usernameFragment": "abc",
    }
    post(args.linyu_base, args.token, "/v1/api/video/candidate", fake_candidate)
    time.sleep(1)

    hangup = {
        "toId": args.to_id,
        "fromId": args.from_id,
        "callId": args.call_id,
    }
    post(args.linyu_base, args.token, "/v1/api/video/hangup", hangup)


if __name__ == "__main__":
    main()

