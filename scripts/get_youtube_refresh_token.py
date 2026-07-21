"""YouTube refresh token 1회 획득 — 브라우저 동의 필요(사람이 실행).

.env의 YOUTUBE_CLIENT_ID/SECRET을 읽어 OAuth 로컬 플로우를 돌리고, refresh token을
출력한다. 스코프는 youtube.upload(업로드 전용). 값은 코드에 하드코딩하지 않는다.

실행: 세션에서  ! python scripts/get_youtube_refresh_token.py
(브라우저가 열리면 발행할 채널의 구글 계정으로 동의 → 미검증 경고는 '고급→계속')
"""
from __future__ import annotations

from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def _load_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip()
    return env


def main() -> None:
    env = _load_env(Path(__file__).resolve().parent.parent / ".env")
    cid = env.get("YOUTUBE_CLIENT_ID", "")
    secret = env.get("YOUTUBE_CLIENT_SECRET", "")
    if not cid or not secret:
        raise SystemExit(".env에 YOUTUBE_CLIENT_ID/SECRET이 없습니다.")

    flow = InstalledAppFlow.from_client_config(
        {
            "installed": {
                "client_id": cid,
                "client_secret": secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost"],
            }
        },
        scopes=SCOPES,
    )
    creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
    print("\n=== 아래 값을 .env의 YOUTUBE_REFRESH_TOKEN=에 붙여넣으세요 ===")
    print(creds.refresh_token)


if __name__ == "__main__":
    main()
