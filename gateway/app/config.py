from __future__ import annotations

from common.config import BaseAppSettings


class GatewaySettings(BaseAppSettings):
    # prefix → 하류 서비스 base URL (compose 서비스명)
    route_auth: str = "http://auth:8000"
    route_sample: str = "http://sample-domain:8000"
    route_llm: str = "http://llm-inference:8000"
    route_agent: str = "http://agent:8000"
    route_research: str = "http://research:8000"
    route_content: str = "http://content:8000"

    @property
    def routes(self) -> dict[str, str]:
        return {
            "/auth": self.route_auth,
            "/sample": self.route_sample,
            "/llm": self.route_llm,
            "/agent": self.route_agent,
            "/research": self.route_research,
            "/content": self.route_content,
        }


settings = GatewaySettings()

# JWT 없이 통과시키는 공개 경로 (로그인 자체는 미인증)
PUBLIC_PATHS: set[str] = {"/health", "/auth/login", "/auth/refresh"}
