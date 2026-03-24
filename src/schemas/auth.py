from pydantic import BaseModel


class GoogleAuthStatusResponse(BaseModel):
    connected: bool
    authMode: str
    redirectUri: str


class GoogleAuthUrlResponse(BaseModel):
    authorizationUrl: str
    state: str
