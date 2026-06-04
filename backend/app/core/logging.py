SENSITIVE_LOG_FIELDS = {
    "access_token",
    "authorization",
    "email",
    "github_url",
    "password",
    "readme_text",
    "token",
}


def mask_sensitive_payload(value):
    if hasattr(value, "model_dump"):
        value = value.model_dump()
    elif hasattr(value, "dict"):
        value = value.dict()

    return _mask_value(value)


def _mask_value(value):
    if isinstance(value, dict):
        return {
            key: "***MASKED***" if str(key).lower() in SENSITIVE_LOG_FIELDS else _mask_value(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_mask_value(item) for item in value]
    return value
