"""
OAuth2/OIDC Provider API endpoints.
Makes CMS an identity provider for external applications.
"""

import json
from typing import Optional
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.api.dependencies import get_current_user, get_db
from backend.core.oauth2_provider_service import get_oauth2_provider_service
from backend.models.user import User

router = APIRouter(prefix="/oauth", tags=["oauth2-provider"])


# === Schemas ===


class ClientCreateRequest(BaseModel):
    """Request to create an OAuth2 client"""

    name: str
    redirect_uris: list[str]
    client_type: str = "confidential"
    description: Optional[str] = None
    logo_url: Optional[str] = None
    grant_types: Optional[list[str]] = None
    allowed_scopes: str = "openid profile email"
    require_pkce: bool = True


class ClientResponse(BaseModel):
    """OAuth2 client details"""

    client_id: str
    name: str
    description: Optional[str]
    logo_url: Optional[str]
    client_type: str
    redirect_uris: list[str]
    allowed_scopes: str
    require_pkce: bool
    is_active: bool
    created_at: str


class ClientCreatedResponse(BaseModel):
    """Response when creating a new client"""

    client_id: str
    client_secret: Optional[str]
    message: Optional[str]
    client: ClientResponse


class TokenResponse(BaseModel):
    """OAuth2 token response"""

    access_token: str
    token_type: str
    expires_in: int
    refresh_token: Optional[str] = None
    scope: Optional[str] = None
    id_token: Optional[str] = None


class TokenIntrospectionResponse(BaseModel):
    """Token introspection response"""

    active: bool
    scope: Optional[str] = None
    client_id: Optional[str] = None
    username: Optional[str] = None
    token_type: Optional[str] = None
    exp: Optional[int] = None
    iat: Optional[int] = None
    sub: Optional[str] = None
    aud: Optional[str] = None
    iss: Optional[str] = None


# === OIDC Discovery ===


@router.get("/.well-known/openid-configuration")
async def openid_configuration(db: Session = Depends(get_db)):
    """
    OpenID Connect Discovery endpoint.
    Returns provider configuration and supported features.
    """
    service = get_oauth2_provider_service(db)
    return JSONResponse(content=service.get_openid_configuration())


@router.get("/.well-known/jwks.json")
async def jwks():
    """
    JSON Web Key Set endpoint.
    Returns public keys for verifying tokens.
    Note: This is a simplified version using symmetric keys.
    Production should use asymmetric keys (RSA/EC).
    """
    # For HS256, there's no public key to expose
    # This endpoint would be populated with RSA/EC public keys in production
    return JSONResponse(content={"keys": []})


# === Client Management ===


