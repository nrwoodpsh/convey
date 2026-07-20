from __future__ import annotations

from common.config import BaseAppSettings


class GatewaySettings(BaseAppSettings):
    # prefix → 하류 서비스 base URL (compose 서비스명)
    route_sample: str = "http://sample-domain:8000"
    route_llm: str = "http://llm-inference:8000"
    route_agent: str = "http://agent:8000"
    route_research: str = "http://research:8000"
    route_content: str = "http://content:8000"

    # Supabase 인증 (ADR 0007) — 로그인·발급은 Supabase, 게이트웨이는 JWKS 검증만
    supabase_url: str = "http://localhost"
    supabase_jwks_url: str = ""  # 비면 {supabase_url}/auth/v1/.well-known/jwks.json
    supabase_aud: str = "authenticated"

    @property
    def jwks_url(self) -> str:
        return self.supabase_jwks_url or f"{self.supabase_url}/auth/v1/.well-known/jwks.json"

    @property
    def routes(self) -> dict[str, str]:
        return {
            "/sample": self.route_sample,
            "/llm": self.route_llm,
            "/agent": self.route_agent,
            "/research": self.route_research,
            "/content": self.route_content,
        }


settings = GatewaySettings()

# 인증 없이 통과시키는 공개 경로 (로그인은 Supabase가 처리 — 게이트웨이 로그인 경로 없음)
PUBLIC_PATHS: set[str] = {"/health"}
