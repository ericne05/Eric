"""
Eric — Personal AI Agent OS
Entry point.
"""

from core.kernel.bootstrap import bootstrap


def main() -> None:
    """Start Eric."""
    kernel = bootstrap()

    try:
        print("\n[Eric] Running. Press Ctrl+C to stop.\n")
        input()
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        kernel.shutdown()


if __name__ == "__main__":
    main()