@router.post("/clients", response_model=ClientCreatedResponse)
async def create_client(
    request: ClientCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Register a new OAuth2 client application.
    Client secret is only shown once in the response.
    """
    service = get_oauth2_provider_service(db)

    result = service.create_client(
        organization_id=str(current_user.organization_id),
        name=request.name,
        redirect_uris=request.redirect_uris,
        client_type=request.client_type,
        description=request.description,
        logo_url=request.logo_url,
        grant_types=request.grant_types,
        allowed_scopes=request.allowed_scopes,
        require_pkce=request.require_pkce,
        created_by=str(current_user.id),
    )

    client = result["client"]

    return ClientCreatedResponse(
        client_id=result["client_id"],
        client_secret=result["client_secret"],
        message=result["message"],
        client=ClientResponse(
            client_id=client.client_id,
            name=client.name,
            description=client.description,
            logo_url=client.logo_url,
            client_type=client.client_type,
            redirect_uris=json.loads(client.redirect_uris),
            allowed_scopes=client.allowed_scopes,
            require_pkce=client.require_pkce,
            is_active=client.is_active,
            created_at=client.created_at,
        ),
    )


@router.get("/clients", response_model=list[ClientResponse])
async def list_clients(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all OAuth2 clients for the organization."""
    from backend.models.oauth2 import OAuth2Client

    clients = (
        db.query(OAuth2Client)
        .filter(
            OAuth2Client.organization_id == current_user.organization_id,
            OAuth2Client.is_active == True,
        )
        .all()
    )

    return [
        ClientResponse(
            client_id=c.client_id,
            name=c.name,
            description=c.description,
            logo_url=c.logo_url,
            client_type=c.client_type,
            redirect_uris=json.loads(c.redirect_uris),
            allowed_scopes=c.allowed_scopes,
            require_pkce=c.require_pkce,
            is_active=c.is_active,
            created_at=c.created_at,
        )
        for c in clients
    ]


@router.delete("/clients/{client_id}")
async def delete_client(
    client_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Deactivate an OAuth2 client."""
    from backend.models.oauth2 import OAuth2Client

    client = (
        db.query(OAuth2Client)
        .filter(
            OAuth2Client.client_id == client_id,
            OAuth2Client.organization_id == current_user.organization_id,
        )
        .first()
    )

    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )

    client.is_active = False
    db.commit()

    return {"message": "Client deactivated successfully"}


# === Authorization Endpoint ===


@router.get("/authorize")
async def authorize(
    request: Request,
    response_type: str = Query(...),
    client_id: str = Query(...),
    redirect_uri: str = Query(...),
    scope: str = Query("openid"),
    state: Optional[str] = Query(None),
    code_challenge: Optional[str] = Query(None),
    code_challenge_method: Optional[str] = Query("S256"),
    nonce: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    OAuth2 Authorization endpoint.
    Initiates the authorization code flow.
    """
    service = get_oauth2_provider_service(db)

    # Validate client
    client = service.get_client(client_id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid client_id",
        )

    # Validate redirect URI
    if not service.validate_redirect_uri(client, redirect_uri):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid redirect_uri",
        )

    # Only support authorization_code for now
    if response_type != "code":
        return _error_redirect(redirect_uri, "unsupported_response_type", state)

    # Validate PKCE if required
    if client.require_pkce and not code_challenge:
        return _error_redirect(redirect_uri, "invalid_request", state, "PKCE required")

    # User must be authenticated
    if not current_user:
        # Redirect to login with return URL
        login_url = f"/login?next={request.url}"
        return RedirectResponse(url=login_url, status_code=302)

    # Validate and filter scopes
    valid_scopes = service.validate_scopes(client, scope)

    # Generate authorization code
    code = service.create_authorization_code(
        client=client,
        user=current_user,
        redirect_uri=redirect_uri,
        scopes=valid_scopes,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
        nonce=nonce,
    )

    # Redirect back to client
    params = {"code": code}
    if state:
        params["state"] = state

    return RedirectResponse(
        url=f"{redirect_uri}?{urlencode(params)}",
        status_code=302,
    )


# === Token Endpoint ===


@router.post("/token", response_model=TokenResponse)
async def token(
    grant_type: str = Form(...),
    code: Optional[str] = Form(None),
    redirect_uri: Optional[str] = Form(None),
    client_id: Optional[str] = Form(None),
    client_secret: Optional[str] = Form(None),
    code_verifier: Optional[str] = Form(None),
    refresh_token: Optional[str] = Form(None),
    scope: Optional[str] = Form(None),
    request: Request = None,
    db: Session = Depends(get_db),
):
    """
    OAuth2 Token endpoint.
    Exchanges authorization code or refresh token for access tokens.
    """
    service = get_oauth2_provider_service(db)

    # Support client credentials in Basic auth header
    if not client_id:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Basic "):
            import base64

            try:
                decoded = base64.b64decode(auth_header[6:]).decode()
                client_id, client_secret = decoded.split(":", 1)
            except Exception:
                pass

    if not client_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Client authentication required",
        )

    # Get client
    client = service.get_client(client_id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid client credentials",
        )

    # Validate client secret for confidential clients
    if client.client_type == "confidential":
        if not client_secret or not service.validate_client_secret(client, client_secret):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid client credentials",
            )

    try:
        if grant_type == "authorization_code":
            if not code or not redirect_uri:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Missing required parameters",
                )

            result = service.exchange_authorization_code(
                client=client,
                code=code,
                redirect_uri=redirect_uri,
                code_verifier=code_verifier,
            )

        elif grant_type == "refresh_token":
            if not refresh_token:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Missing refresh_token",
                )

            result = service.refresh_tokens(
                client=client,
                refresh_token=refresh_token,
                scopes=scope,
            )

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported grant_type: {grant_type}",
            )

        return TokenResponse(**result)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# === Token Revocation ===


