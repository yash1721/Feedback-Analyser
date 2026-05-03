from app.domain.routing.team_router import RoutingResult, TeamRouter


DEFAULT_TEAM_KEYWORDS = {
    "Design Team": ["design", "layout", "animations", "branding", "typography"],
    "Backend Team": ["backend", "api", "database", "security", "crashes", "load balancing"],
    "Frontend Team": ["frontend", "mobile app", "dark mode", "user interface", "navigation"],
    "Logistics Team": ["shipping", "delivery", "inventory", "route", "warehouse", "packaging"],
    "Payment Team": ["payment", "checkout", "fraud", "transaction", "refund", "billing"],
    "Marketing Team": ["marketing", "ads", "email campaign", "seo", "referral", "loyalty"],
    "Sales Team": ["sales", "crm", "revenue", "targets", "deals"],
    "Customer Support Team": ["support", "live chat", "tickets", "helpdesk", "knowledge base"],
    "Human Resources Team": ["hr", "onboarding", "employee", "wellness", "benefits"],
}


class KeywordTeamRouter(TeamRouter):
    def __init__(self, team_keywords: dict[str, list[str]] | None = None) -> None:
        self.team_keywords = team_keywords or DEFAULT_TEAM_KEYWORDS

    def route(self, text: str) -> RoutingResult:
        normalized = text.lower()
        for team, keywords in self.team_keywords.items():
            for keyword in keywords:
                if keyword in normalized:
                    return RoutingResult(team=team, matched_keyword=keyword)
        return RoutingResult(team="Unknown Team")

