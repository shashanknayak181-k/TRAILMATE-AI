from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    username: str = Field(min_length=3, max_length=30, pattern=r"^[A-Za-z0-9_.-]+$")
    email: str
    password: str = Field(min_length=10, max_length=128)
    confirm_password: str
    consent: bool

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        value = value.strip().lower()
        if len(value) > 254 or "@" not in value or "." not in value.rsplit("@", 1)[-1]:
            raise ValueError("Enter a valid email address")
        return value

    @field_validator("full_name", "username")
    @classmethod
    def strip_fields(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def validate_password_and_consent(self):
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        if not self.consent:
            raise ValueError("Consent is required")
        if not any(c.isalpha() for c in self.password) or not any(c.isdigit() for c in self.password):
            raise ValueError("Password must contain letters and numbers")
        return self


class VerifyRequest(BaseModel):
    email: str
    code: str = Field(pattern=r"^\d{6}$")


class SignInRequest(BaseModel):
    identifier: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class ProfileUpdate(BaseModel):
    preferred_language: str = Field(default="English", min_length=2, max_length=30)
    city: str | None = Field(default=None, max_length=100)
    region: str | None = Field(default=None, max_length=100)
    travel_interests: list[str] = Field(default_factory=list, max_length=8)
    preferred_budget: str | None = Field(default=None, pattern=r"^(budget|moderate|premium)$")
    preferred_duration_days: int | None = Field(default=None, ge=1, le=60)
    onboarding_complete: bool = False


class ProfileResponse(ProfileUpdate):
    model_config = ConfigDict(from_attributes=True)
    onboarding_complete: bool


class UserResponse(BaseModel):
    id: int
    full_name: str
    username: str
    email: str
    email_verified: bool
    onboarding_complete: bool


class PasswordResetRequest(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        if len(value) > 254 or "@" not in value or "." not in value.rsplit("@", 1)[-1]:
            raise ValueError("Enter a valid email address")
        return value


class ResetCodeVerifyRequest(PasswordResetRequest):
    code: str = Field(pattern=r"^\d{6}$")


class PasswordResetCompleteRequest(BaseModel):
    reset_token: str = Field(min_length=32, max_length=256)
    password: str = Field(min_length=10, max_length=128)
    confirm_password: str = Field(min_length=10, max_length=128)

    @model_validator(mode="after")
    def validate_password(self):
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        if not any(c.isalpha() for c in self.password) or not any(c.isdigit() for c in self.password):
            raise ValueError("Password must contain letters and numbers")
        return self
