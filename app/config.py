from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    routebinder_inbox_url: str = ""
    data_dir: str = "data"


settings = Settings()
