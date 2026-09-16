"""loguru stub — provides logger with console output, no external dependency."""
import sys


class _Logger:
    def info(self, *a, **k):
        print("[INFO]", *a, file=sys.stderr)

    def debug(self, *a, **k):
        pass

    def warning(self, *a, **k):
        print("[WARN]", *a, file=sys.stderr)

    def error(self, *a, **k):
        print("[ERROR]", *a, file=sys.stderr)

    def fatal(self, *a, **k):
        print("[FATAL]", *a, file=sys.stderr)

    def exception(self, *a, **k):
        print("[ERROR]", *a, file=sys.stderr)

    def configure(self, *a, **k):
        pass


logger = _Logger()
