from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.core.database import get_users_collection
from app.core.security import hash_password, verify_password, create_access_token, get_current_user
from app.models.user import User
from app.schemas.auth import RegisterIn, LoginIn, TokenOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _user_to_dict(u: dict) -> dict:
    """Convert user document to response dictionary, removing internal MontyDB fields."""
    u.pop("_id", None)  # Remove MontyDB internal ID
    u.pop("password_hash", None)  # Don't expose password hash
    return {"id": u.get("id"), "name": u.get("name"), "email": u.get("email"), "school_name": u.get("school_name")}


@router.post("/register", response_model=TokenOut)
def register(body: RegisterIn):
    """Register a new user using MontyDB collection."""
    users_collection = get_users_collection()
    
    # Check if user already exists using MQL syntax
    existing = users_collection.find_one({"email": body.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new user document
    user_data = User(
        name=body.name,
        email=body.email,
        school_name=body.school_name,
        password_hash=hash_password(body.password),
    )
    
    # Insert document into collection using MQL syntax
    user_dict = user_data.model_dump()
    users_collection.insert_one(user_dict)
    
    # Generate token
    token = create_access_token(user_data.id)
    return TokenOut(access_token=token, user=_user_to_dict(user_dict))


@router.post("/login", response_model=TokenOut)
def login(form: OAuth2PasswordRequestForm = Depends()):
    """Login user using OAuth2 form with email as username."""
    users_collection = get_users_collection()
    
    # Query using MQL syntax - OAuth2 form uses 'username' field; we accept it as email
    user_doc = users_collection.find_one({"email": form.username})
    if not user_doc or not verify_password(form.password, user_doc.get("password_hash", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    
    # Generate token using user ID
    token = create_access_token(user_doc.get("id"))
    return TokenOut(access_token=token, user=_user_to_dict(user_doc.copy()))


@router.post("/login-json", response_model=TokenOut)
def login_json(body: LoginIn):
    """Login user with JSON body (alternative to OAuth2 form)."""
    users_collection = get_users_collection()
    
    # Query using MQL syntax
    user_doc = users_collection.find_one({"email": body.email})
    if not user_doc or not verify_password(body.password, user_doc.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Generate token using user ID
    token = create_access_token(user_doc.get("id"))
    return TokenOut(access_token=token, user=_user_to_dict(user_doc.copy()))


@router.get("/me")
def me(current=Depends(get_current_user)):
    """Get current authenticated user information."""
    return _user_to_dict(current.copy())
