from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Chatbot

router = APIRouter(
    prefix="/embed",
    tags=["Embed"],
)


@router.get("/{embed_token}")
async def get_embed_script(
    embed_token: str,
    db: Session = Depends(get_db),
):
    chatbot = (
        db.query(Chatbot)
        .filter(Chatbot.embed_token == embed_token)
        .first()
    )

    if chatbot is None:
        raise HTTPException(
            status_code=404,
            detail="Invalid embed token",
        )

    base_url = "http://localhost:8000"

    script = f"""
<script>
(function() {{
    var s = document.createElement("script");
    s.src = "{base_url}/api/v1/widget/{chatbot.embed_token}.js";
    s.async = true;
    document.body.appendChild(s);
}})();
</script>
"""

    return {
        "chatbot_name": chatbot.name,
        "embed_token": chatbot.embed_token,
        "embed_code": script,
    }