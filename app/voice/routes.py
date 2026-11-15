from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from twilio.request_validator import RequestValidator
from twilio.twiml.voice_response import VoiceResponse

from app.core.config import get_settings

router = APIRouter(prefix="/voice", tags=["voice"])
settings = get_settings()
validator = RequestValidator(settings.twilio_auth_token)


@router.post("/twiml")
async def twiml(request: Request) -> Response:
    form = await request.form()
    signature = request.headers.get("X-Twilio-Signature", "")
    # Validate against the PUBLIC url Twilio signed, not the proxy-internal one.
    if not validator.validate(
        f"{settings.public_base_url}/voice/twiml", dict(form), signature
    ):
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")

    response = VoiceResponse()
    connect = response.connect()
    connect.stream(
        url=f"{settings.public_base_url.replace('https://', 'wss://')}/voice/media-stream"
    )
    return Response(content=str(response), media_type="application/xml")