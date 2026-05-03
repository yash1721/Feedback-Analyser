from app.domain.routing.keyword_team_router import KeywordTeamRouter


def test_routes_payment_feedback_to_payment_team():
    result = KeywordTeamRouter().route("Checkout payment failed during transaction.")

    assert result.team == "Payment Team"
    assert result.matched_keyword == "payment"


def test_unknown_feedback_returns_unknown_team():
    result = KeywordTeamRouter().route("The experience felt confusing.")

    assert result.team == "Unknown Team"
    assert result.matched_keyword is None

