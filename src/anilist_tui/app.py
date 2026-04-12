from .app_core import AnilistTUI


def main() -> None:
    app = AnilistTUI()
    app.run()

if __name__ == "__main__":
    main()
