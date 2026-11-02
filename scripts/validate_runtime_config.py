from app.core.config import settings
from app.core.runtime_validation import assert_runtime_settings_safe


def main() -> None:
    assert_runtime_settings_safe(settings)
    print("Runtime configuration validation passed")


if __name__ == "__main__":
    main()