@router.post("/revoke")
async def revoke_token(
    token: str = Form(...),
    token_type_hint: Optional[str] = Form(None),
    client_id: Optional[str] = Form(None),
    client_secret: Optional[str] = Form(None),
    request: Request = None,
    db: Session = Depends(get_db),
):
    """
    OAuth2 Token Revocation endpoint (RFC 7009).
    Revokes an access or refresh token.
    """
    service = get_oauth2_provider_service(db)

    # Support Basic auth
    if not client_id:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Basic "):
            import base64

            try:
                decoded = base64.b64decode(auth_header[6:]).decode()
                client_id, client_secret = decoded.split(":", 1)
            except Exception:
                pass

    # Client authentication is recommended but not required
    if client_id:
        client = service.get_client(client_id)
        if client and client.client_type == "confidential":
            if not service.validate_client_secret(client, client_secret or ""):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid client credentials",
                )

    # Revoke token (always returns 200 per RFC 7009)
    service.revoke_token(token, token_type_hint)

    return {"status": "ok"}


# === Token Introspection ===


@router.post("/introspect", response_model=TokenIntrospectionResponse)
async def introspect_token(
    token: str = Form(...),
    token_type_hint: Optional[str] = Form(None),
    client_id: Optional[str] = Form(None),
    client_secret: Optional[str] = Form(None),
    request: Request = None,
    db: Session = Depends(get_db),
):
    """
    OAuth2 Token Introspection endpoint (RFC 7662).
    Returns information about a token.
    """
    service = get_oauth2_provider_service(db)

    # Support Basic auth
    if not client_id:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Basic "):
            import base64

            try:
                decoded = base64.b64decode(auth_header[6:]).decode()
                client_id, client_secret = decoded.split(":", 1)
            except Exception:
                pass

    # Client authentication required for introspection
    if not client_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Client authentication required",
        )

    client = service.get_client(client_id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid client credentials",
        )

    if client.client_type == "confidential":
        if not service.validate_client_secret(client, client_secret or ""):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid client credentials",
            )

    result = service.introspect_token(token, token_type_hint)
    return TokenIntrospectionResponse(**result)


# === UserInfo Endpoint ===


@router.get("/userinfo")
async def userinfo(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    OpenID Connect UserInfo endpoint.
    Returns claims about the authenticated user.
    """
    service = get_oauth2_provider_service(db)

    # Get token from Authorization header
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth_header[7:]

    # Introspect token to validate and get user
    import hashlib

    from backend.models.oauth2 import OAuth2AccessToken

    token_hash = hashlib.sha256(token.encode()).hexdigest()
    access_token = (
        db.query(OAuth2AccessToken).filter(OAuth2AccessToken.token_hash == token_hash).first()
    )

    if not access_token or not access_token.is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
        )

    # Get user
    user = db.query(User).filter(User.id == access_token.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return service.get_userinfo(user, access_token.scopes)


# === End Session (Logout) ===


@router.get("/logout")
async def logout(
    id_token_hint: Optional[str] = Query(None),
    post_logout_redirect_uri: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    OpenID Connect End Session endpoint.
    Logs out the user and optionally redirects.
    """
    # In a full implementation, you would:
    # 1. Validate the id_token_hint
    # 2. Revoke all tokens for the user
    # 3. Clear server-side session

    if post_logout_redirect_uri:
        # Should validate against registered URIs
        redirect_url = post_logout_redirect_uri
        if state:
            redirect_url = f"{redirect_url}?state={state}"
        return RedirectResponse(url=redirect_url, status_code=302)

    return {"message": "Logged out successfully"}


def _error_redirect(
    redirect_uri: str,
    error: str,
    state: Optional[str] = None,
    error_description: Optional[str] = None,
) -> RedirectResponse:
    """Create error redirect response"""
    params = {"error": error}
    if state:
        params["state"] = state
    if error_description:
        params["error_description"] = error_description

    return RedirectResponse(
        url=f"{redirect_uri}?{urlencode(params)}",
        status_code=302,
    )
