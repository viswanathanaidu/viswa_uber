from datetime import datetime, timedelta
from jose import JWTError, jwt
from pydantic import BaseModel
from fastapi import Depends, HTTPException, status, Security
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
import os

# Config
SECRET_KEY = os.getenv("SECRET_KEY", "secret")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))

# Define scopes
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="users/login",
    scopes={
        "rider": "Request and manage rides",
        "driver": "Accept and complete rides",
        "admin": "Manage users and drivers"
    }
)

# Token response model
class Token(BaseModel):
    access_token: str
    token_type: str

# Payload model from JWT
class TokenData(BaseModel):
    user_id: int
    email: str
    role: str
    scopes: list[str] = []

# Create JWT token
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# Verify JWT token and enforce scopes
def verify_token(security_scopes: SecurityScopes, token: str = Depends(oauth2_scheme)) -> TokenData:
    auth_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": f'Bearer scope="{security_scopes.scope_str}"'},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("user_id")
        email: str = payload.get("email")
        role: str = payload.get("role")
        scopes: list[str] = payload.get("scopes", [])

        if user_id is None or email is None or role is None:
            raise auth_error

        token_data = TokenData(user_id=user_id, email=email, role=role, scopes=scopes)

        # ✅ Check required scopes
        for scope in security_scopes.scopes:
            if scope not in token_data.scopes:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing required scope: {scope}"
                )
        return token_data
    except JWTError:
        raise auth_error
# Role-based authorization (helper)
def require_role(required_role: str):
    def role_checker(token_data: TokenData = Security(verify_token, scopes=[required_role])):
        if token_data.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Only {required_role}s can access this endpoint"
            )
        return token_data
    return role_checker
